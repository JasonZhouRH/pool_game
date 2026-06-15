"""所有绘制：球台、球、瞄准线、左微调滑条/右蓄力球杆、HUD、结束横幅。只读状态，不修改。"""
import pygame

import config
import menu
from balls import group_of, ball_color
from cue import predict_aim

GROUP_LABEL = {'solid': '全色', 'stripe': '花色', None: '未定'}


def draw_table(screen):
    screen.fill(config.COLOR_BG)

    L, T = config.TABLE_LEFT, config.TABLE_TOP
    R, B = config.TABLE_RIGHT, config.TABLE_BOTTOM

    # 库边主体：比台呢大一圈的圆角矩形
    rail = pygame.Rect(L - 36, T - 36, R - L + 72, B - T + 72)
    pygame.draw.rect(screen, config.COLOR_RAIL, rail, border_radius=22)

    # 内沿立体斜边：圆角矩形描边，高光+阴影偏移叠加
    inset = 18
    inner = pygame.Rect(L - inset, T - inset, R - L + inset * 2, B - T + inset * 2)
    # 圆角描边，偏左上高光 + 偏右下阴影叠加
    pygame.draw.rect(screen, config.COLOR_RAIL_HIGHLIGHT, inner, 3, border_radius=10)
    shadow_inner = inner.move(2, 2)
    pygame.draw.rect(screen, config.COLOR_RAIL_SHADOW, shadow_inner, 3, border_radius=10)

    # 台呢
    felt = pygame.Rect(L, T, R - L, B - T)
    pygame.draw.rect(screen, config.COLOR_FELT, felt)


def draw_pockets(screen, table):
    for (px, py) in table.pocket_positions():
        pygame.draw.circle(screen, config.COLOR_POCKET, (int(px), int(py)), config.POCKET_RADIUS)


def draw_balls(screen, balls, font):
    r = config.BALL_RADIUS
    for b in balls:
        if not b.on_table:
            continue
        cx, cy = int(b.x), int(b.y)
        pygame.draw.circle(screen, ball_color(b.number), (cx, cy), r)
        if group_of(b.number) == 'stripe':
            band = pygame.Rect(0, 0, 2 * r, int(r * 0.9))
            band.center = (cx, cy)
            pygame.draw.rect(screen, config.COLOR_STRIPE_BAND, band)
        if b.number != 0:
            txt = font.render(str(b.number), True, (0, 0, 0))
            screen.blit(txt, txt.get_rect(center=(cx, cy)))
        pygame.draw.circle(screen, (0, 0, 0), (cx, cy), r, 1)


def draw_aim(screen, cue, aim_dir, balls=None, spin_v=0.0, is_forbidden=None):
    """瞄准线（朝 aim_dir 单位方向）+ 分离角预测。aim_dir 为母球去向。

    spin_v: 垂直杆法，传入 predict_aim 改变母球分离方向（跟/定/缩杆）。
    is_forbidden: 可选回调 number->bool，命中球非法时鬼球画成红圈 + 斜杠。
    """
    if aim_dir is None:
        return
    ux, uy = aim_dir
    # 分离角预测：母球射线若撞到球，瞄准线止于鬼球，并画出分叉路径
    pred = predict_aim(cue.x, cue.y, ux, uy, balls, spin_v=spin_v) if balls else None
    if pred is None:
        # 未命中：固定长度瞄准线
        end = (int(cue.x + ux * 220), int(cue.y + uy * 220))
        pygame.draw.line(screen, config.COLOR_LINE, (int(cue.x), int(cue.y)), end, 1)
    else:
        forbidden = bool(is_forbidden and is_forbidden(pred.target_number))
        _draw_separation(screen, cue, pred, forbidden)


def draw_fine_slider(screen, font, fine_offset):
    """左侧竖直微调滑条。fine_offset 无上下界，视觉滑块循环 wrap。"""
    x = config.SLIDER_X
    top, bottom = config.SLIDER_TOP, config.SLIDER_BOTTOM
    pygame.draw.line(screen, config.COLOR_SLIDER_TRACK, (x, top), (x, bottom), 4)
    # 中点刻度（fine=0）
    mid = (top + bottom) // 2
    pygame.draw.line(screen, config.COLOR_SLIDER_TRACK, (x - 8, mid), (x + 8, mid), 2)
    # 视觉位置 wrap：fine_offset 映射回 [-1, 1]
    wrapped = ((fine_offset + 1.0) % 2.0) - 1.0
    knob_y = int(top + (wrapped + 1) / 2 * (bottom - top))
    pygame.draw.circle(screen, config.COLOR_SLIDER_KNOB, (x, knob_y), config.SLIDER_KNOB_R)
    pygame.draw.circle(screen, (0, 0, 0), (x, knob_y), config.SLIDER_KNOB_R, 1)
    label = font.render("微调", True, config.COLOR_TEXT)
    screen.blit(label, label.get_rect(center=(x, top - 18)))


def draw_power_cue(screen, font, power, charging):
    """右侧竖直球杆蓄力槽。power ∈ [0, 1]，越往下退力越大。"""
    x = config.CUE_X
    top, bottom = config.CUE_TOP, config.CUE_BOTTOM
    # 槽背景
    pygame.draw.line(screen, config.COLOR_SLIDER_TRACK, (x, top), (x, bottom), 4)
    grip_y = int(top + power * (bottom - top))   # 握把随蓄力下移
    # 球杆：皮头朝上（指向球台），握把在下；蓄力越大整体越往下退
    tip_y = top - 70 + int(power * 40)
    pygame.draw.line(screen, config.COLOR_CUE_STICK, (x, tip_y + 12), (x, grip_y + 40), 8)
    pygame.draw.line(screen, config.COLOR_CUE_TIP, (x, tip_y), (x, tip_y + 12), 8)
    # 握把指示块
    pygame.draw.circle(screen, config.COLOR_CUE_STICK, (x, grip_y), config.CUE_GRAB_R)
    pygame.draw.circle(screen, (0, 0, 0), (x, grip_y), config.CUE_GRAB_R, 1)
    pct = font.render(f"{int(power * 100)}%", True, config.COLOR_TEXT)
    screen.blit(pct, pct.get_rect(center=(x, bottom + 20)))
    label = font.render("蓄力", True, config.COLOR_TEXT)
    screen.blit(label, label.get_rect(center=(x, top - 18)))


def draw_spin_icon(screen, english):
    """右上角小白球图标：球面 + 反映当前打点的红点。english=(dx,dy) 归一化偏移。"""
    cx, cy, r = config.SPIN_ICON_X, config.SPIN_ICON_Y, config.SPIN_ICON_R
    pygame.draw.circle(screen, config.COLOR_SPIN_BALL, (cx, cy), r)
    pygame.draw.circle(screen, config.COLOR_SPIN_RING, (cx, cy), r, 1)
    dx, dy = english
    dot = (int(cx + dx * (r - 3)), int(cy + dy * (r - 3)))
    pygame.draw.circle(screen, config.COLOR_SPIN_DOT, dot, 3)


def draw_spin_panel(screen, font, english):
    """放大白球面板：十字参考 + 可拖红点。english=(dx,dy) 归一化偏移。"""
    cx, cy, r = config.SPIN_PANEL_X, config.SPIN_PANEL_Y, config.SPIN_PANEL_R
    pygame.draw.circle(screen, config.COLOR_SPIN_BALL, (cx, cy), r)
    pygame.draw.circle(screen, config.COLOR_SPIN_RING, (cx, cy), r, 2)
    # 十字参考线（球心 = 定杆）
    pygame.draw.line(screen, config.COLOR_SPIN_RING, (cx - r, cy), (cx + r, cy), 1)
    pygame.draw.line(screen, config.COLOR_SPIN_RING, (cx, cy - r), (cx, cy + r), 1)
    dx, dy = english
    dot = (int(cx + dx * r), int(cy + dy * r))
    pygame.draw.circle(screen, config.COLOR_SPIN_DOT, dot, config.SPIN_DOT_R)
    pygame.draw.circle(screen, config.COLOR_SPIN_RING, dot, config.SPIN_DOT_R, 1)
    label = font.render("杆法", True, config.COLOR_TEXT)
    screen.blit(label, label.get_rect(center=(cx, cy - r - 14)))


def _draw_separation(screen, cue, pred, forbidden=False):
    """瞄准线止于鬼球，鬼球处画轮廓圈 + 目标球进球路径。

    forbidden=True 时鬼球画成红圈 + 对角斜杠（非法首球提示）。
    """
    r = config.BALL_RADIUS
    gx, gy = int(pred.ghost_x), int(pred.ghost_y)
    # 瞄准线：母球 → 鬼球接触点
    pygame.draw.line(screen, config.COLOR_LINE,
                     (int(cue.x), int(cue.y)), (gx, gy), 1)
    # 鬼球：母球撞击瞬间位置的空心轮廓（非法时变红并叠加禁止斜杠）
    ring_color = config.COLOR_GHOST_FORBIDDEN if forbidden else config.COLOR_GHOST
    pygame.draw.circle(screen, ring_color, (gx, gy), r, 1)
    if forbidden:
        off = round(r * 0.707)   # 对角斜杠端点（圆上 45°）
        pygame.draw.line(screen, config.COLOR_GHOST_FORBIDDEN,
                         (gx - off, gy + off), (gx + off, gy - off), 2)
    # 目标球路径：沿连心线方向
    ox, oy = pred.object_dir
    pygame.draw.line(screen, config.COLOR_OBJECT_PATH, (gx, gy),
                     (int(gx + ox * 160), int(gy + oy * 160)), 2)


def draw_head_line(screen, table):
    """竖直开球线（厨房线）：实线，其左侧为开球摆球区。"""
    x = int(table.head_line_x())
    pygame.draw.line(screen, config.COLOR_HEAD_LINE,
                     (x, int(table.top)), (x, int(table.bottom)), 2)


def draw_hud(screen, font, player_groups, current_player, message, mode='eight'):
    marker = ['  ', '  ']
    marker[current_player] = '▶ '

    if mode == 'nine':
        line1 = f"{marker[0]}玩家1          {marker[1]}玩家2"
    else:
        p1 = GROUP_LABEL[player_groups[0]]
        p2 = GROUP_LABEL[player_groups[1]]
        line1 = f"{marker[0]}玩家1: {p1}      {marker[1]}玩家2: {p2}"

    screen.blit(font.render(line1, True, config.COLOR_TEXT), (40, 20))
    if message:
        screen.blit(font.render(message, True, config.COLOR_TEXT), (40, 52))


def draw_score(screen, font, scores):
    """顶部正中累计胜场比分。scores=[玩家1胜场, 玩家2胜场]，跨局保留。"""
    txt = font.render(f"比分  {scores[0]} : {scores[1]}", True, config.COLOR_TEXT)
    screen.blit(txt, txt.get_rect(center=(config.WINDOW_WIDTH // 2, 30)))


def draw_ball_in_hand_hint(screen, font):
    txt = font.render("自由球：移动鼠标放置母球，点击确定", True, config.COLOR_TEXT)
    screen.blit(txt, (40, config.WINDOW_HEIGHT - 30))


def draw_gameover(screen, font, winner_player):
    overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    msg = f"玩家{winner_player + 1} 获胜！  按 R 重新开始"
    txt = font.render(msg, True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=(config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)))


def draw_menu(screen, font, title_font, table):
    """封面：台面背景 + 半透明遮罩 + 居中标题 + 竖排模式按钮。"""
    draw_table(screen)
    draw_pockets(screen, table)
    overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill(config.COLOR_MENU_OVERLAY)
    screen.blit(overlay, (0, 0))
    rects = menu.button_rects()
    # 标题：最上面按钮的上方（midbottom 锚点，留白不随字体高度变化）
    top = min(y for _bid, _label, _x, y, _w, _h in rects)
    title = title_font.render(config.MENU_TITLE, True, config.COLOR_MENU_TITLE)
    screen.blit(title, title.get_rect(midbottom=(config.WINDOW_WIDTH // 2, top - 24)))
    # 按钮（竖排三个）
    for _bid, label_text, x, y, w, h in rects:
        pygame.draw.rect(screen, config.COLOR_MENU_BTN, (x, y, w, h), border_radius=12)
        pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2, border_radius=12)
        label = font.render(label_text, True, config.COLOR_MENU_BTN_TEXT)
        screen.blit(label, label.get_rect(center=(x + w // 2, y + h // 2)))


def draw_back_hint(screen, font):
    """对局界面右下角小灰字：提示按 ESC 返回主界面。"""
    txt = font.render("ESC 菜单", True, config.COLOR_TEXT)
    screen.blit(txt, txt.get_rect(bottomright=(config.WINDOW_WIDTH - 20, config.WINDOW_HEIGHT - 14)))


def draw_menu_hint(screen, font, text):
    """封面临时提示：按钮区下方居中一行字。text 为空则不画。"""
    if not text:
        return
    # 提示画在最下面一个按钮的下方
    rects = menu.button_rects()
    bottom = max(y + h for _bid, _label, _x, y, _w, h in rects)
    txt = font.render(text, True, config.COLOR_MENU_HINT)
    screen.blit(txt, txt.get_rect(center=(config.WINDOW_WIDTH // 2, bottom + 30)))


def draw_mute_indicator(screen, font, muted):
    """左下角静音指示。"""
    txt = font.render("静音" if muted else "音效", True, config.COLOR_TEXT)
    screen.blit(txt, txt.get_rect(bottomleft=(20, config.WINDOW_HEIGHT - 14)))


def draw_pause_menu(screen, font):
    """暂停菜单：半透明遮罩 + 三个按钮。"""
    overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    # 按钮布局与封面菜单一致
    labels = ['继续', '重新开始', '退出']
    w, h = config.MENU_BTN_W, config.MENU_BTN_H
    step = h + config.MENU_BTN_GAP
    x = (config.WINDOW_WIDTH - w) // 2
    n = len(labels)
    for i, label in enumerate(labels):
        cy = config.WINDOW_HEIGHT // 2 + (i - (n - 1) / 2) * step
        y = round(cy) - h // 2
        pygame.draw.rect(screen, config.COLOR_MENU_BTN, (x, y, w, h), border_radius=12)
        pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2, border_radius=12)
        txt = font.render(label, True, config.COLOR_MENU_BTN_TEXT)
        screen.blit(txt, txt.get_rect(center=(x + w // 2, y + h // 2)))
