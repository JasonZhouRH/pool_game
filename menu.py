"""封面菜单的纯几何逻辑：按钮列表、矩形与命中判定。无任何 pygame 依赖。"""
import config

# 竖排顺序（上→下）：(id, 标签)
BUTTONS = [
    ('eight', '8球模式'),
    ('nine', '9球模式'),
    ('snooker', '斯诺克'),
]


def button_rects():
    """返回按钮列表 [(id, label, x, y, w, h), ...]。

    三个矩形水平居中、竖排；垂直方向整体围绕 config.MENU_BTN_CY 居中，
    相邻按钮中心间距 = 按钮高 + config.MENU_BTN_GAP。
    """
    w, h = config.MENU_BTN_W, config.MENU_BTN_H
    n = len(BUTTONS)
    step = h + config.MENU_BTN_GAP
    x = (config.WINDOW_WIDTH - w) // 2
    rects = []
    for i, (bid, label) in enumerate(BUTTONS):
        cy = config.MENU_BTN_CY + (i - (n - 1) / 2) * step
        y = round(cy) - h // 2
        rects.append((bid, label, x, y, w, h))
    return rects


def button_at(x, y):
    """命中某个按钮则返回其 id，否则返回 None（含边界算命中）。"""
    for bid, _label, bx, by, w, h in button_rects():
        if bx <= x <= bx + w and by <= y <= by + h:
            return bid
    return None
