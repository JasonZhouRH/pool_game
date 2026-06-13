import config
from balls import Ball
from physics import resolve_ball_collision


def test_head_on_equal_mass_swaps_velocity():
    # a 向右撞静止的 b，弹性(e=1) 应交换法向速度
    a = Ball(number=1, x=0.0, y=0.0, vx=5.0, vy=0.0)
    b = Ball(number=2, x=2 * config.BALL_RADIUS - 1.0, y=0.0)  # 略重叠
    hit = resolve_ball_collision(a, b, restitution=1.0)
    assert hit is True
    assert abs(a.vx) < 1e-6          # a 停下
    assert abs(b.vx - 5.0) < 1e-6    # b 获得 5
    # 位置去重叠：两球中心距应 >= 直径
    assert (b.x - a.x) >= 2 * config.BALL_RADIUS - 1e-6


def test_separating_balls_do_not_collide():
    a = Ball(number=1, x=0.0, y=0.0, vx=-5.0, vy=0.0)   # 向左，远离 b
    b = Ball(number=2, x=2 * config.BALL_RADIUS - 1.0, y=0.0, vx=0.0)
    assert resolve_ball_collision(a, b, restitution=1.0) is False


def test_far_apart_balls_do_not_collide():
    a = Ball(number=1, x=0.0, y=0.0, vx=5.0, vy=0.0)
    b = Ball(number=2, x=100.0, y=0.0)
    assert resolve_ball_collision(a, b, restitution=1.0) is False


def test_cue_stun_stops_on_head_on_when_spin_v_zero():
    # 定杆正撞：母球停（与旧的等质量交换一致），spin 清零
    cue = Ball(number=0, x=0.0, y=0.0, vx=5.0, vy=0.0, spin_v=0.0)
    obj = Ball(number=1, x=2 * config.BALL_RADIUS - 1.0, y=0.0)
    assert resolve_ball_collision(cue, obj, restitution=1.0) is True
    assert abs(cue.vx) < 1e-6
    assert cue.spin_v == 0.0


def test_cue_follow_continues_forward():
    # 跟杆正撞：母球碰后仍向 +x 前进
    cue = Ball(number=0, x=0.0, y=0.0, vx=5.0, vy=0.0, spin_v=1.0)
    obj = Ball(number=1, x=2 * config.BALL_RADIUS - 1.0, y=0.0)
    resolve_ball_collision(cue, obj, restitution=1.0)
    assert cue.vx > 1e-6
    assert cue.spin_v == 0.0          # 已消费


def test_cue_draw_pulls_backward():
    # 缩杆正撞：母球碰后向 -x 回退
    cue = Ball(number=0, x=0.0, y=0.0, vx=5.0, vy=0.0, spin_v=-1.0)
    obj = Ball(number=1, x=2 * config.BALL_RADIUS - 1.0, y=0.0)
    resolve_ball_collision(cue, obj, restitution=1.0)
    assert cue.vx < -1e-6
    assert cue.spin_v == 0.0


def test_follow_draw_skipped_when_no_cue_involved():
    # 两颗目标球相撞：即便带 spin_v 也不应用（只有母球吃杆法）
    a = Ball(number=1, x=0.0, y=0.0, vx=5.0, vy=0.0, spin_v=1.0)
    b = Ball(number=2, x=2 * config.BALL_RADIUS - 1.0, y=0.0)
    resolve_ball_collision(a, b, restitution=1.0)
    assert abs(a.vx) < 1e-6           # 仍是普通等质量交换
    assert a.spin_v == 1.0            # 非母球，不消费


def test_cue_follow_vs_draw_on_cut_shifts_along_impact_normal():
    # 切球：跟杆使母球碰后沿冲击法线(母球→目标球)分量更大，缩杆更小
    import math
    R = config.BALL_RADIUS

    def run(spin_v):
        cue = Ball(number=0, x=0.0, y=0.0, vx=5.0, vy=0.0, spin_v=spin_v)
        # 目标球偏移 y，形成约 30° 切角；中心距略小于 2R 触发碰撞
        obj = Ball(number=1, x=(2 * R - 1.0) * math.cos(math.radians(30)),
                   y=(2 * R - 1.0) * math.sin(math.radians(30)))
        dx, dy = obj.x - cue.x, obj.y - cue.y
        d = math.hypot(dx, dy)
        nx, ny = dx / d, dy / d        # 冲击法线：母球→目标球
        resolve_ball_collision(cue, obj, restitution=1.0)
        return cue.vx * nx + cue.vy * ny   # 母球速度在法线上的投影

    stun = run(0.0)
    follow = run(1.0)
    draw = run(-1.0)
    assert follow > stun + 1e-6       # 跟杆：法向分量更大（更朝目标球方向走）
    assert draw < stun - 1e-6         # 缩杆：法向分量更小（朝反方向）
