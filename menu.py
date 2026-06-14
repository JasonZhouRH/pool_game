"""封面菜单的纯几何逻辑：按钮矩形与命中判定。无任何 pygame 依赖。"""
import config


def button_rect():
    """返回"8球模式"按钮矩形 (x, y, w, h)，水平居中、中心 y = MENU_BTN_CY。"""
    w, h = config.MENU_BTN_W, config.MENU_BTN_H
    x = (config.WINDOW_WIDTH - w) // 2
    y = config.MENU_BTN_CY - h // 2
    return (x, y, w, h)


def button_hit(x, y):
    """点击坐标 (x, y) 是否落在按钮矩形内（含边界）。"""
    bx, by, w, h = button_rect()
    return bx <= x <= bx + w and by <= y <= by + h
