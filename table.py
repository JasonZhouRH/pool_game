"""球台几何：库边矩形、6 个袋口、15 球三角架、开球点。无 pygame 依赖。"""
from dataclasses import dataclass
from math import sqrt

import config


@dataclass
class Table:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

    def pocket_positions(self):
        """4 角 + 上下长边中点，共 6 个。"""
        mid_x = (self.left + self.right) / 2
        return [
            (self.left, self.top),       # 0 左上
            (mid_x, self.top),           # 1 上中
            (self.right, self.top),      # 2 右上
            (self.left, self.bottom),    # 3 左下
            (mid_x, self.bottom),        # 4 下中
            (self.right, self.bottom),   # 5 右下
        ]

    def head_spot(self):
        """母球开球点：左侧 1/4 处、中线上。"""
        return (self.left + 0.25 * self.width, self.center_y)

    def head_line_x(self):
        """开球线（厨房线）竖线 x：左侧 1/4 处。其左侧为开球摆球区（厨房）。"""
        return self.left + 0.25 * self.width

    def rack_positions(self):
        """15 球三角架：顶点在脚点(右侧 3/4 处)，朝左指向开球方。"""
        foot_x = self.left + 0.75 * self.width
        foot_y = self.center_y
        d = 2 * config.BALL_RADIUS + 1.0          # 同列相邻球心间距
        col_dx = d * sqrt(3) / 2                  # 相邻列水平间距
        positions = []
        for col in range(5):                      # 列 0=顶点(1球) ... 列 4=底排(5球)
            count = col + 1
            cx = foot_x + col * col_dx
            start_y = foot_y - col * (d / 2)
            for i in range(count):
                positions.append((cx, start_y + i * d))
        return positions

    def nine_ball_foot_spot(self):
        """脚点：右侧 3/4 处、中线上。9 球菱形架的顶点。"""
        return (self.left + 0.75 * self.width, self.center_y)

    def nine_ball_rack_positions(self):
        """9 球菱形架：1-2-3-2-1 五列菱形，1 号球在脚点顶点。"""
        foot_x, foot_y = self.nine_ball_foot_spot()
        d = 2 * config.BALL_RADIUS + 1.0          # 同列相邻球心间距
        col_dx = d * sqrt(3) / 2                  # 相邻列水平间距
        counts = [1, 2, 3, 2, 1]
        positions = []
        for col, count in enumerate(counts):
            cx = foot_x + col * col_dx
            start_y = foot_y - (count - 1) * (d / 2)
            for i in range(count):
                positions.append((cx, start_y + i * d))
        return positions
