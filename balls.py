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


def create_nine_ball_balls(table):
    """母球放开球点，1-9 号球按菱形架摆放。

    菱形布局（1-2-3-2-1 五列）：
        列0(1球): index 0  —— 1 号球（顶点）
        列1(2球): index 1,2 —— 其他球
        列2(3球): index 3,4,5 —— 9 号球在中心 index 4
        列3(2球): index 6,7 —— 其他球
        列4(1球): index 8  —— 其他球
    """
    hx, hy = table.head_spot()
    positions = table.nine_ball_rack_positions()
    # Ball 1 at the front (index 0), ball 9 at center (index 4)
    # Remaining balls 2-8 fill the rest
    order = [1, 2, 3, 4, 9, 5, 6, 7, 8]
    balls = [Ball(number=0, x=hx, y=hy)]
    for number, (x, y) in zip(order, positions):
        balls.append(Ball(number=number, x=x, y=y))
    return balls


def find_cue(balls):
    for b in balls:
        if b.number == 0:
            return b
    return None


def snooker_ball_color(number):
    """Return the color for a snooker ball by its number."""
    if number == 0:
        return config.COLOR_CUE
    if 1 <= number <= 15:
        return config.COLOR_SNOOKER_RED
    if number == 16:
        return config.COLOR_SNOOKER_YELLOW
    if number == 17:
        return config.COLOR_SNOOKER_GREEN
    if number == 18:
        return config.COLOR_SNOOKER_BROWN
    if number == 19:
        return config.COLOR_SNOOKER_BLUE
    if number == 20:
        return config.COLOR_SNOOKER_PINK
    if number == 21:
        return config.COLOR_SNOOKER_BLACK
    return config.COLOR_CUE  # fallback


def snooker_value(number):
    """Return the point value for a snooker ball. Returns 0 for cue ball."""
    if number == 0:
        return 0
    if 1 <= number <= 15:
        return 1
    if number == 16:
        return 2
    if number == 17:
        return 3
    if number == 18:
        return 4
    if number == 19:
        return 5
    if number == 20:
        return 6
    if number == 21:
        return 7
    return 0


def create_snooker_balls(table):
    """Create snooker balls: cue at head spot, 6 colors at their spots,
    15 reds in a triangle behind pink spot."""
    hx, hy = table.head_spot()
    balls = [Ball(number=0, x=hx, y=hy)]

    spots = table.snooker_spots()

    # Six colors at their designated spots
    # brown=18, yellow=16, green=17, blue=19, pink=20, black=21
    color_map = {
        'brown': 18,
        'yellow': 16,
        'green': 17,
        'blue': 19,
        'pink': 20,
        'black': 21,
    }
    for name, number in color_map.items():
        balls.append(Ball(number=number, x=spots[name][0], y=spots[name][1]))

    # 15 reds (numbers 1-15) at rack positions
    for number, (x, y) in zip(range(1, 16), table.snooker_rack_positions()):
        balls.append(Ball(number=number, x=x, y=y))

    return balls
