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

    # ---- 斯诺克点位 ----

    def baulk_line_x(self):
        """发球线 x：左侧 1/4 处（与 head_line_x 相同）。"""
        return self.left + 0.25 * self.width

    def snooker_spots(self):
        """斯诺克 7 颗彩球的标准点位。

        返回 dict: 颜色名 -> (x, y)
        - 黄/绿/棕: 在发球线上，分别居左/右/中
        - 蓝: 台面正中心
        - 粉: 中心与右侧库边之间
        - 黑: 靠近右侧库边
        """
        baulk_x = self.baulk_line_x()
        center_x = (self.left + self.right) / 2
        return {
            'brown':  (baulk_x, self.center_y),
            'yellow': (baulk_x, self.center_y - self.height * 0.20),
            'green':  (baulk_x, self.center_y + self.height * 0.20),
            'blue':   (center_x, self.center_y),
            'pink':   (self.left + 0.70 * self.width, self.center_y),
            'black':  (self.left + 0.90 * self.width, self.center_y),
        }

    def snooker_d_center(self):
        """斯诺克 D 区圆心（棕球位置）。"""
        return self.snooker_spots()['brown']

    def snooker_d_radius(self):
        """斯诺克 D 区半径（棕球到黄球的距离）。"""
        bx, by = self.snooker_d_center()
        yx, yy = self.snooker_spots()['yellow']
        return ((yx - bx) ** 2 + (yy - by) ** 2) ** 0.5

    def snooker_rack_positions(self):
        """斯诺克 15 颗红球的三角架。

        三角顶点紧邻粉球右侧，向右（远离发球线方向）展开：
        5 列 (1+2+3+4+5=15)，与 rack_positions 使用相同间距。
        """
        pink_x, pink_y = self.snooker_spots()['pink']
        d = 2 * config.BALL_RADIUS + 1.0          # 同列相邻球心间距
        col_dx = d * sqrt(3) / 2                  # 相邻列水平间距
        # 顶点在 pink 右侧一个间距的位置，整体略右移
        apex_x = pink_x + col_dx + 6
        positions = []
        for col in range(5):                      # 列 0=顶点(1球) ... 列 4=底排(5球)
            count = col + 1
            cx = apex_x + col * col_dx
            start_y = pink_y - col * (d / 2)
            for i in range(count):
                positions.append((cx, start_y + i * d))
        return positions

    def snooker_respot_position(self, color_name, balls):
        """返回彩球复位位置。如果原位被占，沿 y 轴向上/下寻找空位。"""
        spot_x, spot_y = self.snooker_spots()[color_name]
        r = config.BALL_RADIUS
        for offset in range(0, int(self.height), 2):
            test_y = spot_y - offset
            if test_y < self.top + r:
                break
            if not any((b.x - spot_x) ** 2 + (b.y - test_y) ** 2 < (2 * r) ** 2
                      for b in balls if b.on_table):
                return (spot_x, test_y)
        for offset in range(0, int(self.height), 2):
            test_y = spot_y + offset
            if test_y > self.bottom - r:
                break
            if not any((b.x - spot_x) ** 2 + (b.y - test_y) ** 2 < (2 * r) ** 2
                      for b in balls if b.on_table):
                return (spot_x, test_y)
        return (spot_x, spot_y)
