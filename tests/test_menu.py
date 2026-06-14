import config
import menu


def test_buttons_ids_and_labels_in_order():
    rects = menu.button_rects()
    assert [r[0] for r in rects] == ['eight', 'nine', 'snooker']
    assert [r[1] for r in rects] == ['8球模式', '9球模式', '斯诺克']


def test_button_rects_inside_window():
    for _id, _label, x, y, w, h in menu.button_rects():
        assert w == config.MENU_BTN_W and h == config.MENU_BTN_H
        assert x >= 0 and y >= 0
        assert x + w <= config.WINDOW_WIDTH
        assert y + h <= config.WINDOW_HEIGHT


def test_button_rects_horizontally_centered():
    for _id, _label, x, _y, w, _h in menu.button_rects():
        assert abs((x + w / 2) - config.WINDOW_WIDTH / 2) < 1e-6


def test_button_rects_no_vertical_overlap():
    rects = sorted(menu.button_rects(), key=lambda r: r[3])  # 按 y 排序
    for (a, b) in zip(rects, rects[1:]):
        a_bottom = a[3] + a[5]   # a.y + a.h
        b_top = b[3]
        assert a_bottom <= b_top


def test_button_at_center_returns_id():
    for _id, _label, x, y, w, h in menu.button_rects():
        cx, cy = x + w // 2, y + h // 2
        assert menu.button_at(cx, cy) == _id


def test_button_at_gap_returns_none():
    rects = sorted(menu.button_rects(), key=lambda r: r[3])
    # 相邻两按钮之间的竖向空隙中点
    a, b = rects[0], rects[1]
    gap_y = (a[3] + a[5] + b[3]) // 2   # (a 底 + b 顶) / 2
    cx = config.WINDOW_WIDTH // 2
    assert menu.button_at(cx, gap_y) is None


def test_button_at_corners_return_none():
    assert menu.button_at(0, 0) is None
    assert menu.button_at(config.WINDOW_WIDTH, config.WINDOW_HEIGHT) is None
