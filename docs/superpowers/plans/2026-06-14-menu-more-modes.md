# 封面三按钮 + 临时提示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 封面按钮从单个「8球模式」扩展为竖排三个（8球/9球/斯诺克），8球进游戏，9球与斯诺克点击后浮现数秒「敬请期待」提示。

**Architecture:** `menu.py` 升级为"带 id 的按钮列表"——`button_rects()` 竖排算出三个矩形（带 id+label），`button_at(x,y)` 返回命中 id。`renderer.draw_menu` 遍历绘制，新增 `draw_menu_hint`。`main()` 菜单场景按 id 分派，用 `pygame.time.get_ticks()` 做提示计时。`Game` 类不动。

**Tech Stack:** Python 3 + pygame；pytest（`menu.py` 纯逻辑单测，沿用 `tests/` + `conftest.py` 约定）。运行 python 用 `./venv/bin/python`（plain `python` 不在 PATH）。

---

## File Structure

- `config.py`（修改）—— 追加 `MENU_BTN_GAP`、`MENU_HINT_SECONDS`、`COLOR_MENU_HINT`。
- `menu.py`（重写）—— `BUTTONS` 常量列表；`button_rects()` 返回 `[(id, label, x, y, w, h), ...]`；`button_at(x, y)` 返回 id 或 None。移除 `button_rect`/`button_hit`。
- `tests/test_menu.py`（重写）—— 针对新接口的纯逻辑单测，替换旧 `button_rect`/`button_hit` 测试。
- `renderer.py`（修改）—— `draw_menu` 改为遍历 `button_rects()`；新增 `draw_menu_hint`。
- `billiar_ball.py`（修改）—— `main()` 菜单场景按 id 分派 + 提示计时与绘制。

执行顺序按 Task 1→4，依赖自底向上（config → menu → renderer → main）。

---

### Task 1: 封面新常量（config.py）

**Files:**
- Modify: `config.py`（在 `# ---- 封面菜单 ----` 段落内追加）
- Test: `tests/test_config.py`（在 `test_menu_constants_present_and_sane` 末尾追加断言）

- [ ] **Step 1: 扩充失败测试**

打开 `tests/test_config.py`，在 `test_menu_constants_present_and_sane` 函数体**末尾**追加以下断言（紧接现有最后一行 `assert len(config.COLOR_MENU_TITLE) == 3` 之后，保持同样缩进）：

```python
    # 三按钮布局 + 提示
    assert config.MENU_BTN_GAP >= 0
    assert config.MENU_HINT_SECONDS > 0
    assert len(config.COLOR_MENU_HINT) == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./venv/bin/python -m pytest tests/test_config.py::test_menu_constants_present_and_sane -v`
Expected: FAIL，报 `AttributeError: module 'config' has no attribute 'MENU_BTN_GAP'`

- [ ] **Step 3: 实现 —— 在 `config.py` 的封面菜单段落追加**

在 `config.py` 中 `COLOR_MENU_TITLE = (245, 245, 245)    # 标题文字` 这一行**之后**追加：

```python
MENU_BTN_GAP = 20            # 按钮竖向间距（像素）
MENU_HINT_SECONDS = 2.0      # 临时提示停留秒数
COLOR_MENU_HINT = (235, 220, 120)  # 临时提示文字色（暖黄）
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./venv/bin/python -m pytest tests/test_config.py -v`
Expected: PASS（全部）

- [ ] **Step 5: 提交**

```bash
git add config.py tests/test_config.py
git commit -m "feat(config): 三按钮间距 + 临时提示常量"
```

---

### Task 2: 按钮列表几何（menu.py 重写）

**Files:**
- Modify: `menu.py`（整体重写）
- Test: `tests/test_menu.py`（整体重写）

> 说明：本任务用新接口 `button_rects()` / `button_at()` 取代旧的 `button_rect()` / `button_hit()`。旧测试一并替换。Task 3、4 会更新 renderer 与 main 的调用方，故本任务提交后旧调用点暂时引用不存在的函数——这是预期的中间态，会在 Task 3/4 修复。先不要去改 renderer/main。

- [ ] **Step 1: 重写测试文件**

将 `tests/test_menu.py` **整体替换**为：

```python
import config
import menu


def test_buttons_ids_and_labels_in_order():
    rects = menu.button_rects()
    assert [r[0] for r in rects] == ['eight', 'nine', 'snooker']
    assert [r[1] for r in rects] == ['8球模式', '9球模式', '斯诺克']


def test_button_rects_inside_window():
    for _id, _label, x, y, w, h in menu.button_rects():
        assert w == config.MENU_BTN_W and h == config.MENU_BTN_H
        assert x >= 0 and y >= 0
        assert x + w <= config.WINDOW_WIDTH
        assert y + h <= config.WINDOW_HEIGHT


def test_button_rects_horizontally_centered():
    for _id, _label, x, _y, w, _h in menu.button_rects():
        assert abs((x + w / 2) - config.WINDOW_WIDTH / 2) < 1e-6


def test_button_rects_no_vertical_overlap():
    rects = sorted(menu.button_rects(), key=lambda r: r[3])  # 按 y 排序
    for (a, b) in zip(rects, rects[1:]):
        a_bottom = a[3] + a[5]   # a.y + a.h
        b_top = b[3]
        assert a_bottom <= b_top


def test_button_at_center_returns_id():
    for _id, _label, x, y, w, h in menu.button_rects():
        cx, cy = x + w // 2, y + h // 2
        assert menu.button_at(cx, cy) == _id


def test_button_at_gap_returns_none():
    rects = sorted(menu.button_rects(), key=lambda r: r[3])
    # 相邻两按钮之间的竖向空隙中点
    a, b = rects[0], rects[1]
    gap_y = (a[3] + a[5] + b[3]) // 2   # (a 底 + b 顶) / 2
    cx = config.WINDOW_WIDTH // 2
    assert menu.button_at(cx, gap_y) is None


def test_button_at_corners_return_none():
    assert menu.button_at(0, 0) is None
    assert menu.button_at(config.WINDOW_WIDTH, config.WINDOW_HEIGHT) is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./venv/bin/python -m pytest tests/test_menu.py -v`
Expected: FAIL，报 `AttributeError: module 'menu' has no attribute 'button_rects'`

- [ ] **Step 3: 实现 —— 将 `menu.py` 整体替换为**

```python
"""封面菜单的纯几何逻辑：按钮列表、矩形与命中判定。无任何 pygame 依赖。"""
import config

# 竖排顺序（上→下）：(id, 标签)
BUTTONS = [
    ('eight', '8球模式'),
    ('nine', '9球模式'),
    ('snooker', '斯诺克'),
]


def button_rects():
    """返回按钮列表 [(id, label, x, y, w, h), ...]。

    三个矩形水平居中、竖排；垂直方向整体围绕 config.MENU_BTN_CY 居中，
    相邻按钮中心间距 = 按钮高 + config.MENU_BTN_GAP。
    """
    w, h = config.MENU_BTN_W, config.MENU_BTN_H
    n = len(BUTTONS)
    step = h + config.MENU_BTN_GAP
    x = (config.WINDOW_WIDTH - w) // 2
    rects = []
    for i, (bid, label) in enumerate(BUTTONS):
        cy = config.MENU_BTN_CY + (i - (n - 1) / 2) * step
        y = round(cy) - h // 2
        rects.append((bid, label, x, y, w, h))
    return rects


def button_at(x, y):
    """命中某个按钮则返回其 id，否则返回 None（含边界算命中）。"""
    for bid, _label, bx, by, w, h in button_rects():
        if bx <= x <= bx + w and by <= y <= by + h:
            return bid
    return None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./venv/bin/python -m pytest tests/test_menu.py -v`
Expected: PASS（7 个测试全过）

- [ ] **Step 5: 提交**

```bash
git add menu.py tests/test_menu.py
git commit -m "feat(menu): 按钮列表 button_rects/button_at 取代单按钮接口"
```

---

### Task 3: 封面绘制三按钮 + 提示（renderer.py）

**Files:**
- Modify: `renderer.py:192-207`（`draw_menu` 函数体的按钮部分）+ 文件末尾追加 `draw_menu_hint`

> 说明：renderer 绘制函数沿用项目惯例不写单测。本任务做实现 + 冒烟校验。

- [ ] **Step 1: 替换 `draw_menu` 的按钮绘制部分**

当前 `renderer.py` 的 `draw_menu`（约 192-207 行）结尾是：

```python
    # 按钮
    x, y, w, h = menu.button_rect()
    pygame.draw.rect(screen, config.COLOR_MENU_BTN, (x, y, w, h), border_radius=12)
    pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2, border_radius=12)
    label = font.render(config.MENU_BTN_TEXT, True, config.COLOR_MENU_BTN_TEXT)
    screen.blit(label, label.get_rect(center=(x + w // 2, y + h // 2)))
```

将从 `# 按钮` 起到函数末尾的这 6 行替换为：

```python
    # 按钮（竖排三个）
    for _bid, label_text, x, y, w, h in menu.button_rects():
        pygame.draw.rect(screen, config.COLOR_MENU_BTN, (x, y, w, h), border_radius=12)
        pygame.draw.rect(screen, (0, 0, 0), (x, y, w, h), 2, border_radius=12)
        label = font.render(label_text, True, config.COLOR_MENU_BTN_TEXT)
        screen.blit(label, label.get_rect(center=(x + w // 2, y + h // 2)))
```

同时把 `draw_menu` 的 docstring 由 `"""封面：台面背景 + 半透明遮罩 + 居中标题 + "8球模式"按钮。"""` 改为 `"""封面：台面背景 + 半透明遮罩 + 居中标题 + 竖排模式按钮。"""`。

- [ ] **Step 2: 在 `renderer.py` 末尾追加 `draw_menu_hint`**

在文件最末尾（`draw_back_hint` 之后）追加：

```python


def draw_menu_hint(screen, font, text):
    """封面临时提示：按钮区下方居中一行字。text 为空则不画。"""
    if not text:
        return
    # 提示画在最下面一个按钮的下方
    rects = menu.button_rects()
    bottom = max(y + h for _bid, _label, _x, y, _w, h in rects)
    txt = font.render(text, True, config.COLOR_MENU_HINT)
    screen.blit(txt, txt.get_rect(center=(config.WINDOW_WIDTH // 2, bottom + 30)))
```

- [ ] **Step 3: 冒烟校验**

Run:
```bash
SDL_VIDEODRIVER=dummy ./venv/bin/python -c "
import pygame, config, renderer
from table import Table
pygame.init(); s = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
f = pygame.font.SysFont('arial', 22); tf = pygame.font.SysFont('arial', 64)
t = Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)
renderer.draw_menu(s, f, tf, t)
renderer.draw_menu_hint(s, f, '9球模式 敬请期待')
renderer.draw_menu_hint(s, f, '')
print('draw OK')
pygame.quit()
"
```
Expected: 打印 `draw OK`，无异常

- [ ] **Step 4: 提交**

```bash
git add renderer.py
git commit -m "feat(renderer): 封面绘制竖排三按钮 + draw_menu_hint 临时提示"
```

---

### Task 4: 主循环按 id 分派 + 提示计时（billiar_ball.py）

**Files:**
- Modify: `billiar_ball.py:331-358`（`main()` 的菜单初始化 / 事件分派 / 菜单绘制三处）

> 说明：场景切换与计时发生在 pygame 主循环，沿用项目惯例不写单测。本任务做实现 + 全量测试 + 无头冒烟。

- [ ] **Step 1: 在菜单状态变量处加入提示状态**

当前（约 331-334 行）：

```python
    table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                  config.TABLE_RIGHT, config.TABLE_BOTTOM)
    scene = 'menu'      # 'menu' 封面 / 'game' 对局
    game = None
```

替换为：

```python
    table = Table(config.TABLE_LEFT, config.TABLE_TOP,
                  config.TABLE_RIGHT, config.TABLE_BOTTOM)
    scene = 'menu'      # 'menu' 封面 / 'game' 对局
    game = None
    hint_text = ""      # 封面临时提示文字，空串=不显示
    hint_until = 0      # 提示到期时间戳（ms, pygame.time.get_ticks）
```

- [ ] **Step 2: 替换菜单事件分派**

当前（约 342-346 行）：

```python
            if scene == 'menu':
                if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                        and menu.button_hit(*mouse_pos)):
                    game = Game()          # 全新一局，比分清零
                    scene = 'game'
```

替换为：

```python
            if scene == 'menu':
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    clicked = menu.button_at(*mouse_pos)
                    if clicked == 'eight':
                        game = Game()          # 全新一局，比分清零
                        scene = 'game'
                    elif clicked == 'nine':
                        hint_text = "9球模式 敬请期待"
                        hint_until = pygame.time.get_ticks() + int(config.MENU_HINT_SECONDS * 1000)
                    elif clicked == 'snooker':
                        hint_text = "斯诺克 敬请期待"
                        hint_until = pygame.time.get_ticks() + int(config.MENU_HINT_SECONDS * 1000)
```

- [ ] **Step 3: 替换菜单绘制分支**

当前（约 357-358 行）：

```python
        if scene == 'menu':
            renderer.draw_menu(screen, font, title_font, table)
```

替换为：

```python
        if scene == 'menu':
            renderer.draw_menu(screen, font, title_font, table)
            if hint_text and pygame.time.get_ticks() < hint_until:
                renderer.draw_menu_hint(screen, font, hint_text)
            else:
                hint_text = ""   # 到期清空
```

- [ ] **Step 4: 全量测试确认无回归**

Run: `./venv/bin/python -m pytest -q`
Expected: `80 passed`（外加 `tests/test_game_fire_spin.py` 的 5 个 PRE-EXISTING errors，因加载已不存在的 `23.py`——与本改动无关，忽略）

- [ ] **Step 5: 无头冒烟（导入 + 构建 Game 不报错）**

Run:
```bash
SDL_VIDEODRIVER=dummy ./venv/bin/python -c "
import pygame, config, billiar_ball, menu
pygame.init(); pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
# 三按钮 id 都能被各自中心命中
ids = [menu.button_at(x + w // 2, y + h // 2) for _i, _l, x, y, w, h in menu.button_rects()]
assert ids == ['eight', 'nine', 'snooker'], ids
g = billiar_ball.Game(); assert g.scores == [0, 0]
print('OK ids=', ids, 'scores=', g.scores)
pygame.quit()
"
```
Expected: 打印 `OK ids= ['eight', 'nine', 'snooker'] scores= [0, 0]`，无异常

> 交互式校验（需真实显示，人工执行）：`./venv/bin/python billiar_ball.py` → 封面三按钮竖排 → 点 9球/斯诺克 浮现「…敬请期待」约 2 秒后消失 → 点 8球模式 进游戏。

- [ ] **Step 6: 提交**

```bash
git add billiar_ball.py
git commit -m "feat(game): 封面按 id 分派 — 9球/斯诺克临时提示，8球进游戏"
```

---

## Self-Review

**Spec coverage：**
- 竖排三按钮 8球/9球/斯诺克 → Task 2 `BUTTONS` + `button_rects`，Task 3 绘制。✓
- 8球进游戏 → Task 4 `clicked == 'eight'`。✓
- 9球/斯诺克临时提示「…敬请期待」 → Task 4 分派设 `hint_text`/`hint_until`，Task 3 `draw_menu_hint`。✓
- 提示数秒后自动消失 → Task 4 Step 3 `get_ticks() < hint_until` 否则清空，秒数来自 `config.MENU_HINT_SECONDS`（Task 1）。✓
- 接口 `button_rects` 返回五元组带 label + `button_at` 返回 id → Task 2。✓
- 几何纯逻辑单测（顺序/居中/不重叠/命中/空隙/角落） → Task 2 Step 1。✓
- 新常量 `MENU_BTN_GAP`/`MENU_HINT_SECONDS`/`COLOR_MENU_HINT` → Task 1。✓

**Placeholder scan：** 无 TBD/TODO；每个代码步骤均给出完整代码与精确命令。✓

**Type consistency：**
- `button_rects()` 五元组 `(id, label, x, y, w, h)`：Task 2 定义、Task 2 测试解包、Task 3 `draw_menu`/`draw_menu_hint` 解包、Task 4 Step 5 冒烟解包——全一致（解包变量名可不同，位置一致即可）。✓
- `button_at(x, y)` 返回 id 字符串或 None：Task 2 定义、Task 4 分派比较 `'eight'/'nine'/'snooker'`、Task 2 测试断言——一致。✓
- 旧 `button_rect`/`button_hit` 在 Task 2 移除；其调用点 renderer（Task 3）、main（Task 4）同步改掉，无悬空引用残留在最终状态。Task 2 提交后到 Task 3 完成前存在中间态引用缺失，已在 Task 2 说明中标注为预期。✓
- `hint_text`/`hint_until` 在 Task 4 Step 1 声明，Step 2/3 使用——一致。✓
