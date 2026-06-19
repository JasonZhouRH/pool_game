"""美式8球 — 双人同屏。游戏循环 + 状态机，串联各纯逻辑模块。"""
import sys

import pygame

import config
import menu
import physics
import renderer
import sounds
from balls import (create_nine_ball_balls, create_snooker_balls,
                   create_standard_balls, find_cue, group_of)
from cue import (aim_direction, apply_fine_tune, clamp_english,
                 power_from_drag, velocity_from_aim)
from rules import (evaluate_nine_ball_shot, evaluate_shot,
                   evaluate_snooker_shot, first_cue_contact,
                   is_legal_first_contact,
                   is_legal_nine_ball_contact, is_snookered,
                   snooker_balls_on)
from table import Table

STATE_BREAK_PLACE = 'break_place'   # 开球摆球：白球可在开球线左侧厨房区自由摆放
STATE_AIMING = 'aiming'
STATE_MOVING = 'moving'
STATE_BALL_IN_HAND = 'ball_in_hand'
STATE_GAMEOVER = 'gameover'

OPPOSITE = {'solid': 'stripe', 'stripe': 'solid'}


def _snooker_legal_contact(number, phase, next_color):
    """斯诺克瞄准用：判断击打该球是否合法。"""
    if number == 0:
        return False
    if phase == 'red':
        return 1 <= number <= 15
    # phase == 'color'
    if next_color is None:
        return 16 <= number <= 21  # 自选彩球
    return number == next_color


class Game:
    def __init__(self, mode='eight', sound=None):
        self.mode = mode
        self.table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                           config.TABLE_RIGHT, config.TABLE_BOTTOM)
        self.scores = [0, 0]    # 跨局累计胜场，reset() 不清零，按 R 重开局保留
        self.reset()
        self.sound = sound or sounds.SoundManager()

    def reset(self):
        if self.mode == 'nine':
            self.balls = create_nine_ball_balls(self.table)
            self.player_groups = [None, None]
            self.open_table = False
            self.message = "9球模式：在开球线左侧移动鼠标摆放白球，点击确定"
        elif self.mode == 'snooker':
            self.balls = create_snooker_balls(self.table)
            self.player_groups = [None, None]
            self.open_table = False
            self._snooker_phase = 'red'
            self._snooker_next_color = None
            self._snooker_scores = [0, 0]
            self.message = "斯诺克模式：在D区移动鼠标摆放白球，点击确定"
        else:
            self.balls = create_standard_balls(self.table)
            self.player_groups = [None, None]
            self.open_table = True
            self.message = "开球：在开球线左侧区域移动鼠标摆放白球，点击确定"
        self.current = 0
        self.state = STATE_BREAK_PLACE
        self._is_break = self.mode != 'nine'  # 8球开球不分组，下一杆才认领
        self.shot_events = []
        self.shot_on_eight = False   # 本杆开始时击球者是否已清完本组（开杆前快照）
        self.winner = None
        # 三区控制状态
        self.coarse_dir = (1.0, 0.0) # 鼠标粗瞄方向（未叠加微调）
        self.aim_dir = (1.0, 0.0)    # 当前合成瞄准方向（粗瞄 + 微调）
        self.fine_offset = 0.0       # 左滑条，无上下界（循环滑动）
        self.charging = False        # 右球杆是否正在蓄力
        self.power = 0.0             # 当前蓄力 [0, 1]
        self.dragging_slider = False # 是否正在拖左滑条
        self._slider_prev_y = 0     # 拖拽期间上一帧鼠标Y，用于增量累积
        self.aiming = False          # 是否正在按住鼠标瞄准（球台区）
        self.place_mode = 'kitchen'  # 摆球特权：'kitchen'开球/'free'自由球/None正常回合
        self.free_ball = False       # 自由球:本杆可把任意球当 ball-on
        self._was_free_ball = False
        # F 键复位（斯诺克）：对手解球失败后做斯诺克方可让其重打
        self._snooker_pre_shot = None   # 出杆前整桌快照
        self._can_replay = False        # 当前是否可按 F 复位
        # 杆法（右上角红点控件）
        self.english = (0.0, 0.0)    # 红点归一化偏移 (dx,dy)，模长≤1；上=跟杆 右=右塞
        self.spin_panel_open = False # 放大面板是否打开
        self.dragging_spin = False   # 是否正在拖红点

    # ---- 结算 ----
    def _shooter_on_eight(self):
        if self.mode == 'nine':
            return False
        g = self.player_groups[self.current]
        if g is None:
            return False
        return not any(b.on_table and group_of(b.number) == g for b in self.balls)

    def resolve_shot(self):
        if self.mode == 'nine':
            result = evaluate_nine_ball_shot(self.shot_events, self._lowest_on_table,
                                             is_ball_in_hand=self._was_ball_in_hand)
        elif self.mode == 'snooker':
            phase_before = self._snooker_phase
            next_color_before = self._snooker_next_color
            result, pts, foul_pts, respot, new_phase, next_color = evaluate_snooker_shot(
                self.shot_events, self.balls, self._snooker_phase,
                self._snooker_next_color, self.table, free_ball=self._was_free_ball)
            # 计分
            if pts > 0:
                self._snooker_scores[self.current] += pts
            if foul_pts > 0:
                self._snooker_scores[1 - self.current] += foul_pts
            # 彩球复位
            for cn in respot:
                for b in self.balls:
                    if b.number == cn and not b.on_table:
                        rx, ry = self.table.snooker_respot_position(
                            {16: 'yellow', 17: 'green', 18: 'brown',
                             19: 'blue', 20: 'pink', 21: 'black'}[cn],
                            self.balls)
                        b.x, b.y = rx, ry
                        b.vx, b.vy = 0.0, 0.0
                        b.on_table = True
                        break
            # 更新阶段
            self._snooker_phase = new_phase
            self._snooker_next_color = next_color
            # 决胜黑球：仅剩黑球时，进球或犯规结束本局
            only_black_left = (
                not any(b.on_table and b.number != 0 and b.number != 21 for b in self.balls)
                and any(b.on_table and b.number == 21 for b in self.balls)
            )
            if only_black_left and (result.foul or 21 in result.pocketed):
                s0, s1 = self._snooker_scores
                if s0 == s1:
                    # 平分：黑球复位，白球放 D 区，继续
                    for b in self.balls:
                        if b.number == 21 and not b.on_table:
                            bx, by = self.table.snooker_spots()['black']
                            b.x, b.y = bx, by
                            b.vx, b.vy = 0.0, 0.0
                            b.on_table = True
                            break
                    cue = find_cue(self.balls)
                    cue.x, cue.y = self.table.snooker_d_center()
                    self._snooker_phase = 'color'
                    self._snooker_next_color = 21
                    self.message = "平分，黑球复位，继续决胜"
                    self.state = STATE_AIMING
                    self.current = 0  # 先手开球
                    return
                else:
                    self.winner = 0 if s0 > s1 else 1
                    self.scores[self.winner] += 1
                    self.state = STATE_GAMEOVER
                    return
            # 所有球清完：比分数定胜负
            all_off = not any(b.on_table and b.number != 0 for b in self.balls)
            if all_off:
                s0, s1 = self._snooker_scores
                if s0 > s1:
                    self.winner = 0
                elif s1 > s0:
                    self.winner = 1
                else:
                    self.winner = 0  # 平局先手胜
                self.scores[self.winner] += 1
                self.state = STATE_GAMEOVER
                return
        else:
            shooter_group = self.player_groups[self.current]
            result = evaluate_shot(
                self.shot_events,
                open_table=self.open_table,
                shooter_group=shooter_group,
                shooter_on_eight=self.shot_on_eight,
            )
        # 分组认领（仅8球模式，开球不分组）
        if self.mode != 'nine' and result.assigned_group:
            if self._is_break:
                # 开球进球：显示进了什么，但不分组
                group_name = '全色' if result.assigned_group == 'solid' else '花色'
                self.message = f"玩家{self.current + 1} 开球进了{group_name}，台面仍开放"
            else:
                self.player_groups[self.current] = result.assigned_group
                self.player_groups[1 - self.current] = OPPOSITE[result.assigned_group]
                self.open_table = False
        was_break = self._is_break
        self._is_break = False  # 第一杆结束后不再处于开球阶段
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
            if self.mode == 'snooker':
                hx, hy = self.table.snooker_d_center()
            else:
                hx, hy = self.table.head_spot()
            cue.x, cue.y, cue.vx, cue.vy = hx, hy, 0.0, 0.0
            cue.on_table = True
        # 回合切换
        if result.foul:
            self.message = f"玩家{self.current + 1} 犯规：{result.foul_reason}"
            self.current = 1 - self.current
            if result.cue_pocketed:
                # 母球落袋:对手在 D 区(斯诺克)/开球区(8球)摆放
                if self.mode == 'snooker':
                    self.place_mode = 'kitchen'
                    self.state = STATE_BREAK_PLACE
                    self.message = "犯规后在D区移动鼠标摆放白球，点击确定"
                else:
                    self.place_mode = 'free'
                    self.state = STATE_BALL_IN_HAND
            else:
                # 母球未落袋:斯诺克原位接着打;8球给自由球
                if self.mode == 'snooker':
                    self.place_mode = None
                    self.state = STATE_AIMING
                    cue = find_cue(self.balls)
                    balls_on = snooker_balls_on(
                        self._snooker_phase, self._snooker_next_color, self.balls)
                    if is_snookered(cue, balls_on, self.balls):
                        self.free_ball = True
                        self.message = "自由球：可击打任意球作为目标球"
                    # 对手没碰到 ball-on(用击球前阶段判定)且未拿自由球 → 可让其重打。
                    # 母球能碰到的球必然击球前在台,故按阶段判定首碰是否为目标球即可,
                    # 不依赖落袋后的在台状态(避免对手误把目标球连同彩球打进时误判可复位)。
                    fc = first_cue_contact(self.shot_events)
                    missed_ball_on = fc is None or not _snooker_legal_contact(
                        fc, phase_before, next_color_before)
                    self._can_replay = missed_ball_on and not self.free_ball
                else:
                    self.place_mode = 'free'
                    self.state = STATE_BALL_IN_HAND
        elif result.continue_turn and not was_break:
            if self.mode == 'snooker':
                if self._snooker_phase == 'red':
                    self.message = f"玩家{self.current + 1} 进球，继续击打红球"
                elif self._snooker_next_color:
                    cn = {16: '黄', 17: '绿', 18: '棕', 19: '蓝', 20: '粉', 21: '黑'}.get(self._snooker_next_color, '?')
                    self.message = f"玩家{self.current + 1} 进球，继续击打{cn}球"
                else:
                    self.message = f"玩家{self.current + 1} 进球，继续"
            else:
                self.message = f"玩家{self.current + 1} 进球，继续"
            self.state = STATE_AIMING
        elif result.continue_turn:
            # 开球进球已在上方设置了 message，不覆盖
            self.state = STATE_AIMING
        else:
            self.current = 1 - self.current
            if self.mode == 'snooker':
                if self._snooker_phase == 'red':
                    self.message = f"轮到玩家{self.current + 1}，击打红球"
                elif self._snooker_next_color:
                    cn = {16: '黄', 17: '绿', 18: '棕', 19: '蓝', 20: '粉', 21: '黑'}.get(self._snooker_next_color, '?')
                    self.message = f"轮到玩家{self.current + 1}，击打{cn}球"
                else:
                    self.message = f"轮到玩家{self.current + 1}"
            elif self.mode == 'nine':
                self.message = f"轮到玩家{self.current + 1}"
            else:
                self.message = f"轮到玩家{self.current + 1}" if not result.pocketed else "未进本组球，交换"
            self.state = STATE_AIMING

    def _replay_after_miss(self):
        """斯诺克:把球复位到对手击球前,交还回合让其重打。罚分保留。"""
        snap = self._snooker_pre_shot
        by_number = {num: (x, y, on) for num, x, y, vx, vy, on in snap['balls']}
        for b in self.balls:
            if b.number in by_number:
                x, y, on = by_number[b.number]
                b.x, b.y, b.vx, b.vy, b.on_table = x, y, 0.0, 0.0, on
        self._snooker_phase = snap['phase']
        self._snooker_next_color = snap['next_color']
        self.current = snap['current']
        self._can_replay = False
        self.free_ball = False
        self.place_mode = None
        # 清除蓄力/瞄准瞬态,避免按 F 时正握杆蓄力导致随后误出杆
        self.charging = False
        self.power = 0.0
        self.aiming = False
        self.dragging_slider = False
        self.dragging_spin = False
        self.fine_offset = 0.0
        self.english = (0.0, 0.0)
        self.spin_panel_open = False
        self.state = STATE_AIMING
        self.message = "复位：对手重新解斯诺克"

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

    # ---- 斯诺克 D 区摆球合法性 ----
    def _snooker_d_valid(self, x, y):
        """斯诺克开球：白球必须在 D 区内或弧线上。"""
        if not self._placement_valid(x, y):
            return False
        cx, cy = self.table.snooker_d_center()
        r = self.table.snooker_d_radius()
        dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        # 在 D 区半圆内（左侧）且在线左侧
        return dist <= r and x <= self.table.baulk_line_x()
    def _kitchen_valid(self, x, y):
        """开球摆球合法性：在台内、且球心在开球线上或左侧。"""
        if not self._placement_valid(x, y):
            return False
        return x <= self.table.head_line_x()

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
        """增量累积微调偏移（无上下界），轨道高度对应 fine_offset 变化 ±2。"""
        span = config.SLIDER_BOTTOM - config.SLIDER_TOP
        delta = (y - self._slider_prev_y) / span * 2
        self._slider_prev_y = y
        return self.fine_offset + delta

    def _power_from_y(self, y):
        span = config.CUE_BOTTOM - config.CUE_TOP
        return power_from_drag((y - config.CUE_TOP) / span)

    def _recompute_aim(self, coarse_dir):
        self.aim_dir = apply_fine_tune(coarse_dir[0], coarse_dir[1], self.fine_offset)

    def _fire(self):
        cue = find_cue(self.balls)
        vx, vy = velocity_from_aim(self.aim_dir[0], self.aim_dir[1], self.power)
        cue.vx, cue.vy = vx, vy
        self.sound.play_cue_hit()
        dx, dy = self.english
        cue.spin_v = -dy             # 红点偏上(dy<0)=跟杆(+)
        cue.spin_s = dx              # 红点偏右(dx>0)=右塞(+)
        self.shot_events = []
        # 斯诺克：出杆前拍整桌快照，供对手解球失败后 F 复位；自己出杆清除上一轮资格
        if self.mode == 'snooker':
            self._snooker_pre_shot = {
                'balls': [(b.number, b.x, b.y, b.vx, b.vy, b.on_table) for b in self.balls],
                'phase': self._snooker_phase,
                'next_color': self._snooker_next_color,
                'current': self.current,
            }
        self._can_replay = False
        # 在物理推进（移除落袋球）之前，快照本杆是否处于"打8号"阶段
        self.shot_on_eight = self._shooter_on_eight()
        # 9球：快照击球前台面最小号球（物理推进后会移除落袋球，不能事后判断）
        if self.mode == 'nine':
            self._lowest_on_table = min(
                (b.number for b in self.balls if b.on_table and b.number != 0),
                default=None,
            )
        self.charging = False
        self.power = 0.0
        self.aiming = False
        self.fine_offset = 0.0       # 每打完一球微调杆归回中间
        self.english = (0.0, 0.0)    # 出杆后杆法归零
        self.spin_panel_open = False # 出杆后自动收起放大面板
        self.dragging_spin = False
        self._was_ball_in_hand = (self.place_mode == 'free')  # 快照是否自由球出杆
        self.place_mode = None       # 出杆后摆球特权失效
        self._was_free_ball = self.free_ball   # 快照本杆是否自由球(resolve 时用)
        self.free_ball = False       # 出杆后自由球特权失效
        self.state = STATE_MOVING

    # ---- 事件处理 ----
    def handle_event(self, ev, mouse_pos):
        if self.state == STATE_GAMEOVER:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                self.reset()
            return

        if self.state == STATE_BREAK_PLACE:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                valid = self._snooker_d_valid(*mouse_pos) if self.mode == 'snooker' else self._kitchen_valid(*mouse_pos)
                if valid:
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

        # 僵局:斯诺克瞄准时按 G 重新摆球(跨局胜场保留)
        if (self.state == STATE_AIMING and self.mode == 'snooker'
                and ev.type == pygame.KEYDOWN and ev.key == pygame.K_g):
            self.reset()
            self.message = "僵局：重新摆球，按原顺序重赛"
            return

        # F 复位:做斯诺克方让解球失败的对手在原局面重打
        if (self.state == STATE_AIMING and self.mode == 'snooker'
                and self._can_replay and self._snooker_pre_shot is not None
                and ev.type == pygame.KEYDOWN and ev.key == pygame.K_f):
            self._replay_after_miss()
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
                self._slider_prev_y = my
                self._recompute_aim(self.coarse_dir)
            elif self._in_aim_zone(mx, my):
                self.aiming = True         # 按住才瞄准，瞄准线立即朝向鼠标
                self.fine_offset = 0.0     # 重新瞄准时重置微调
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
            new_events = physics.step(self.balls, self.table)
            self.shot_events.extend(new_events)
            # Play sounds for physics events
            for e in new_events:
                if e.type == 'pocketed':
                    self.sound.play_pocket()
                elif e.type == 'ball_hit':
                    self.sound.play_ball_hit()
            if physics.all_stopped(self.balls):
                self.resolve_shot()

    # ---- 绘制 ----
    def draw(self, screen, font, mouse_pos):
        r = config.BALL_RADIUS
        renderer.draw_table(screen)
        renderer.draw_pockets(screen, self.table)
        if self.state == STATE_BREAK_PLACE:
            if self.mode == 'snooker':
                renderer.draw_snooker_d(screen, self.table)
            renderer.draw_head_line(screen, self.table)
            cue = find_cue(self.balls)
            # 始终跟随鼠标，只夹到台面边界内（不过滤合法性，避免卡顿）
            cx = max(self.table.left + r, min(self.table.right - r, mouse_pos[0]))
            cy = max(self.table.top + r, min(self.table.bottom - r, mouse_pos[1]))
            cue.x, cue.y = cx, cy
        if self.state == STATE_BALL_IN_HAND:
            cue = find_cue(self.balls)
            cx = max(self.table.left + r, min(self.table.right - r, mouse_pos[0]))
            cy = max(self.table.top + r, min(self.table.bottom - r, mouse_pos[1]))
            cue.x, cue.y = cx, cy
        renderer.draw_balls(screen, self.balls, font, mode=self.mode)
        if self.state == STATE_AIMING:
            group = self.player_groups[self.current]
            on_eight = self._shooter_on_eight()
            if self.mode == 'nine':
                forbidden = lambda n: not is_legal_nine_ball_contact(n, self.balls)
            elif self.mode == 'snooker':
                if self.free_ball:
                    forbidden = lambda n: n == 0
                else:
                    forbidden = lambda n: not _snooker_legal_contact(
                        n, self._snooker_phase, self._snooker_next_color)
            else:
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
        renderer.draw_hud(screen, font, self.player_groups, self.current, self.message,
                          mode=self.mode,
                          snooker_scores=self._snooker_scores if self.mode == 'snooker' else None,
                          can_replay=self._can_replay)
        renderer.draw_score(screen, font, self.scores)
        if self.state == STATE_GAMEOVER:
            renderer.draw_gameover(screen, font, self.winner)


PAUSE_BUTTONS = [
    ('continue', '继续'),
    ('restart', '重新开始'),
    ('quit', '退出'),
]


def _pause_button_rects():
    """暂停菜单三个按钮的矩形。"""
    w, h = config.MENU_BTN_W, config.MENU_BTN_H
    step = h + config.MENU_BTN_GAP
    x = (config.WINDOW_WIDTH - w) // 2
    rects = []
    n = len(PAUSE_BUTTONS)
    for i, (bid, label) in enumerate(PAUSE_BUTTONS):
        cy = config.WINDOW_HEIGHT // 2 + (i - (n - 1) / 2) * step
        y = round(cy) - h // 2
        rects.append((bid, label, x, y, w, h))
    return rects


def _pause_button_at(x, y):
    for bid, _label, bx, by, w, h in _pause_button_rects():
        if bx <= x <= bx + w and by <= y <= by + h:
            return bid
    return None


def main():
    pygame.init()
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    pygame.display.set_caption("2D台球游戏")
    font = pygame.font.SysFont('arialunicode,heitisc,pingfangsc,arial', 22)
    title_font = pygame.font.SysFont('arialunicode,heitisc,pingfangsc,arial', 64)
    clock = pygame.time.Clock()

    table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                  config.TABLE_RIGHT, config.TABLE_BOTTOM)
    scene = 'menu'      # 'menu' 封面 / 'game' 对局
    game = None
    paused = False
    sound = sounds.SoundManager()  # 全局音效，菜单和对局共用
    hint_text = ""      # 封面临时提示文字，空串=不显示
    hint_until = 0      # 提示到期时间戳（ms, pygame.time.get_ticks）

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
                sound.muted = not sound.muted
            if scene == 'menu':
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    clicked = menu.button_at(*mouse_pos)
                    if clicked is not None:
                        sound.play_btn_click()
                    if clicked == 'eight':
                        game = Game(sound=sound)          # 全新一局，比分清零
                        scene = 'game'
                        hint_text = ""         # 进游戏即清除残留提示
                        hint_until = 0
                    elif clicked == 'nine':
                        game = Game(mode='nine', sound=sound)
                        scene = 'game'
                        hint_text = ""
                        hint_until = 0
                    elif clicked == 'snooker':
                        game = Game(mode='snooker', sound=sound)
                        scene = 'game'
                        hint_text = ""
                        hint_until = 0
            else:  # scene == 'game'
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    paused = not paused
                elif not paused:
                    game.handle_event(ev, mouse_pos)
                elif paused and ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    # 暂停菜单按钮处理
                    btn = _pause_button_at(*mouse_pos)
                    if btn is not None:
                        sound.play_btn_click()
                    if btn == 'continue':
                        paused = False
                    elif btn == 'restart':
                        game.reset()
                        paused = False
                    elif btn == 'quit':
                        scene = 'menu'
                        game = None
                        paused = False

        if scene == 'game' and game is not None and not paused:
            game.update()

        if scene == 'menu':
            renderer.draw_menu(screen, font, title_font, table)
            if hint_text and pygame.time.get_ticks() < hint_until:
                renderer.draw_menu_hint(screen, font, hint_text)
            else:
                hint_text = ""   # 到期清空
            renderer.draw_mute_indicator(screen, font, sound.muted)
        else:
            game.draw(screen, font, mouse_pos)
            renderer.draw_back_hint(screen, font)
            renderer.draw_mute_indicator(screen, font, game.sound.muted)
            if paused:
                renderer.draw_pause_menu(screen, font)

        pygame.display.flip()
        clock.tick(config.FPS)


if __name__ == '__main__':
    main()
