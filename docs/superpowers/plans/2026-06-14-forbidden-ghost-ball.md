# 非法首球时鬼球显示禁止样式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 瞄准时若母球射线第一颗会撞上的球不是合法首球（按美式8球规则），把鬼球（假想球）画成红圈 + 对角斜杠的禁止样式。

**Architecture:** 在纯逻辑层抽出可复用的合法性判定函数 `rules.is_legal_first_contact`，让 `cue.predict_aim` 把命中球号带回渲染层，`billiar_ball.Game.draw` 用当前实时状态构造 `is_forbidden` 回调传给 `renderer.draw_aim`，渲染层据此切换鬼球样式。规则/逻辑层无 pygame 依赖、可单测；渲染层不写单测（项目惯例）。

**Tech Stack:** Python 3.14、pygame-ce 2.6、pytest。运行测试：`pool_game/.venv` 在本机实际为 `pool_game/venv`，用 `venv/bin/python -m pytest`。

---

## File Structure

- `cue.py` — `AimPrediction` namedtuple 末尾加 `target_number` 字段；`predict_aim` 填入命中球号。
- `rules.py` — 新增纯函数 `is_legal_first_contact(...)`；`evaluate_shot` 改为复用它。
- `config.py` — 新增颜色常量 `COLOR_GHOST_FORBIDDEN`。
- `renderer.py` — `draw_aim` / `_draw_separation` 接收 `is_forbidden` 回调，非法时画红圈 + 斜杠。
- `billiar_ball.py` — `Game.draw` 构造 `is_forbidden` 回调并传入 `draw_aim`。
- `tests/test_cue.py` — 加一条断言鬼球带回球号的测试。
- `tests/test_rules.py` — 加 `is_legal_first_contact` 的单元测试。

测试运行根目录为仓库父目录，命令统一为：
`cd /Users/jason/work/projects && pool_game/venv/bin/python -m pytest pool_game/tests -q`

---

## Task 1: `cue.AimPrediction` 带回命中球号

**Files:**
- Modify: `pool_game/cue.py`（`AimPrediction` 定义约 52-60 行；`predict_aim` 的 return 约 124-125 行）
- Test: `pool_game/tests/test_cue.py`

- [ ] **Step 1: 写失败测试**

在 `pool_game/tests/test_cue.py` 末尾追加：

```python
def test_predict_returns_target_number():
    # 命中 3 号球，预测应带回球号 3
    balls = [Ball(0, 0.0, 0.0), Ball(3, 100.0, 0.0)]
    pred = predict_aim(0.0, 0.0, 1.0, 0.0, balls)
    assert pred is not None
    assert pred.target_number == 3
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -m pytest pool_game/tests/test_cue.py::test_predict_returns_target_number -q`
Expected: FAIL，`AttributeError: 'AimPrediction' object has no attribute 'target_number'`

- [ ] **Step 3: 给 namedtuple 加字段**

在 `pool_game/cue.py` 中，把 `AimPrediction` 类定义改为在末尾新增一个字段（保留原有字段与注释）：

```python
class AimPrediction(NamedTuple):
    """母球沿瞄准方向飞行，撞到第一颗球时的分离角预测。"""
    ghost_x: float        # 母球接触瞬间的球心（鬼球位置）
    ghost_y: float
    target_x: float       # 被撞目标球球心
    target_y: float
    object_dir: tuple     # 目标球去向（沿两球连心线）单位向量
    cue_dir: tuple        # 母球去向（切线，90° 定杆分离）单位向量
    target_number: int    # 被撞目标球号（用于判定是否合法首球）
```

- [ ] **Step 4: return 时填入球号**

在 `pool_game/cue.py` 的 `predict_aim` 末尾，把 return 改为：

```python
    return AimPrediction(ghost_x, ghost_y, best_ball.x, best_ball.y,
                         (nx, ny), (cx, cy), best_ball.number)
```

- [ ] **Step 5: 运行测试，确认全绿**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -m pytest pool_game/tests/test_cue.py -q`
Expected: PASS（含原有所有 cue 测试，按字段名访问不受影响）

- [ ] **Step 6: 提交**

```bash
cd /Users/jason/work/projects/pool_game
git add cue.py tests/test_cue.py
git commit -m "feat(cue): AimPrediction 带回命中球号 target_number"
```

---

## Task 2: `rules.is_legal_first_contact` 纯函数 + 复用重构

**Files:**
- Modify: `pool_game/rules.py`（新增函数；改 `evaluate_shot` 约 44-53 行的首球判定分支）
- Test: `pool_game/tests/test_rules.py`

- [ ] **Step 1: 写失败测试**

在 `pool_game/tests/test_rules.py` 顶部 import 改为同时引入新函数：

```python
from rules import evaluate_shot, is_legal_first_contact
```

在文件末尾追加：

```python
# ---- 合法首球判定（瞄准时鬼球禁止样式用） ----

def test_legal_first_open_table_non_eight_is_legal():
    assert is_legal_first_contact(3, open_table=True, shooter_group=None, shooter_on_eight=False) is True
    assert is_legal_first_contact(11, open_table=True, shooter_group=None, shooter_on_eight=False) is True


def test_legal_first_open_table_eight_is_illegal():
    assert is_legal_first_contact(8, open_table=True, shooter_group=None, shooter_on_eight=False) is False


def test_legal_first_assigned_own_group_legal_opponent_illegal():
    # 我是 solid：碰 solid 合法，碰 stripe / 8 非法
    assert is_legal_first_contact(2, open_table=False, shooter_group='solid', shooter_on_eight=False) is True
    assert is_legal_first_contact(9, open_table=False, shooter_group='solid', shooter_on_eight=False) is False
    assert is_legal_first_contact(8, open_table=False, shooter_group='solid', shooter_on_eight=False) is False


def test_legal_first_on_eight_only_eight_legal():
    assert is_legal_first_contact(8, open_table=False, shooter_group='solid', shooter_on_eight=True) is True
    assert is_legal_first_contact(2, open_table=False, shooter_group='solid', shooter_on_eight=True) is False
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -m pytest pool_game/tests/test_rules.py -q`
Expected: FAIL，`ImportError: cannot import name 'is_legal_first_contact'`

- [ ] **Step 3: 新增纯函数**

在 `pool_game/rules.py` 中 `_first_cue_contact` 之后、`evaluate_shot` 之前新增：

```python
def is_legal_first_contact(number, open_table, shooter_group, shooter_on_eight):
    """该球作为母球首个碰到的球是否合法。与 evaluate_shot 的犯规判定一致。

    开放球台：除 8 号外都合法；打 8 阶段：仅 8 号合法；已分组：仅本组合法。
    """
    if open_table:
        return number != 8
    if shooter_on_eight:
        return number == 8
    return group_of(number) == shooter_group
```

- [ ] **Step 4: `evaluate_shot` 复用该函数**

在 `pool_game/rules.py` 的 `evaluate_shot` 中，把现有首球判定分支：

```python
    else:
        fc_group = group_of(first_contact)
        if open_table:
            if first_contact == 8:
                foul, reason = True, '开放球台不能先碰8号球'
        elif shooter_on_eight:
            if first_contact != 8:
                foul, reason = True, '应先碰8号球'
        elif fc_group != shooter_group:
            foul, reason = True, '先碰到对方或错误的球'
```

替换为：

```python
    elif not is_legal_first_contact(first_contact, open_table, shooter_group, shooter_on_eight):
        if open_table:
            reason = '开放球台不能先碰8号球'
        elif shooter_on_eight:
            reason = '应先碰8号球'
        else:
            reason = '先碰到对方或错误的球'
        foul = True
```

- [ ] **Step 5: 运行测试，确认全绿**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -m pytest pool_game/tests/test_rules.py -q`
Expected: PASS（新增 4 条 + 现有 rules 测试，证明重构未改变 `evaluate_shot` 行为）

- [ ] **Step 6: 提交**

```bash
cd /Users/jason/work/projects/pool_game
git add rules.py tests/test_rules.py
git commit -m "feat(rules): 抽出 is_legal_first_contact 并复用于 evaluate_shot"
```

---

## Task 3: `config` 新增禁止鬼球颜色

**Files:**
- Modify: `pool_game/config.py`（颜色区，`COLOR_GHOST` 定义之后，约 66 行）

- [ ] **Step 1: 新增颜色常量**

在 `pool_game/config.py` 中 `COLOR_GHOST = ...` 那一行之后新增：

```python
COLOR_GHOST_FORBIDDEN = (230, 60, 60)  # 非法首球时鬼球（红圈 + 斜杠）
```

- [ ] **Step 2: 确认无导入/语法错误**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -c "import sys; sys.path.insert(0,'pool_game'); import config; print(config.COLOR_GHOST_FORBIDDEN)"`
Expected: 打印 `(230, 60, 60)`

- [ ] **Step 3: 提交**

```bash
cd /Users/jason/work/projects/pool_game
git add config.py
git commit -m "feat(config): 新增 COLOR_GHOST_FORBIDDEN 禁止鬼球颜色"
```

---

## Task 4: `renderer` 画禁止样式鬼球

**Files:**
- Modify: `pool_game/renderer.py`（`draw_aim` 约 49-64 行；`_draw_separation` 约 128-140 行）

渲染层无单测（项目惯例：renderer 不测）。本任务结束用导入冒烟测试 + 手动跑游戏验证。

- [ ] **Step 1: `draw_aim` 透传 is_forbidden 回调**

在 `pool_game/renderer.py` 中，把 `draw_aim` 签名与调用 `_draw_separation` 的分支改为：

```python
def draw_aim(screen, cue, aim_dir, balls=None, spin_v=0.0, is_forbidden=None):
    """瞄准线（朝 aim_dir 单位方向）+ 分离角预测。aim_dir 为母球去向。

    spin_v: 垂直杆法，传入 predict_aim 改变母球分离方向（跟/定/缩杆）。
    is_forbidden: 可选回调 number->bool，命中球非法时鬼球画成红圈 + 斜杠。
    """
    if aim_dir is None:
        return
    ux, uy = aim_dir
    # 分离角预测：母球射线若撞到球，瞄准线止于鬼球，并画出分叉路径
    pred = predict_aim(cue.x, cue.y, ux, uy, balls, spin_v=spin_v) if balls else None
    if pred is None:
        # 未命中：固定长度瞄准线
        end = (int(cue.x + ux * 220), int(cue.y + uy * 220))
        pygame.draw.line(screen, config.COLOR_LINE, (int(cue.x), int(cue.y)), end, 1)
    else:
        forbidden = bool(is_forbidden and is_forbidden(pred.target_number))
        _draw_separation(screen, cue, pred, forbidden)
```

- [ ] **Step 2: `_draw_separation` 按 forbidden 切换鬼球样式**

在 `pool_game/renderer.py` 中，把 `_draw_separation` 整体替换为：

```python
def _draw_separation(screen, cue, pred, forbidden=False):
    """瞄准线止于鬼球，鬼球处画轮廓圈 + 目标球进球路径。

    forbidden=True 时鬼球画成红圈 + 对角斜杠（非法首球提示）。
    """
    r = config.BALL_RADIUS
    gx, gy = int(pred.ghost_x), int(pred.ghost_y)
    # 瞄准线：母球 → 鬼球接触点
    pygame.draw.line(screen, config.COLOR_LINE,
                     (int(cue.x), int(cue.y)), (gx, gy), 1)
    # 鬼球：母球撞击瞬间位置的空心轮廓（非法时变红并叠加禁止斜杠）
    ring_color = config.COLOR_GHOST_FORBIDDEN if forbidden else config.COLOR_GHOST
    pygame.draw.circle(screen, ring_color, (gx, gy), r, 1)
    if forbidden:
        off = int(r * 0.707)   # 对角斜杠端点（圆上 45°）
        pygame.draw.line(screen, config.COLOR_GHOST_FORBIDDEN,
                         (gx - off, gy + off), (gx + off, gy - off), 2)
    # 目标球路径：沿连心线方向
    ox, oy = pred.object_dir
    pygame.draw.line(screen, config.COLOR_OBJECT_PATH, (gx, gy),
                     (int(gx + ox * 160), int(gy + oy * 160)), 2)
```

- [ ] **Step 3: 导入冒烟测试**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -c "import sys; sys.path.insert(0,'pool_game'); import renderer; print('ok')"`
Expected: 打印 `ok`（无语法/导入错误）

- [ ] **Step 4: 提交**

```bash
cd /Users/jason/work/projects/pool_game
git add renderer.py
git commit -m "feat(renderer): 非法首球时鬼球画红圈 + 禁止斜杠"
```

---

## Task 5: `billiar_ball.Game.draw` 接线 is_forbidden 回调

**Files:**
- Modify: `pool_game/billiar_ball.py`（顶部 import 区约 12 行；`Game.draw` 的 `STATE_AIMING` 分支约 301-303 行）

- [ ] **Step 1: 引入 rules 的判定函数**

在 `pool_game/billiar_ball.py` 顶部，把：

```python
from rules import evaluate_shot
```

改为：

```python
from rules import evaluate_shot, is_legal_first_contact
```

- [ ] **Step 2: draw 中构造并传入回调**

在 `pool_game/billiar_ball.py` 的 `Game.draw` 中，把 `STATE_AIMING` 分支里调用 `draw_aim` 的语句：

```python
        if self.state == STATE_AIMING:
            renderer.draw_aim(screen, find_cue(self.balls), self.aim_dir,
                              self.balls, -self.english[1])   # spin_v = -dy（上=跟杆）
```

替换为：

```python
        if self.state == STATE_AIMING:
            group = self.player_groups[self.current]
            on_eight = self._shooter_on_eight()
            forbidden = lambda n: not is_legal_first_contact(
                n, self.open_table, group, on_eight)
            renderer.draw_aim(screen, find_cue(self.balls), self.aim_dir,
                              self.balls, -self.english[1],   # spin_v = -dy（上=跟杆）
                              is_forbidden=forbidden)
```

- [ ] **Step 3: 导入冒烟测试**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -c "import sys; sys.path.insert(0,'pool_game'); import billiar_ball; print('ok')"`
Expected: 打印 `ok`

- [ ] **Step 4: 跑全部单测**

Run: `cd /Users/jason/work/projects && pool_game/venv/bin/python -m pytest pool_game/tests -q`
Expected: 全绿（原 36 条 + 本次新增 5 条 = 41 条）

- [ ] **Step 5: 手动验证（人工）**

Run: `cd /Users/jason/work/projects/pool_game && venv/bin/python billiar_ball.py`
观察：开球完成、分组后，瞄准对方组别球或（未到打8阶段时）8 号球，鬼球应显示为红圈 + 斜杠；瞄准本组球时鬼球仍为白色细圈。关闭窗口退出。

- [ ] **Step 6: 提交**

```bash
cd /Users/jason/work/projects/pool_game
git add billiar_ball.py
git commit -m "feat(game): 瞄准非法首球时鬼球显示禁止样式"
```

---

## Self-Review 结果

- **Spec 覆盖：** 合法规则 → Task 2；带回球号 → Task 1；禁止颜色 → Task 3；红圈+斜杠渲染 → Task 4；接线实时状态 → Task 5；测试 → Task 1/2 含测试代码，Task 5 跑全量。"不隐藏目标球路径" 在 Task 4 的 `_draw_separation` 中目标球路径行保持原样。✓
- **Placeholder 扫描：** 无 TBD/TODO，每个代码步骤均含完整代码。✓
- **类型/命名一致性：** `target_number`（Task 1 定义）在 Task 4 以 `pred.target_number` 使用；`is_legal_first_contact` 签名 `(number, open_table, shooter_group, shooter_on_eight)` 在 Task 2 定义、Task 5 调用一致；`is_forbidden` 回调签名 `number->bool` 在 Task 4 接收、Task 5 提供一致。✓
