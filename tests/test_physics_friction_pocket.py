import config
from balls import Ball
from table import Table
from physics import apply_friction, check_pocket, all_stopped


def make_table():
    return Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)


def test_friction_slows_and_eventually_stops():
    b = Ball(number=1, x=0.0, y=0.0, vx=1.0, vy=0.0)
    apply_friction(b)
    assert abs(b.vx) < 1.0 and b.vx > 0          # 减速但未停
    b.vx = 0.01                                  # 低于阈值
    apply_friction(b)
    assert b.vx == 0.0 and b.vy == 0.0           # 归零


def test_check_pocket_detects_ball_in_pocket_radius():
    t = make_table()
    pockets = t.pocket_positions()
    px, py = pockets[0]
    b = Ball(number=3, x=px + 2.0, y=py + 2.0)   # 袋口附近
    assert check_pocket(b, pockets) == 0
    far = Ball(number=4, x=(t.left + t.right) / 2, y=t.center_y)
    assert check_pocket(far, pockets) is None


def test_all_stopped_ignores_off_table_balls():
    moving = Ball(number=1, x=0.0, y=0.0, vx=2.0, vy=0.0)
    still = Ball(number=2, x=10.0, y=0.0, vx=0.0, vy=0.0)
    assert all_stopped([moving, still]) is False
    moving.vx = 0.0
    assert all_stopped([moving, still]) is True
    pocketed = Ball(number=3, x=0.0, y=0.0, vx=9.0, vy=0.0, on_table=False)
    assert all_stopped([moving, still, pocketed]) is True  # 不在台的球被忽略
