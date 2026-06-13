import config
from table import Table
from balls import Ball, group_of, ball_color, create_standard_balls, find_cue


def make_table():
    return Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)


def test_group_of_classifies_numbers():
    assert group_of(0) == 'cue'
    assert group_of(1) == 'solid'
    assert group_of(7) == 'solid'
    assert group_of(8) == 'eight'
    assert group_of(9) == 'stripe'
    assert group_of(15) == 'stripe'


def test_ball_color_specials():
    assert ball_color(0) == config.COLOR_CUE
    assert ball_color(8) == config.COLOR_EIGHT
    assert ball_color(1) == config.BALL_BASE_COLORS[1]
    # 花色复用同色相
    assert ball_color(9) == config.BALL_BASE_COLORS[1]


def test_standard_set_has_cue_plus_15_objects():
    balls = create_standard_balls(make_table())
    numbers = sorted(b.number for b in balls)
    assert numbers == list(range(16))      # 0..15
    cue = find_cue(balls)
    assert cue is not None and cue.number == 0


def test_eight_ball_is_center_of_third_rack_row():
    balls = create_standard_balls(make_table())
    rack = make_table().rack_positions()
    eight = next(b for b in balls if b.number == 8)
    # 第三列(列索引2)的中间位置 = rack 索引 4
    assert abs(eight.x - rack[4][0]) < 1e-6
    assert abs(eight.y - rack[4][1]) < 1e-6


def test_ball_spin_components_default_zero():
    b = Ball(number=0, x=0.0, y=0.0)
    assert b.spin_v == 0.0     # 垂直杆法：跟杆(+)/缩杆(-)
    assert b.spin_s == 0.0     # 水平塞：右塞(+)/左塞(-)
    assert not hasattr(b, 'spin')   # 旧单字段已移除
