# 封面三按钮 + 临时提示 设计文档

日期：2026-06-14

## 目标

在封面（主界面）上把按钮从单个「8球模式」扩展为竖排三个：

- 「8球模式」 —— 点击进入对局（沿用现有逻辑）。
- 「9球模式」 —— 点击显示临时提示「9球模式 敬请期待」，不进游戏。
- 「斯诺克」 —— 点击显示临时提示「斯诺克 敬请期待」，不进游戏。

提示在标题/按钮区附近浮现，停留数秒后自动消失。9 球与斯诺克的实际玩法**本次不做**。

## 数据模型（`menu.py`，纯逻辑，无 pygame 依赖）

按钮定义为模块内常量列表，每项 `(id, 标签)`，列表顺序即竖排上→下：

```python
BUTTONS = [('eight', '8球模式'), ('nine', '9球模式'), ('snooker', '斯诺克')]
```

- `button_rects()` → 返回 `[(id, label, x, y, w, h), ...]`（带标签，见下"接口取舍"），三个矩形水平居中、竖排，垂直方向整体围绕 `config.MENU_BTN_CY` 居中，相邻按钮间距 `config.MENU_BTN_GAP`。
- `button_at(x, y)` → 命中某个按钮则返回其 id（字符串），否则返回 `None`。**取代**旧的 `button_hit`。

布局算法（明确，避免歧义）：

- 单个按钮高 `h = MENU_BTN_H`，宽 `w = MENU_BTN_W`，相邻按钮中心间距 `step = h + MENU_BTN_GAP`。
- n 个按钮，第 i 个（i 从 0 起）中心 y = `MENU_BTN_CY + (i - (n-1)/2) * step`。
- 矩形 x = `(WINDOW_WIDTH - w) // 2`，y = `round(中心y) - h // 2`。

## `config.py` 新增

- `MENU_BTN_GAP = 20` —— 按钮竖向间距（像素）。
- `MENU_HINT_SECONDS = 2.0` —— 提示停留秒数。
- `COLOR_MENU_HINT = (235, 220, 120)` —— 提示文字色（暖黄，区别于标题白）。

> 提示文字由主循环按模式名拼接（「9球模式 敬请期待」/「斯诺克 敬请期待」），故不需要单独的 `MENU_HINT_TEXT` 常量。

## `renderer.py` 改动

- `draw_menu(screen, font, title_font, table)` —— 背景/遮罩/标题不变；按钮部分改为遍历 `menu.button_rects()`，对每个 `(id, x, y, w, h)` 画圆角矩形 + 居中标签（标签取自 `menu.BUTTONS` 的同序项，或直接在 `button_rects` 返回里带上标签——见下"接口取舍"）。
- 新增 `draw_menu_hint(screen, font, text)` —— 在按钮区下方居中画一行提示字（颜色 `COLOR_MENU_HINT`）。`text` 为空字符串时不画。

### 接口取舍

为了让 renderer 不必再去 `menu.BUTTONS` 找标签，`button_rects()` 直接返回带标签的四元组扩展为五元组：`(id, label, x, y, w, h)`。这样 `draw_menu` 单次遍历即可，`button_at` 仍只用 id 与矩形。

最终接口定为：

- `button_rects()` → `[(id, label, x, y, w, h), ...]`
- `button_at(x, y)` → `id` 或 `None`

## 主循环（`billiar_ball.py`）

菜单场景新增两个状态变量（在 `main()` 局部）：

- `hint_text = ""` —— 当前提示文字，空串表示不显示。
- `hint_until = 0` —— 提示到期的时间戳（毫秒，`pygame.time.get_ticks()`）。

事件分派（菜单场景，左键按下时）：

```
clicked = menu.button_at(*mouse_pos)
if clicked == 'eight':
    game = Game(); scene = 'game'
elif clicked == 'nine':
    hint_text = "9球模式 敬请期待"
    hint_until = pygame.time.get_ticks() + int(config.MENU_HINT_SECONDS * 1000)
elif clicked == 'snooker':
    hint_text = "斯诺克 敬请期待"
    hint_until = pygame.time.get_ticks() + int(config.MENU_HINT_SECONDS * 1000)
# clicked is None: 不做任何事
```

绘制菜单时：

```
renderer.draw_menu(screen, font, title_font, table)
if hint_text and pygame.time.get_ticks() < hint_until:
    renderer.draw_menu_hint(screen, font, hint_text)
else:
    hint_text = ""   # 到期清空
```

进入游戏（`scene='game'`）时提示状态保持原样即可——返回菜单后若仍未到期会继续显示，但因 `Game()` 这条路径只走 `'eight'`，9/斯诺克提示不会与进游戏同时发生，无需特殊处理。

计时用 `pygame.time.get_ticks()`，不引入新依赖。

## 测试（`tests/test_menu.py`）

菜单几何是纯逻辑，重点测（替换旧的 `button_hit` 相关测试）：

- `button_rects()` 返回 3 项；id 顺序为 `['eight', 'nine', 'snooker']`；label 顺序为 `['8球模式', '9球模式', '斯诺克']`。
- 每个矩形完全落在窗口内（`x>=0, y>=0, x+w<=WINDOW_WIDTH, y+h<=WINDOW_HEIGHT`）。
- 每个矩形水平居中（中心 x == `WINDOW_WIDTH/2`）。
- 三个矩形竖向互不重叠（按 y 排序后，前一个的 `y+h <= 后一个的 y`）。
- `button_at` 在每个按钮中心分别返回对应 id（`eight`/`nine`/`snooker`）。
- `button_at` 在按钮之间的空隙（相邻两按钮中点）返回 `None`。
- `button_at` 在窗口四角返回 `None`。

提示计时与绘制发生在主循环/renderer，沿用项目惯例不强测。

## 不做（YAGNI）

- 9 球 / 斯诺克的实际玩法与规则。
- 提示淡入淡出动画（只做"显示→到点消失"）。
- 按钮配置外置到 `config`（写死在 `menu.py` 的 `BUTTONS` 足够）。
- 提示底部常驻区 / 不可点的灰色禁用按钮（已选"可点 + 临时提示"方案）。
