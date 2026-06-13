"""瞄准方向、力度与击球速度向量，以及瞄准分离角的几何预测。无 pygame 依赖。

控制模型（QQ 桌球式三区）：
- 中间：鼠标指向哪，母球就朝那个方向飞（粗瞄）。
- 左侧滑条：在粗瞄方向上叠加 ±FINE_TUNE_DEG 的角度微调（精瞄）。
- 右侧球杆：往下拖蓄力，越往下力度越大；松手按"方向 + 力度"击球。
"""
from math import atan2, cos, hypot, radians, sin, sqrt
from typing import NamedTuple

import config


def aim_direction(cue_x, cue_y, mouse_x, mouse_y):
    """鼠标粗瞄：母球朝鼠标方向飞，返回单位方向向量。重合时返回 None。"""
    dx = mouse_x - cue_x
    dy = mouse_y - cue_y
    dist = hypot(dx, dy)
    if dist < 1e-9:
        return None
    return (dx / dist, dy / dist)


def apply_fine_tune(dir_x, dir_y, fine):
    """在方向 (dir_x, dir_y) 上叠加微调，返回新单位方向。

    fine ∈ [-1, 1]，映射到 ±FINE_TUNE_DEG 度的旋转（正值顺时针）。
    """
    angle = atan2(dir_y, dir_x) + radians(config.FINE_TUNE_DEG * fine)
    return (cos(angle), sin(angle))


def power_from_drag(drag_frac):
    """右球杆下拖比例 → 力度比例 [0, 1]。drag_frac 自动夹到 [0, 1]。"""
    return max(0.0, min(1.0, drag_frac))


def clamp_english(dx, dy):
    """把红点偏移 (dx, dy) 夹到单位圆内（模长 ≤ 1），返回新偏移。"""
    mag = hypot(dx, dy)
    if mag <= 1.0:
        return (dx, dy)
    return (dx / mag, dy / mag)


def velocity_from_aim(dir_x, dir_y, power_frac):
    """方向（单位向量）+ 力度比例 [0,1] → 击球速度向量。"""
    speed = max(0.0, min(1.0, power_frac)) * config.MAX_SHOT_SPEED
    return (dir_x * speed, dir_y * speed)


class AimPrediction(NamedTuple):
    """母球沿瞄准方向飞行，撞到第一颗球时的分离角预测。"""
    ghost_x: float        # 母球接触瞬间的球心（鬼球位置）
    ghost_y: float
    target_x: float       # 被撞目标球球心
    target_y: float
    object_dir: tuple     # 目标球去向（沿两球连心线）单位向量
    cue_dir: tuple        # 母球去向（切线，90° 定杆分离）单位向量


def predict_aim(cue_x, cue_y, dir_x, dir_y, balls, sum_radius=None, spin_v=0.0):
    """沿单位方向 (dir_x, dir_y) 投射母球，返回第一颗被撞球的分离角预测。

    dir 必须已归一化。balls 为场上所有球（含母球，本函数自动跳过母球与离台球）。
    无命中返回 None。母球切线方向按 90° 定杆模型（垂直于连心线）。
    spin_v: 垂直杆法 ∈ [-1,1]。0=定杆(90°切线)；>0 跟杆(母球随连心线前进，分离角<90°)；<0 缩杆(>90°)。
    """
    if sum_radius is None:
        sum_radius = 2 * config.BALL_RADIUS

    best_t = None
    best_ball = None
    for b in balls:
        if b.number == 0 or not b.on_table:
            continue
        ex = cue_x - b.x
        ey = cue_y - b.y
        proj = ex * dir_x + ey * dir_y          # b 系数（u 为单位向量）
        c = ex * ex + ey * ey - sum_radius * sum_radius
        disc = proj * proj - c
        if disc < 0.0:
            continue                            # 射线不与该球相交
        t = -proj - sqrt(disc)                  # 最近接触点
        if t <= 1e-9:
            continue                            # 命中点在母球后方或已重叠
        if best_t is None or t < best_t:
            best_t = t
            best_ball = b

    if best_ball is None:
        return None

    ghost_x = cue_x + dir_x * best_t
    ghost_y = cue_y + dir_y * best_t

    # 连心线方向：鬼球 → 目标球（目标球去向）
    nx = best_ball.x - ghost_x
    ny = best_ball.y - ghost_y
    nlen = hypot(nx, ny)
    if nlen < 1e-9:
        return None
    nx, ny = nx / nlen, ny / nlen

    # 母球切线：入射方向去掉连心线分量后剩下的部分（与连心线垂直，90°）
    dot = dir_x * nx + dir_y * ny
    tx = dir_x - dot * nx
    ty = dir_y - dot * ny
    tlen = hypot(tx, ty)
    if tlen < 1e-9:
        tx, ty = 0.0, 0.0                       # 正撞：定杆时切线为零
    else:
        tx, ty = tx / tlen, ty / tlen

    # 杆法合成：定杆=纯切线(90°)；跟杆沿 +连心线(分离角变小)、缩杆沿 -连心线(变大)
    cx = tx + spin_v * config.FOLLOW_DRAW_STRENGTH * nx
    cy = ty + spin_v * config.FOLLOW_DRAW_STRENGTH * ny
    clen = hypot(cx, cy)
    if clen < 1e-9:
        cx, cy = 0.0, 0.0                       # 定杆正撞：母球原地停
    else:
        cx, cy = cx / clen, cy / clen

    return AimPrediction(ghost_x, ghost_y, best_ball.x, best_ball.y,
                         (nx, ny), (cx, cy))
