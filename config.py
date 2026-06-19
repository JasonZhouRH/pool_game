"""全部常量：窗口、球台几何、物理参数、颜色。无任何 pygame 依赖。"""

# ---- 窗口 ----
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600
FPS = 60

# ---- 球台（库边内侧矩形，球心在此矩形内反弹）----
TABLE_LEFT = 120
TABLE_RIGHT = 880
TABLE_TOP = 170
TABLE_BOTTOM = 520

# ---- 球与袋 ----
BALL_RADIUS = 11
POCKET_RADIUS = 24

# ---- 物理参数 ----
FRICTION = 0.985             # 每帧速度衰减系数
STOP_THRESHOLD = 0.06        # 速度低于此值判为停止
CUSHION_RESTITUTION = 0.9    # 库边反弹能量保留
BALL_RESTITUTION = 0.95      # 球间碰撞恢复系数
SUBSTEPS = 8                 # 每帧分步推进次数
MAX_SHOT_SPEED = 30.0        # 击球最大速度（像素/帧）
MAX_DRAG = 220.0             # 拉杆最大有效距离（像素）

# ---- 杆法（旋转）物理强度 ----
FOLLOW_DRAW_STRENGTH = 0.6   # 跟/缩杆：沿冲击法线追加的前/后向速度系数（也用于预测线）
SIDE_ENGLISH_STRENGTH = 0.35 # 左右塞：母球碰库反弹后沿库边切向偏移系数

# ---- 控制台（左微调滑条 + 右球杆蓄力）----
FINE_TUNE_DEG = 8.0          # 左滑条最大微调角度（粗瞄方向 ±此值）

# 左侧竖直微调滑条
SLIDER_X = 40                # 滑轨中心 x
SLIDER_TOP = 210             # 滑轨顶端 y
SLIDER_BOTTOM = 480          # 滑轨底端 y
SLIDER_KNOB_R = 12           # 滑块半径

# 右侧竖直球杆蓄力槽（往下拖蓄力，越往下力越大）
CUE_X = 960                  # 球杆槽中心 x
CUE_TOP = 210                # 槽顶端 y（力度 0）
CUE_BOTTOM = 480             # 槽底端 y（力度 100%）
CUE_GRAB_R = 16              # 球杆握把命中半径

# 右上角杆法控件：小图标（点击放大）+ 放大面板（拖红点设打点）
SPIN_ICON_X = 930            # 小图标球心 x（避开蓄力列与瞄准区）
SPIN_ICON_Y = 55             # 小图标球心 y（球台上沿之上）
SPIN_ICON_R = 16             # 小图标半径
SPIN_PANEL_X = 835           # 放大面板球心 x
SPIN_PANEL_Y = 95            # 放大面板球心 y
SPIN_PANEL_R = 55            # 放大面板半径
SPIN_DOT_R = 7               # 红点半径

# ---- 颜色 (RGB) ----
COLOR_BG = (30, 30, 35)
COLOR_FELT = (20, 120, 60)
COLOR_RAIL = (90, 55, 25)
COLOR_RAIL_HIGHLIGHT = (140, 100, 60)  # 库边内沿高光（左上）
COLOR_RAIL_SHADOW = (50, 30, 14)       # 库边内沿阴影（右下）
COLOR_POCKET = (12, 12, 12)
COLOR_LINE = (255, 255, 255)
COLOR_TEXT = (235, 235, 235)
COLOR_CUE = (245, 245, 245)
COLOR_EIGHT = (20, 20, 20)
COLOR_STRIPE_BAND = (245, 245, 245)
COLOR_POWER_BAR = (220, 60, 60)
COLOR_GHOST = (235, 235, 235)        # 鬼球（母球撞击瞬间位置）轮廓
COLOR_GHOST_FORBIDDEN = (230, 60, 60)  # 非法首球时鬼球（红圈 + 斜杠）
COLOR_OBJECT_PATH = (235, 220, 120)  # 目标球路径（沿连心线）
COLOR_CUE_PATH = (120, 220, 235)     # 母球切线路径（90° 定杆分离）
COLOR_SLIDER_TRACK = (70, 70, 78)    # 微调滑轨
COLOR_SLIDER_KNOB = (220, 220, 230)  # 微调滑块
COLOR_CUE_STICK = (200, 150, 70)     # 球杆木色
COLOR_CUE_TIP = (90, 170, 220)       # 球杆皮头
COLOR_HEAD_LINE = (210, 230, 210)    # 开球线（厨房线）
COLOR_SPIN_BALL = (245, 245, 245)    # 杆法控件白球面
COLOR_SPIN_DOT = (220, 50, 50)       # 杆法红点（击打点）
COLOR_SPIN_RING = (0, 0, 0)          # 杆法控件轮廓/十字参考

# ---- 斯诺克球色 ----
COLOR_SNOOKER_RED = (200, 30, 30)
COLOR_SNOOKER_YELLOW = (220, 200, 40)
COLOR_SNOOKER_GREEN = (30, 150, 70)
COLOR_SNOOKER_BROWN = (120, 70, 40)
COLOR_SNOOKER_BLUE = (40, 80, 210)
COLOR_SNOOKER_PINK = (230, 140, 160)
COLOR_SNOOKER_BLACK = (20, 20, 20)

# 1-7 号基础色；花色 9-15 复用同色相 + 白带
BALL_BASE_COLORS = {
    1: (230, 200, 40),    # 黄
    2: (40, 80, 200),     # 蓝
    3: (200, 40, 40),     # 红
    4: (120, 50, 160),    # 紫
    5: (230, 130, 40),    # 橙
    6: (30, 140, 70),     # 绿
    7: (120, 40, 40),     # 栗
}

# ---- 封面菜单 ----
MENU_TITLE = "2D台球游戏"
MENU_BTN_W = 220            # 按钮宽
MENU_BTN_H = 64             # 按钮高
MENU_BTN_CY = 400           # 按钮中心 y（窗口下部，标题在其上方）

COLOR_MENU_OVERLAY = (0, 0, 0, 150)   # 台面背景上的半透明黑遮罩 (RGBA)
COLOR_MENU_BTN = (40, 140, 80)        # 按钮填充（呼应台呢绿）
COLOR_MENU_BTN_TEXT = (245, 245, 245) # 按钮文字
COLOR_MENU_TITLE = (245, 245, 245)    # 标题文字
MENU_BTN_GAP = 20            # 按钮竖向间距（像素）
MENU_HINT_SECONDS = 2.0      # 临时提示停留秒数
COLOR_MENU_HINT = (235, 220, 120)  # 临时提示文字色（暖黄）
