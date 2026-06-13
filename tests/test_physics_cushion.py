import config
from balls import Ball
from table import Table
from physics import resolve_cushion


def make_table():
    return Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)


def test_left_wall_reverses_x_and_clamps():
    t = make_table()
    b = Ball(number=1, x=t.left - 5.0, y=t.center_y, vx=-4.0, vy=0.0)
    hit = resolve_cushion(b, t, restitution=1.0)
    assert hit is True
    assert b.vx > 0                       # x 速度反向
    assert b.x >= t.left + b.radius - 1e-6  # 被夹回界内


def test_no_hit_when_inside():
    t = make_table()
    b = Ball(number=1, x=(t.left + t.right) / 2, y=t.center_y, vx=3.0, vy=0.0)
    assert resolve_cushion(b, t, restitution=1.0) is False


def test_bottom_wall_reverses_y_with_energy_loss():
    t = make_table()
    b = Ball(number=1, x=(t.left + t.right) / 2, y=t.bottom + 3.0, vx=0.0, vy=5.0)
    assert resolve_cushion(b, t, restitution=0.5) is True
    assert b.vy < 0
    assert abs(b.vy) < 5.0                # 有能量损失


def test_cue_side_english_adds_tangential_on_vertical_wall():
    # 母球带右塞撞左库（竖直库），反弹后应产生 y 方向切向速度
    t = make_table()
    cue = Ball(number=0, x=t.left - 5.0, y=t.center_y, vx=-4.0, vy=0.0, spin_s=1.0)
    assert resolve_cushion(cue, t, restitution=1.0) is True
    assert abs(cue.vy) > 1e-6          # 出现切向速度
    assert cue.spin_s == 0.0           # 已消费


def test_cue_side_english_adds_tangential_on_horizontal_wall():
    # 母球带塞撞下库（水平库），反弹后应产生 x 方向切向速度
    t = make_table()
    cue = Ball(number=0, x=(t.left + t.right) / 2, y=t.bottom + 3.0,
               vx=0.0, vy=5.0, spin_s=1.0)
    assert resolve_cushion(cue, t, restitution=1.0) is True
    assert abs(cue.vx) > 1e-6
    assert cue.spin_s == 0.0


def test_side_english_ignored_for_non_cue_ball():
    # 非母球带 spin_s 碰库不产生切向偏移，也不清零
    t = make_table()
    obj = Ball(number=1, x=t.left - 5.0, y=t.center_y, vx=-4.0, vy=0.0, spin_s=1.0)
    resolve_cushion(obj, t, restitution=1.0)
    assert abs(obj.vy) < 1e-6
    assert obj.spin_s == 1.0
