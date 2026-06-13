"""纯台球物理：碰撞、库边反弹、摩擦、进袋，逐帧推进并返回事件。无 pygame 依赖。"""
from collections import namedtuple
from math import hypot

import config

# ---- 事件 ----
EVENT_POCKETED = 'pocketed'   # data = {'number': int, 'pocket': int}
EVENT_BALL_HIT = 'ball_hit'   # data = {'a': int, 'b': int}
EVENT_CUSHION = 'cushion'     # data = {'number': int}

Event = namedtuple('Event', ['type', 'data'])


def resolve_ball_collision(a, b, restitution):
    """等质量弹性碰撞，沿连心线处理。发生碰撞返回 True，并修正重叠。"""
    dx = b.x - a.x
    dy = b.y - a.y
    dist = hypot(dx, dy)
    min_dist = a.radius + b.radius
    if dist == 0.0 or dist >= min_dist:
        return False
    nx = dx / dist
    ny = dy / dist
    # b 相对 a 沿法向(由 a 指向 b)的速度；<0 表示接近
    vn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if vn >= 0:
        return False
    j = -(1 + restitution) * vn / 2     # 等质量，单位质量冲量
    a.vx -= j * nx
    a.vy -= j * ny
    b.vx += j * nx
    b.vy += j * ny
    # 不变量：FOLLOW_DRAW_STRENGTH * 2 * MAX_SHOT_SPEED < 2 * BALL_RADIUS * SUBSTEPS，避免追加速度导致单 substep 穿模
    # 跟杆/缩杆：仅母球吃杆法，碰后沿冲击法线追加前/后向速度，并清零（每杆首次接触生效）
    cue = a if a.number == 0 else (b if b.number == 0 else None)
    if cue is not None and cue.spin_v != 0.0:
        inx, iny = (nx, ny) if cue is a else (-nx, -ny)   # 由母球指向目标球
        boost = config.FOLLOW_DRAW_STRENGTH * cue.spin_v * abs(vn)
        cue.vx += boost * inx
        cue.vy += boost * iny
        cue.spin_v = 0.0
    # 位置去重叠，各退一半
    overlap = min_dist - dist
    a.x -= nx * overlap / 2
    a.y -= ny * overlap / 2
    b.x += nx * overlap / 2
    b.y += ny * overlap / 2
    return True


def resolve_cushion(ball, table, restitution):
    """球心越过库边内侧线则夹回并反向（带能量损失）。发生反弹返回 True。

    母球带左右塞(spin_s)时，反弹后沿库边切向追加偏移（跑塞/反塞），并清零 spin_s。
    """
    r = ball.radius
    hit_x = False
    hit_y = False
    if ball.x < table.left + r:
        ball.x = table.left + r
        ball.vx = -ball.vx * restitution
        hit_x = True
    elif ball.x > table.right - r:
        ball.x = table.right - r
        ball.vx = -ball.vx * restitution
        hit_x = True
    if ball.y < table.top + r:
        ball.y = table.top + r
        ball.vy = -ball.vy * restitution
        hit_y = True
    elif ball.y > table.bottom - r:
        ball.y = table.bottom - r
        ball.vy = -ball.vy * restitution
        hit_y = True
    hit = hit_x or hit_y
    # 左右塞：仅母球，碰库后沿库边切向偏移
    if hit and ball.number == 0 and ball.spin_s != 0.0:
        s = config.SIDE_ENGLISH_STRENGTH * ball.spin_s
        if hit_x:                       # 竖直库边：切向沿 y
            ball.vy += s * abs(ball.vx)
        if hit_y:                       # 水平库边：切向沿 x
            ball.vx += s * abs(ball.vy)
        ball.spin_s = 0.0
    return hit


def apply_friction(ball):
    """每帧速度衰减；低于停止阈值则归零。"""
    ball.vx *= config.FRICTION
    ball.vy *= config.FRICTION
    if hypot(ball.vx, ball.vy) < config.STOP_THRESHOLD:
        ball.vx = 0.0
        ball.vy = 0.0


def check_pocket(ball, pockets):
    """球心进入任一袋口半径则返回袋索引，否则 None。"""
    for idx, (px, py) in enumerate(pockets):
        if hypot(ball.x - px, ball.y - py) <= config.POCKET_RADIUS:
            return idx
    return None


def all_stopped(balls):
    """在台的球是否全部停止。"""
    return all(b.vx == 0.0 and b.vy == 0.0 for b in balls if b.on_table)


def step(balls, table):
    """推进一帧：substep 内做移动/进袋/球碰/库边，帧末统一摩擦。返回本帧事件列表。"""
    events = []
    pockets = table.pocket_positions()
    n = len(balls)
    for _ in range(config.SUBSTEPS):
        # 1. 移动
        for b in balls:
            if not b.on_table:
                continue
            b.x += b.vx / config.SUBSTEPS
            b.y += b.vy / config.SUBSTEPS
        # 2. 进袋（先于库边，避免袋口处误判反弹）
        for b in balls:
            if not b.on_table:
                continue
            pi = check_pocket(b, pockets)
            if pi is not None:
                b.on_table = False
                b.vx = 0.0
                b.vy = 0.0
                events.append(Event(EVENT_POCKETED, {'number': b.number, 'pocket': pi}))
        # 3. 球间碰撞（暴力两两）
        for i in range(n):
            a = balls[i]
            if not a.on_table:
                continue
            for j in range(i + 1, n):
                c = balls[j]
                if not c.on_table:
                    continue
                if resolve_ball_collision(a, c, config.BALL_RESTITUTION):
                    events.append(Event(EVENT_BALL_HIT, {'a': a.number, 'b': c.number}))
        # 4. 库边
        for b in balls:
            if not b.on_table:
                continue
            if resolve_cushion(b, table, config.CUSHION_RESTITUTION):
                events.append(Event(EVENT_CUSHION, {'number': b.number}))
    # 5. 摩擦（每帧一次）
    for b in balls:
        if b.on_table:
            apply_friction(b)
    return events
