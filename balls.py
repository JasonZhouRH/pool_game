"""球数据类与球组管理。无 pygame 依赖。"""
from dataclasses import dataclass, field

import config


@dataclass
class Ball:
    number: int                 # 0=母球, 1-7=全色, 8=黑8, 9-15=花色
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    spin_v: float = 0.0         # 垂直杆法：跟杆(+)/定杆(0)/缩杆(-)，碰目标球时消费
    spin_s: float = 0.0         # 水平塞：右塞(+)/左塞(-)，碰库时消费
    radius: float = field(default=config.BALL_RADIUS)
    on_table: bool = True


def group_of(number):
    if number == 0:
        return 'cue'
    if number == 8:
        return 'eight'
    if 1 <= number <= 7:
        return 'solid'
    return 'stripe'             # 9-15


def ball_color(number):
    if number == 0:
        return config.COLOR_CUE
    if number == 8:
        return config.COLOR_EIGHT
    if number <= 7:
        return config.BALL_BASE_COLORS[number]
    return config.BALL_BASE_COLORS[number - 8]   # 9->1 ... 15->7


# 三角架内 15 个位置对应的球号；索引 4 = 列2中心 = 黑8
_RACK_ARRANGEMENT = [1, 9, 2, 10, 8, 3, 11, 4, 12, 5, 13, 6, 14, 7, 15]


def create_standard_balls(table):
    """母球放开球点，15 颗目标球按三角架摆放。"""
    hx, hy = table.head_spot()
    balls = [Ball(number=0, x=hx, y=hy)]
    for number, (x, y) in zip(_RACK_ARRANGEMENT, table.rack_positions()):
        balls.append(Ball(number=number, x=x, y=y))
    return balls


def find_cue(balls):
    for b in balls:
        if b.number == 0:
            return b
    return None
