from math import acos, atan2, degrees, hypot, isclose, radians

import config
from balls import Ball
from cue import (aim_direction, apply_fine_tune, clamp_english, power_from_drag,
                 predict_aim, velocity_from_aim)


# ---- 粗瞄方向 ----

def test_aim_points_from_cue_toward_mouse():
    # 鼠标在母球右侧，母球应朝右瞄
    d = aim_direction(100, 100, 200, 100)
    assert d is not None
    assert isclose(d[0], 1.0, abs_tol=1e-6)
    assert isclose(d[1], 0.0, abs_tol=1e-6)


def test_aim_is_unit_vector():
    d = aim_direction(0, 0, 30, 40)
    assert isclose(hypot(*d), 1.0, abs_tol=1e-6)


def test_aim_none_when_mouse_on_cue():
    assert aim_direction(100, 100, 100, 100) is None


# ---- 左滑条角度微调 ----

def test_fine_tune_zero_keeps_direction():
    d = apply_fine_tune(1.0, 0.0, 0.0)
    assert isclose(d[0], 1.0, abs_tol=1e-6)
    assert isclose(d[1], 0.0, abs_tol=1e-6)


def test_fine_tune_full_rotates_by_max_degrees():
    # fine=+1 应顺时针旋转 FINE_TUNE_DEG 度
    dx, dy = apply_fine_tune(1.0, 0.0, 1.0)
    assert isclose(degrees(atan2(dy, dx)), config.FINE_TUNE_DEG, abs_tol=1e-6)
    # fine=-1 反向
    dx2, dy2 = apply_fine_tune(1.0, 0.0, -1.0)
    assert isclose(degrees(atan2(dy2, dx2)), -config.FINE_TUNE_DEG, abs_tol=1e-6)


def test_fine_tune_preserves_unit_length():
    d = apply_fine_tune(0.6, 0.8, 0.5)
    assert isclose(hypot(*d), 1.0, abs_tol=1e-6)


# ---- 球杆蓄力 → 力度 → 速度 ----

def test_power_from_drag_clamps():
    assert power_from_drag(-0.2) == 0.0
    assert power_from_drag(0.5) == 0.5
    assert power_from_drag(1.5) == 1.0


def test_velocity_scales_with_power_and_clamps():
    vx, vy = velocity_from_aim(1.0, 0.0, 1.0)
    assert isclose(hypot(vx, vy), config.MAX_SHOT_SPEED, abs_tol=1e-6)
    vx2, vy2 = velocity_from_aim(1.0, 0.0, 0.5)
    assert isclose(hypot(vx2, vy2), config.MAX_SHOT_SPEED / 2, abs_tol=1e-6)
    vx3, vy3 = velocity_from_aim(1.0, 0.0, 0.0)
    assert (vx3, vy3) == (0.0, 0.0)


def test_velocity_keeps_direction():
    # 45° 方向，分量应相等
    inv = 1.0 / (2 ** 0.5)
    vx, vy = velocity_from_aim(inv, inv, 1.0)
    assert isclose(vx, vy, abs_tol=1e-6)


# ---- 分离角几何预测 ----

def _angle_between(a, b):
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    return degrees(acos(dot))


def test_predict_no_hit_returns_none():
    # 目标球在母球射线侧方，沿 +x 打不到
    balls = [Ball(0, 0.0, 0.0), Ball(1, 0.0, 500.0)]
    assert predict_aim(0.0, 0.0, 1.0, 0.0, balls) is None


def test_predict_skips_cue_and_off_table_balls():
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, 0.0, on_table=False)]
    assert predict_aim(0.0, 0.0, 1.0, 0.0, balls) is None


def test_predict_head_on_ghost_and_directions():
    # 正撞：目标球正前方 x=100，沿 +x 击打
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, 0.0)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls)
    assert pred is not None
    # 鬼球停在距目标球球心 2R 处
    assert isclose(pred.ghost_x, 100.0 - 2 * config.BALL_RADIUS, abs_tol=1e-6)
    assert isclose(pred.ghost_y, 0.0, abs_tol=1e-6)
    # 目标球沿连心线（+x）
    assert isclose(pred.object_dir[0], 1.0, abs_tol=1e-6)
    assert isclose(pred.object_dir[1], 0.0, abs_tol=1e-6)
    # 正撞定杆：母球切线为零向量
    assert isclose(hypot(*pred.cue_dir), 0.0, abs_tol=1e-6)


def test_predict_separation_is_90_degrees_on_cut():
    # 切球：分离角恒为 90°（定杆模型）
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, config.BALL_RADIUS)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls)
    assert pred is not None
    assert isclose(_angle_between(pred.object_dir, pred.cue_dir), 90.0, abs_tol=1e-6)


def test_predict_directions_are_unit_vectors_on_cut():
    balls = [Ball(0, 0.0, 0.0), Ball(1, 80.0, config.BALL_RADIUS)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls)
    assert pred is not None
    assert isclose(hypot(*pred.object_dir), 1.0, abs_tol=1e-6)
    assert isclose(hypot(*pred.cue_dir), 1.0, abs_tol=1e-6)


def test_predict_picks_nearest_ball_along_ray():
    # 顺序打乱，仍应选最近的球
    balls = [Ball(0, 0.0, 0.0), Ball(2, 300.0, 0.0), Ball(1, 100.0, 0.0)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls)
    assert pred is not None
    assert isclose(pred.target_x, 100.0, abs_tol=1e-6)


# ---- 杆法红点夹取（单位圆） ----

def test_clamp_english_inside_disk_unchanged():
    dx, dy = clamp_english(0.3, -0.4)
    assert isclose(dx, 0.3, abs_tol=1e-9)
    assert isclose(dy, -0.4, abs_tol=1e-9)


def test_clamp_english_outside_disk_projected_to_edge():
    dx, dy = clamp_english(3.0, 4.0)            # 模长 5 → 投影到模长 1
    assert isclose(hypot(dx, dy), 1.0, abs_tol=1e-9)
    assert isclose(dx, 0.6, abs_tol=1e-9)
    assert isclose(dy, 0.8, abs_tol=1e-9)


def test_clamp_english_center_stays_center():
    assert clamp_english(0.0, 0.0) == (0.0, 0.0)


# ---- 杆法对分离角的影响 ----

def test_predict_stun_unchanged_when_spin_zero_head_on():
    # 定杆正撞：母球切线仍为零向量（与旧行为一致）
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, 0.0)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls, spin_v=0.0)
    assert isclose(hypot(*pred.cue_dir), 0.0, abs_tol=1e-9)


def test_predict_follow_head_on_sends_cue_forward():
    # 跟杆正撞：母球沿连心线继续前进（+x）
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, 0.0)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls, spin_v=1.0)
    assert isclose(pred.cue_dir[0], 1.0, abs_tol=1e-9)
    assert isclose(pred.cue_dir[1], 0.0, abs_tol=1e-9)


def test_predict_draw_head_on_sends_cue_backward():
    # 缩杆正撞：母球沿连心线反向（-x）
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, 0.0)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls, spin_v=-1.0)
    assert isclose(pred.cue_dir[0], -1.0, abs_tol=1e-9)
    assert isclose(pred.cue_dir[1], 0.0, abs_tol=1e-9)


def test_predict_follow_narrows_separation_on_cut():
    # 切球：跟杆使分离角 < 90°
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, config.BALL_RADIUS)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls, spin_v=1.0)
    assert _angle_between(pred.object_dir, pred.cue_dir) < 90.0 - 1e-6
    assert isclose(hypot(*pred.cue_dir), 1.0, abs_tol=1e-9)


def test_predict_draw_widens_separation_on_cut():
    # 切球：缩杆使分离角 > 90°
    balls = [Ball(0, 0.0, 0.0), Ball(1, 100.0, config.BALL_RADIUS)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls, spin_v=-1.0)
    assert _angle_between(pred.object_dir, pred.cue_dir) > 90.0 + 1e-6
    assert isclose(hypot(*pred.cue_dir), 1.0, abs_tol=1e-9)
