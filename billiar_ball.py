"""美式8球 — 双人同屏。游戏循环 + 状态机，串联各纯逻辑模块。"""
import sys

import pygame

import config
import menu
import physics
import renderer
from balls import create_standard_balls, find_cue, group_of
from cue import (aim_direction, apply_fine_tune, clamp_english,
                 power_from_drag, velocity_from_aim)
from rules import evaluate_shot, is_legal_first_contact
from table import Table

STATE_BREAK_PLACE = 'break_place'   # 开球摆球：白球可在开球线左侧厨房区自由摆放
STATE_AIMING = 'aiming'
STATE_MOVING = 'moving'
STATE_BALL_IN_HAND = 'ball_in_hand'
STATE_GAMEOVER = 'gameover'

OPPOSITE = {'solid': 'stripe', 'stripe': 'solid'}


class Game:
    def __init__(self):
        self.table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                           config.TABLE_RIGHT, config.TABLE_BOTTOM)
        self.scores = [0, 0]    # 跨局累计胜场，reset() 不清零，按 R 重开局保留
        self.reset()

    def reset(self):
        self.balls = create_standard_balls(self.table)
        self.current = 0
        self.player_groups = [None, None]   # None=未分组
        self.open_table = True
        self.state = STATE_BREAK_PLACE
        self.message = "开球：在开球线左侧区域移动鼠标摆放白球，点击确定"
        self.shot_events = []
        self.shot_on_eight = False   # 本杆开始时击球者是否已清完本组（开杆前快照）
        self.winner = None
        # 三区控制状态
        self.coarse_dir = (1.0, 0.0) # 鼠标粗瞄方向（未叠加微调）
        self.aim_dir = (1.0, 0.0)    # 当前合成瞄准方向（粗瞄 + 微调）
        self.fine_offset = 0.0       # 左滑条 [-1, 1]
        self.charging = False        # 右球杆是否正在蓄力
        self.power = 0.0             # 当前蓄力 [0, 1]
        self.dragging_slider = False # 是否正在拖左滑条
        self.aiming = False          # 是否正在按住鼠标瞄准（球台区）
        self.place_mode = 'kitchen'  # 摆球特权：'kitchen'开球/'free'自由球/None正常回合
        # 杆法（右上角红点控件）
        self.english = (0.0, 0.0)    # 红点归一化偏移 (dx,dy)，模长≤1；上=跟杆 右=右塞
        self.spin_panel_open = False # 放大面板是否打开
        self.dragging_spin = False   # 是否正在拖红点

    # ---- 结算 ----
    def _shooter_on_eight(self):
        g = self.player_groups[self.current]
        if g is None:
            return False
        return not any(b.on_table and group_of(b.number) == g for b in self.balls)

    def resolve_shot(self):
        shooter_group = self.player_groups[self.current]
        result = evaluate_shot(
            self.shot_events,
            open_table=self.open_table,
            shooter_group=shooter_group,
            shooter_on_eight=self.shot_on_eight,
        )
        # 分组认领
        if result.assigned_group:
            self.player_groups[self.current] = result.assigned_group
            self.player_groups[1 - self.current] = OPPOSITE[result.assigned_group]
            self.open_table = False
        # 胜负
        if result.winner_is_shooter is True:
            self.winner = self.current
            self.scores[self.winner] += 1
            self.state = STATE_GAMEOVER
            return
        if result.winner_is_shooter is False:
            self.winner = 1 - self.current
            self.scores[self.winner] += 1
            self.state = STATE_GAMEOVER
            return
        # 母球落袋：复位并交给对手自由球
        if result.cue_pocketed:
            cue = find_cue(self.balls)
            hx, hy = self.table.head_spot()
            cue.x, cue.y, cue.vx, cue.vy = hx, hy, 0.0, 0.0
            cue.on_table = True
        # 回合切换
        if result.foul:
            self.message = f"玩家{self.current + 1} 犯规：{result.foul_reason}"
            self.current = 1 - self.current
            self.place_mode = 'free'
            self.state = STATE_BALL_IN_HAND
        elif result.continue_turn:
            self.message = f"玩家{self.current + 1} 进球，继续"
            self.state = STATE_AIMING
        else:
            self.current = 1 - self.current
            self.message = f"轮到玩家{self.current + 1}" if not result.pocketed else "未进本组球，交换"
            self.state = STATE_AIMING

    # ---- 自由球放置合法性 ----
    def _placement_valid(self, x, y):
        r = config.BALL_RADIUS
        if not (self.table.left + r <= x <= self.table.right - r):
            return False
        if not (self.table.top + r <= y <= self.table.bottom - r):
            return False
        for b in self.balls:
            if b.number == 0 or not b.on_table:
                continue
            if (b.x - x) ** 2 + (b.y - y) ** 2 < (2 * r) ** 2:
                return False
        return True

    # ---- 开球摆球：限制在开球线左侧的厨房区 ----
    def _kitchen_valid(self, x, y):
        """开球摆球合法性：在台内、且球完全位于开球线左侧。"""
        if not self._placement_valid(x, y):
            return False
        return x + config.BALL_RADIUS <= self.table.head_line_x()

    # ---- 三区控制命中判定 ----
    def _near_slider(self, x, y):
        return (abs(x - config.SLIDER_X) <= 2 * config.SLIDER_KNOB_R
                and config.SLIDER_TOP - 20 <= y <= config.SLIDER_BOTTOM + 20)

    def _near_cue(self, x, y):
        return (abs(x - config.CUE_X) <= 2 * config.CUE_GRAB_R
                and config.CUE_TOP - 20 <= y <= config.CUE_BOTTOM + 20)

    def _in_aim_zone(self, x, y):
        """鼠标处于"移动即瞄准"区域（球台区，避开左右两根控件列）。"""
        return (config.SLIDER_X + 2 * config.SLIDER_KNOB_R < x
                < config.CUE_X - 2 * config.CUE_GRAB_R)

    def _on_cue_ball(self, x, y):
        """点击是否落在白球上（用于自由球/开球阶段重新拿起白球）。"""
        cue = find_cue(self.balls)
        return (cue.x - x) ** 2 + (cue.y - y) ** 2 <= config.BALL_RADIUS ** 2

    # ---- 杆法控件命中判定 ----
    def _on_spin_icon(self, x, y):
        return ((x - config.SPIN_ICON_X) ** 2 + (y - config.SPIN_ICON_Y) ** 2
                <= config.SPIN_ICON_R ** 2)

    def _on_spin_panel(self, x, y):
        return ((x - config.SPIN_PANEL_X) ** 2 + (y - config.SPIN_PANEL_Y) ** 2
                <= config.SPIN_PANEL_R ** 2)

    def _spin_from_panel_pos(self, x, y):
        """放大面板内坐标 → 归一化打点偏移 (dx,dy)，夹到单位圆。"""
        dx = (x - config.SPIN_PANEL_X) / config.SPIN_PANEL_R
        dy = (y - config.SPIN_PANEL_Y) / config.SPIN_PANEL_R
        return clamp_english(dx, dy)

    def _slider_value_from_y(self, y):
        span = config.SLIDER_BOTTOM - config.SLIDER_TOP
        frac = (y - config.SLIDER_TOP) / span
        return max(-1.0, min(1.0, frac * 2 - 1))

    def _power_from_y(self, y):
        span = config.CUE_BOTTOM - config.CUE_TOP
        return power_from_drag((y - config.CUE_TOP) / span)

    def _recompute_aim(self, coarse_dir):
        self.aim_dir = apply_fine_tune(coarse_dir[0], coarse_dir[1], self.fine_offset)

    def _fire(self):
        cue = find_cue(self.balls)
        vx, vy = velocity_from_aim(self.aim_dir[0], self.aim_dir[1], self.power)
        cue.vx, cue.vy = vx, vy
        dx, dy = self.english
        cue.spin_v = -dy             # 红点偏上(dy<0)=跟杆(+)
        cue.spin_s = dx              # 红点偏右(dx>0)=右塞(+)
        self.shot_events = []
        # 在物理推进（移除落袋球）之前，快照本杆是否处于"打8号"阶段
        self.shot_on_eight = self._shooter_on_eight()
        self.charging = False
        self.power = 0.0
        self.aiming = False
        self.fine_offset = 0.0       # 每打完一球微调杆归回中间
        self.english = (0.0, 0.0)    # 出杆后杆法归零
        self.spin_panel_open = False # 出杆后自动收起放大面板
        self.dragging_spin = False
        self.place_mode = None       # 出杆后摆球特权失效
        self.state = STATE_MOVING

    # ---- 事件处理 ----
    def handle_event(self, ev, mouse_pos):
        if self.state == STATE_GAMEOVER:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                self.reset()
            return

        if self.state == STATE_BREAK_PLACE:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._kitchen_valid(*mouse_pos):
                    cue = find_cue(self.balls)
                    cue.x, cue.y = mouse_pos
                    self.message = "瞄准：点白球可重新摆放；按住鼠标定方向，右球杆蓄力松手击球"
                    self.state = STATE_AIMING
            return

        if self.state == STATE_BALL_IN_HAND:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self._placement_valid(*mouse_pos):
                    cue = find_cue(self.balls)
                    cue.x, cue.y = mouse_pos
                    self.message = "瞄准：点白球可重新摆放；按住鼠标定方向，右球杆蓄力松手击球"
                    self.state = STATE_AIMING
            return

        if self.state != STATE_AIMING:
            return

        mx, my = mouse_pos
        cue = find_cue(self.balls)

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            # 杆法控件优先：图标(开/关) → 面板(设点并拖动)
            if self._on_spin_icon(mx, my):
                self.spin_panel_open = not self.spin_panel_open
                self.dragging_spin = False
                return
            if self.spin_panel_open and self._on_spin_panel(mx, my):
                self.english = self._spin_from_panel_pos(mx, my)
                self.dragging_spin = True
                return
            # 持有摆球特权时点白球 → 重新拿起来再摆
            if self.place_mode is not None and self._on_cue_ball(mx, my):
                if self.place_mode == 'kitchen':
                    self.message = "重新开球摆放：在开球线左侧区域移动鼠标，点击确定"
                    self.state = STATE_BREAK_PLACE
                else:
                    self.message = "自由球：移动鼠标重新放置母球，点击确定"
                    self.state = STATE_BALL_IN_HAND
                return
            if self._near_cue(mx, my):
                self.charging = True       # 抓住球杆开始蓄力，瞄准方向锁定
                self.power = self._power_from_y(my)
            elif self._near_slider(mx, my):
                self.dragging_slider = True
                self.fine_offset = self._slider_value_from_y(my)
                self._recompute_aim(self.coarse_dir)
            elif self._in_aim_zone(mx, my):
                self.aiming = True         # 按住才瞄准，瞄准线立即朝向鼠标
                coarse = aim_direction(cue.x, cue.y, mx, my)
                if coarse is not None:
                    self.coarse_dir = coarse
                    self._recompute_aim(coarse)

        elif ev.type == pygame.MOUSEMOTION:
            if self.dragging_spin:
                self.english = self._spin_from_panel_pos(mx, my)
            elif self.charging:
                self.power = self._power_from_y(my)
            elif self.dragging_slider:
                self.fine_offset = self._slider_value_from_y(my)
                self._recompute_aim(self.coarse_dir)
            elif self.aiming:              # 按住拖动时瞄准线持续跟随鼠标
                coarse = aim_direction(cue.x, cue.y, mx, my)
                if coarse is not None:
                    self.coarse_dir = coarse
                    self._recompute_aim(coarse)

        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            if self.charging:
                if self.power > 0.0:
                    self._fire()
                else:
                    self.charging = False
            self.dragging_slider = False
            self.dragging_spin = False     # 松开停止拖红点
            self.aiming = False            # 松开则瞄准方向定格

    def update(self):
        if self.state == STATE_MOVING:
            self.shot_events.extend(physics.step(self.balls, self.table))
            if physics.all_stopped(self.balls):
                self.resolve_shot()

    # ---- 绘制 ----
    def draw(self, screen, font, mouse_pos):
        renderer.draw_table(screen)
        renderer.draw_pockets(screen, self.table)
        if self.state == STATE_BREAK_PLACE:
            renderer.draw_head_line(screen, self.table)
            cue = find_cue(self.balls)
            if self._kitchen_valid(*mouse_pos):
                cue.x, cue.y = mouse_pos
        if self.state == STATE_BALL_IN_HAND:
            cue = find_cue(self.balls)
            if self._placement_valid(*mouse_pos):
                cue.x, cue.y = mouse_pos
        renderer.draw_balls(screen, self.balls, font)
        if self.state == STATE_AIMING:
            group = self.player_groups[self.current]
            on_eight = self._shooter_on_eight()
            forbidden = lambda n: not is_legal_first_contact(
                n, self.open_table, group, on_eight)
            renderer.draw_aim(screen, find_cue(self.balls), self.aim_dir,
                              self.balls, -self.english[1],   # spin_v = -dy（上=跟杆）
                              is_forbidden=forbidden)
            renderer.draw_fine_slider(screen, font, self.fine_offset)
            renderer.draw_power_cue(screen, font, self.power, self.charging)
            renderer.draw_spin_icon(screen, self.english)
            if self.spin_panel_open:
                renderer.draw_spin_panel(screen, font, self.english)
        if self.state == STATE_BALL_IN_HAND:
            renderer.draw_ball_in_hand_hint(screen, font)
        renderer.draw_hud(screen, font, self.player_groups, self.current, self.message)
        renderer.draw_score(screen, font, self.scores)
        if self.state == STATE_GAMEOVER:
            renderer.draw_gameover(screen, font, self.winner)


def main():
    pygame.init()
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    pygame.display.set_caption("2D 美式8球")
    font = pygame.font.SysFont('arialunicode,heitisc,pingfangsc,arial', 22)
    title_font = pygame.font.SysFont('arialunicode,heitisc,pingfangsc,arial', 64)
    clock = pygame.time.Clock()

    table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                  config.TABLE_RIGHT, config.TABLE_BOTTOM)
    scene = 'menu'      # 'menu' 封面 / 'game' 对局
    game = None

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if scene == 'menu':
                if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                        and menu.button_hit(*mouse_pos)):
                    game = Game()          # 全新一局，比分清零
                    scene = 'game'
            else:  # scene == 'game'
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    scene = 'menu'         # 丢弃当前对局，返回封面
                    game = None
                else:
                    game.handle_event(ev, mouse_pos)

        if scene == 'game' and game is not None:
            game.update()

        if scene == 'menu':
            renderer.draw_menu(screen, font, title_font, table)
        else:
            game.draw(screen, font, mouse_pos)
            renderer.draw_back_hint(screen, font)

        pygame.display.flip()
        clock.tick(config.FPS)


if __name__ == '__main__':
    main()
