# 封面菜单 + ESC 退回主界面 设计文档

日期：2026-06-14

## 目标

为游戏增加一个封面（主界面）：

- 封面以台面为背景，叠半透明遮罩，居中显示标题"美式8球"，下方一个"8球模式"按钮。
- 点击"8球模式"按钮进入对局。
- 对局中按 **ESC** 返回封面；返回即**完全重置**（含累计比分清零）。

## 架构

在 `main()` 之上引入一个轻量的**场景层**，只有两个场景：

- `'menu'` —— 封面
- `'game'` —— 一局对战

`Game` 类**完全不改**，它的职责仍是"一局对战"。场景切换逻辑只活在 `main()` 主循环里。

启动流程：

- 启动时 `scene = 'menu'`，`game = None`
- 封面点"8球模式"按钮 → **新建 `Game()`**，`scene = 'game'`
- 对局中按 ESC → `scene = 'menu'`，`game = None`（丢弃当前对局）

因为每次进游戏都是 `Game()` 全新实例，`scores` 自然回到 `[0, 0]`，满足"完全重置含比分清零"，无需给 `reset()` 加参数。

## 模块划分

### 新增 `menu.py`（纯逻辑，无 pygame 依赖）

与 `config` 一样保持零 pygame 依赖，便于单测：

- `button_rect()` → 返回按钮矩形 `(x, y, w, h)`，水平居中、垂直靠下。
- `button_hit(x, y)` → 点击坐标是否落在按钮矩形内。

### `config.py` 新增（纯常量，无 pygame）

- `MENU_TITLE = "美式8球"`
- `MENU_BTN_TEXT = "8球模式"`
- `MENU_BTN_W`, `MENU_BTN_H` —— 按钮尺寸
- `MENU_BTN_CY` —— 按钮中心 y（靠窗口下部）
- 颜色：
  - `COLOR_MENU_OVERLAY` —— 半透明黑遮罩 (含 alpha)
  - `COLOR_MENU_BTN` —— 按钮填充
  - `COLOR_MENU_BTN_TEXT` —— 按钮文字
  - `COLOR_MENU_TITLE` —— 标题文字

### `renderer.py` 新增 `draw_menu(screen, font, title_font)`

复用现有 `draw_table(screen)` + `draw_pockets(screen, table)` 画台面背景 → 叠半透明遮罩 → 居中大字标题 → 用 `menu.button_rect()` 画圆角按钮 + 居中文字。

标题用更大号字体：在 `main()` 中额外创建一个 `title_font` 传入。

### 对局界面可发现性提示

ESC 是隐形操作，需在对局界面右下角画一行小灰字 `ESC 返回主界面`。新增 `renderer.draw_back_hint(screen, font)`。

> 注：现有 `draw_ball_in_hand_hint` 也画在左下角 (40, H-30)，二者位置不冲突（一个左下、一个右下）。

## 数据流（main 主循环）

```
启动: scene = 'menu'; game = None
      title_font = 更大号字体

循环:
  mouse_pos = 当前鼠标
  for ev in events:
    QUIT → 退出
    if scene == 'menu':
      左键 且 menu.button_hit(*mouse_pos) → game = Game(); scene = 'game'
    elif scene == 'game':
      KEYDOWN 且 key == ESC → scene = 'menu'; game = None
      否则 → game.handle_event(ev, mouse_pos)

  if scene == 'game' and game:
    game.update()

  绘制:
    scene == 'menu' → renderer.draw_menu(screen, font, title_font)
    scene == 'game' → game.draw(screen, font, mouse_pos)
                      renderer.draw_back_hint(screen, font)

  flip(); tick(FPS)
```

## 测试

新增 `tests/test_menu.py`（纯逻辑，沿用现有 pytest 风格，无需 pygame）：

- `button_hit` 在按钮中心返回 True。
- `button_hit` 在按钮四周（外侧）返回 False。
- `button_rect` 完全落在窗口矩形内（0 ≤ x，x+w ≤ WINDOW_WIDTH，y、y+h 同理）。

场景切换发生在 pygame 主循环，沿用项目惯例（renderer/主循环不强测），不额外加循环测试。

## 不做（YAGNI）

- 不做"暂停保留残局再续打"。
- 不做封面上的设置项/难度选择/音效开关。
- 不做对局内可见的"退出"按钮（只用 ESC + 文字提示）。
