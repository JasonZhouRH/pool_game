import config
from table import Table


def make_table():
    return Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)


def test_six_pockets_at_corners_and_long_rail_mids():
    t = make_table()
    pockets = t.pocket_positions()
    assert len(pockets) == 6
    mid_x = (config.TABLE_LEFT + config.TABLE_RIGHT) / 2
    # 四角 + 上下长边中点
    assert (config.TABLE_LEFT, config.TABLE_TOP) in pockets
    assert (config.TABLE_RIGHT, config.TABLE_BOTTOM) in pockets
    assert (mid_x, config.TABLE_TOP) in pockets
    assert (mid_x, config.TABLE_BOTTOM) in pockets


def test_rack_has_15_positions_inside_table():
    t = make_table()
    rack = t.rack_positions()
    assert len(rack) == 15
    for (x, y) in rack:
        assert config.TABLE_LEFT < x < config.TABLE_RIGHT
        assert config.TABLE_TOP < y < config.TABLE_BOTTOM


def test_head_spot_is_left_quarter_on_center_line():
    t = make_table()
    hx, hy = t.head_spot()
    assert abs(hy - t.center_y) < 1e-6
    expected_x = config.TABLE_LEFT + 0.25 * (config.TABLE_RIGHT - config.TABLE_LEFT)
    assert abs(hx - expected_x) < 1e-6


def test_head_line_x_matches_head_spot_x():
    t = make_table()
    assert abs(t.head_line_x() - t.head_spot()[0]) < 1e-6
    assert config.TABLE_LEFT < t.head_line_x() < config.TABLE_RIGHT
