import config
import menu


def test_button_rect_inside_window():
    x, y, w, h = menu.button_rect()
    assert w == config.MENU_BTN_W and h == config.MENU_BTN_H
    assert x >= 0 and y >= 0
    assert x + w <= config.WINDOW_WIDTH
    assert y + h <= config.WINDOW_HEIGHT


def test_button_rect_horizontally_centered():
    x, _, w, _ = menu.button_rect()
    # 矩形中心 x 等于窗口中心 x
    assert abs((x + w / 2) - config.WINDOW_WIDTH / 2) < 1e-6


def test_button_hit_center_true():
    assert menu.button_hit(config.WINDOW_WIDTH // 2, config.MENU_BTN_CY) is True


def test_button_hit_outside_false():
    x, y, w, h = menu.button_rect()
    assert menu.button_hit(x - 5, y + h // 2) is False        # 左外
    assert menu.button_hit(x + w + 5, y + h // 2) is False     # 右外
    assert menu.button_hit(x + w // 2, y - 5) is False         # 上外
    assert menu.button_hit(x + w // 2, y + h + 5) is False     # 下外


def test_button_hit_edges_inclusive():
    x, y, w, h = menu.button_rect()
    assert menu.button_hit(x, y) is True                       # 左上角
    assert menu.button_hit(x + w, y + h) is True               # 右下角
