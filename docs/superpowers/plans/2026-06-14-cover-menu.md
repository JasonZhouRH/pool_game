# 封面菜单 + ESC 退回主界面 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加一个以台面为背景的封面（主界面），点"8球模式"按钮进入对局；对局中按 ESC 完全重置并返回封面。

**Architecture:** 在 `main()` 之上加一个轻量场景层（`'menu'`/`'game'`），`Game` 类不改。新增纯逻辑模块 `menu.py`（按钮几何）和 `config` 常量，renderer 增加 `draw_menu`、`draw_back_hint`。每次进游戏都 `new Game()`，比分自然清零。

**Tech Stack:** Python 3 + pygame；pytest（纯逻辑模块单测，沿用 `tests/` + `conftest.py` 的导入约定）。

---

## File Structure

- `config.py`（修改）—— 末尾追加封面相关常量（尺寸、文字、颜色）。
- `menu.py`（新建）—— 纯逻辑：`button_rect()`、`button_hit(x, y)`。无 pygame 依赖。
- `renderer.py`（修改）—— 新增 `draw_menu(screen, font, title_font)` 与 `draw_back_hint(screen, font)`。
- `billiar_ball.py`（修改）—— `main()` 引入场景层与 ESC 处理。
- `tests/test_menu.py`（新建）—— `menu.py` 单测。

---

### Task 1: 封面常量（config.py）

**Files:**
- Modify: `config.py`（在文件末尾 `BALL_BASE_COLORS` 之后追加）
- Test: `tests/test_config.py`（追加一个测试函数）

- [ ] **Step 1: 写失败测试**

在 `tests/test_config.py` 末尾追加：

```python
def test_menu_constants_present_and_sane():
    # 文案
    assert isinstance(config.MENU_TITLE, str) and config.MENU_TITLE
    assert isinstance(config.MENU_BTN_TEXT, str) and config.MENU_BTN_TEXT
    # 按钮尺寸为正、按钮整体落在窗口内
    assert config.MENU_BTN_W > 0 and config.MENU_BTN_H > 0
    assert config.MENU_BTN_W <= config.WINDOW_WIDTH
    assert 0 < config.MENU_BTN_CY < config.WINDOW_HEIGHT
    assert config.MENU_BTN_CY + config.MENU_BTN_H // 2 <= config.WINDOW_HEIGHT
    # 遮罩为带 alpha 的 RGBA，其余为 RGB
    assert len(config.COLOR_MENU_OVERLAY) == 4 and 0 <= config.COLOR_MENU_OVERLAY[3] <= 255
    assert len(config.COLOR_MENU_BTN) == 3
    assert len(config.COLOR_MENU_BTN_TEXT) == 3
    assert len(config.COLOR_MENU_TITLE) == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_config.py::test_menu_constants_present_and_sane -v`
Expected: FAIL，报 `AttributeError: module 'config' has no attribute 'MENU_TITLE'`

- [ ] **Step 3: 实现 —— 在 `config.py` 末尾追加**

```python

# ---- 封面菜单 ----
MENU_TITLE = "美式8球"
MENU_BTN_TEXT = "8球模式"
MENU_BTN_W = 220            # 按钮宽
MENU_BTN_H = 64             # 按钮高
MENU_BTN_CY = 400           # 按钮中心 y（窗口下部，标题在其上方）

COLOR_MENU_OVERLAY = (0, 0, 0, 150)   # 台面背景上的半透明黑遮罩 (RGBA)
COLOR_MENU_BTN = (40, 140, 80)        # 按钮填充（呼应台呢绿）
COLOR_MENU_BTN_TEXT = (245, 245, 245) # 按钮文字
COLOR_MENU_TITLE = (245, 245, 245)    # 标题文字
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS（含新测试与原有测试）

- [ ] **Step 5: 提交**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): 新增封面菜单常量"
```

---

### Task 2: 按钮几何逻辑（menu.py）

**Files:**
- Create: `menu.py`
- Test: `tests/test_menu.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_menu.py`：

```python
import config
import menu


def test_button_rect_inside_window():
    x, y, w, h = menu.button_rect()
    assert w == config.MENU_BTN_W and h == config.MENU_BTN_H
    assert x >= 0 and y >= 0
    assert x + w <= config.WINDOW_WIDTH
    assert y + h <= config.WINDOW_HEIGHT


def test_button_rect_horizontally_centered():
    x, _, w, _ = menu.button_rect()
    # 矩形中心 x 等于窗口中心 x
    assert abs((x + w / 2) - config.WINDOW_WIDTH / 2) < 1e-6


def test_button_hit_center_true():
    assert menu.button_hit(config.WINDOW_WIDTH // 2, config.MENU_BTN_CY) is True


def test_button_hit_outside_false():
    x, y, w, h = menu.button_rect()
    assert menu.button_hit(x - 5, y + h // 2) is False        # 左外
    assert menu.button_hit(x + w + 5, y + h // 2) is False     # 右外
    assert menu.button_hit(x + w // 2, y - 5) is False         # 上外
    assert menu.button_hit(x + w // 2, y + h + 5) is False     # 下外


def test_button_hit_edges_inclusive():
    x, y, w, h = menu.button_rect()
    assert menu.button_hit(x, y) is True                       # 左上角
    assert menu.button_hit(x + w, y + h) is True               # 右下角
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_menu.py -v`
Expected: FAIL，报 `ModuleNotFoundError: No module named 'menu'`

- [ ] **Step 3: 实现 —— 新建 `menu.py`**

```python
"""封面菜单的纯几何逻辑：按钮矩形与命中判定。无任何 pygame 依赖。"""
import config


def button_rect():
    """返回"8球模式"按钮矩形 (x, y, w, h)，水平居中、中心 y = MENU_BTN_CY。"""
    w, h = config.MENU_BTN_W, config.MENU_BTN_H
    x = (config.WINDOW_WIDTH - w) // 2
    y = config.MENU_BTN_CY - h // 2
    return (x, y, w, h)


def button_hit(x, y):
    """点击坐标 (x, y) 是否落在按钮矩形内（含边界）。"""
    bx, by, w, h = button_rect()
    return bx <= x <= bx + w and by <= y <= by + h
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_menu.py -v`
Expected: PASS（5 个测试全过）

- [ ] **Step 5: 提交**

```bash
git add menu.py tests/test_menu.py
git commit -m "feat(menu): 封面按钮几何与命中判定"
```

---

### Task 3: 封面与返回提示绘制（renderer.py）

**Files:**
- Modify: `renderer.py`（顶部 import 区 + 文件末尾追加两个函数）

> 说明：renderer 绘制函数沿用项目惯例不写单测（与现有 `draw_*` 一致）。本任务只做实现与一次冒烟导入校验，无 TDD 循环。

- [ ] **Step 1: 在 `renderer.py` 顶部 import 区追加 `import menu`**

把现有：

```python
import config
from balls import group_of, ball_color
from cue import predict_aim
```

改为：

```python
import config
import menu
from balls import group_of, ball_color
from cue import predict_aim
```

- [ ] **Step 2: 在 `renderer.py` 末尾追加 `draw_menu` 与 `draw_back_hint`**

```python


def draw_menu(screen, font, title_font, table):
    """封面：台面背景 + 半透明遮罩 + 居中标题 + "8球模式"按钮。"""
    draw_table(screen)
    draw_pockets(screen, table)
    overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill(config.COLOR_MENU_OVERLAY)
    screen.blit(overlay, (0, 0))
    # 标题：按钮上方
    title = title_font.render(config.MENU_TITLE, True, config.COLOR_MENU_TITLE)
    screen.blit(title, title.get_rect(center=(config.WINDOW_WIDTH // 2, config.MENU_BTN_CY - 140)))
    # 按钮
    x, y, w, h = menu.button_rect()
    pygame.draw.rect(screen, config.COLOR_MENU_BTN, (x, y, w, h), border_radius=12)
    pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2, border_radius=12)
    label = font.render(config.MENU_BTN_TEXT, True, config.COLOR_MENU_BTN_TEXT)
    screen.blit(label, label.get_rect(center=(x + w // 2, y + h // 2)))


def draw_back_hint(screen, font):
    """对局界面右下角小灰字：提示按 ESC 返回主界面。"""
    txt = font.render("ESC 返回主界面", True, config.COLOR_TEXT)
    screen.blit(txt, txt.get_rect(bottomright=(config.WINDOW_WIDTH - 20, config.WINDOW_HEIGHT - 14)))
```

- [ ] **Step 3: 冒烟校验（dummy 视频驱动下导入并调用一次，确认无异常）**

Run:
```bash
SDL_VIDEODRIVER=dummy python -c "
import pygame, config, renderer
from table import Table
pygame.init(); s = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
f = pygame.font.SysFont('arial', 22); tf = pygame.font.SysFont('arial', 64)
t = Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)
renderer.draw_menu(s, f, tf, t); renderer.draw_back_hint(s, f)
print('draw OK')
pygame.quit()
"
```
Expected: 打印 `draw OK`，无异常

- [ ] **Step 4: 提交**

```bash
git add renderer.py
git commit -m "feat(renderer): 封面绘制 draw_menu 与返回提示 draw_back_hint"
```

---

### Task 4: 主循环场景层（billiar_ball.py）

**Files:**
- Modify: `billiar_ball.py:322-344`（`main()` 函数整体替换）

> 说明：场景切换发生在 pygame 主循环，沿用项目惯例不写单测。本任务做实现 + 手动运行校验。

- [ ] **Step 1: 替换 `main()` 实现**

将现有 `main()`（约 322-344 行）整体替换为：

```python
def main():
    pygame.init()
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    pygame.display.set_caption("2D 美式8球")
    font = pygame.font.SysFont('arialunicode,heitisc,pingfangsc,arial', 22)
    title_font = pygame.font.SysFont('arialunicode,heitisc,pingfangsc,arial', 64)
    clock = pygame.time.Clock()

    table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                  config.TABLE_RIGHT, config.TABLE_BOTTOM)
    scene = 'menu'      # 'menu' 封面 / 'game' 对局
    game = None

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if scene == 'menu':
                if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                        and menu.button_hit(*mouse_pos)):
                    game = Game()          # 全新一局，比分清零
                    scene = 'game'
            else:  # scene == 'game'
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                    scene = 'menu'         # 丢弃当前对局，返回封面
                    game = None
                else:
                    game.handle_event(ev, mouse_pos)

        if scene == 'game' and game is not None:
            game.update()

        if scene == 'menu':
            renderer.draw_menu(screen, font, title_font, table)
        else:
            game.draw(screen, font, mouse_pos)
            renderer.draw_back_hint(screen, font)

        pygame.display.flip()
        clock.tick(config.FPS)
```

- [ ] **Step 2: 顶部加入 `import menu`**

把 `billiar_ball.py` 顶部：

```python
import config
import physics
import renderer
```

改为：

```python
import config
import menu
import physics
import renderer
```

- [ ] **Step 3: 全量测试确认无回归**

Run: `python -m pytest -q`
Expected: 全部 PASS（含新增 menu/config 测试）

- [ ] **Step 4: 手动运行校验（无头冒烟：构建 Game 不报错 + 模块可导入）**

Run:
```bash
SDL_VIDEODRIVER=dummy python -c "
import pygame, config, billiar_ball
pygame.init(); pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
g = billiar_ball.Game()
assert g.scores == [0, 0]
print('Game boots, scores zeroed:', g.scores)
pygame.quit()
"
```
Expected: 打印 `Game boots, scores zeroed: [0, 0]`，无异常

> 交互式校验（需真实显示，由人工执行）：`python billiar_ball.py` → 看到封面 → 点"8球模式"进游戏 → 按 ESC 回封面 → 再进游戏确认比分为 0:0。

- [ ] **Step 5: 提交**

```bash
git add billiar_ball.py
git commit -m "feat(game): main 加场景层 — 封面进入 + ESC 返回主界面"
```

---

## Self-Review

**Spec coverage：**
- 封面以台面为背景 + 遮罩 + 标题 + 按钮 → Task 3 `draw_menu`，常量 Task 1。✓
- 点"8球模式"进对局 → Task 4 `menu.button_hit` 分支。✓
- ESC 返回封面 + 完全重置含比分清零 → Task 4：`game = None` + 下次 `Game()` 新实例（`scores` 在 `__init__` 重建为 `[0,0]`），Task 4 Step 4 验证。✓
- 按钮几何纯逻辑 + 单测 → Task 2。✓
- 右下角 ESC 提示 → Task 3 `draw_back_hint`。✓

**Placeholder scan：** 无 TBD/TODO；每个代码步骤均给出完整代码。✓

**Type consistency：**
- `menu.button_rect()` 返回 `(x, y, w, h)`，在 Task 2 测试、Task 3 `draw_menu`、隐式经 `button_hit` 使用，签名一致。✓
- `renderer.draw_menu(screen, font, title_font, table)` 四参，Task 3 定义、Task 4 调用一致（注意：设计文档初稿写的是三参，实现按四参——需传 `table` 画背景，已在两处统一为四参）。✓
- `renderer.draw_back_hint(screen, font)` Task 3 定义、Task 4 调用一致。✓
- `Game.scores` 在 `billiar_ball.py:28` `__init__` 中创建，ESC 走新 `Game()` 即清零，无需改 `reset()`。✓
