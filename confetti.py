"""获胜界面的碎纸粒子系统与标题弹入缓动。纯数学,无 pygame 依赖,可单测。

确定性:粒子初值由其序号经 sin 取小数导出,不使用全局随机状态,
故同一 frame 的结果每次一致(便于测试与 resume)。
"""
import math

import config

CONFETTI_COUNT = 80           # 粒子数
CONFETTI_FALL_FRAMES = 150    # 一波落完的帧数（60fps ≈ 2.5 秒）
CONFETTI_SIZE = 8             # 方块边长（像素）

# 鲜艳配色（复用球色相近的高饱和 RGB）
CONFETTI_COLORS = [
    (230, 60, 60), (60, 140, 230), (240, 200, 50), (70, 200, 110),
    (200, 80, 200), (240, 140, 50), (90, 210, 220),
]

_TITLE_BOUNCE_FRAMES = 18     # 标题弹入过程帧数；之后恒为 1.0


def _rand(i, salt):
    """基于粒子序号 i 与 salt 的确定性伪随机，返回 [0, 1)。"""
    v = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return v - math.floor(v)


def particles_at(frame, width, height):
    """返回第 frame 帧所有在场碎纸：[{'x','y','color','angle'}, ...]。

    frame >= CONFETTI_FALL_FRAMES 后返回 []（落完消失）。
    下落用初速 + 重力（先慢后快），x 用正弦摆动模拟飘，angle 随帧旋转。
    """
    if frame >= CONFETTI_FALL_FRAMES:
        return []
    particles = []
    g = 0.04                              # 重力加速度（像素/帧²，归一空间后乘高度）
    for i in range(CONFETTI_COUNT):
        # 初值（确定性）
        x0 = _rand(i, 1) * width          # 横向起点：铺满整个宽度
        y_start = -_rand(i, 2) * height * 0.3   # 起点在屏幕上沿之上一点，错开入场
        v0 = 1.5 + _rand(i, 3) * 2.0      # 初始下落速度
        sway_amp = 10 + _rand(i, 4) * 25  # 横摆幅度
        sway_freq = 0.03 + _rand(i, 5) * 0.05
        spin = (_rand(i, 6) - 0.5) * 20   # 旋转速度（度/帧）
        color = CONFETTI_COLORS[i % len(CONFETTI_COLORS)]

        t = frame
        y = y_start + v0 * t + 0.5 * g * height / 100 * t * t
        x = x0 + math.sin(t * sway_freq + i) * sway_amp
        angle = (spin * t) % 360
        particles.append({'x': x, 'y': y, 'color': color, 'angle': angle})
    return particles


def title_scale(frame):
    """标题缩放系数：frame=0 时≈0，快速放大越过 1（回弹），最终收敛到 1.0。"""
    if frame >= _TITLE_BOUNCE_FRAMES:
        return 1.0
    t = frame / _TITLE_BOUNCE_FRAMES      # 0 → 1
    # 带 overshoot 的缓动（back-out）：在接近末尾时越过 1 再回落
    c = 1.70158
    s = t - 1.0
    return 1.0 + (c + 1.0) * s * s * s + c * s * s
