# 斯诺克规则完善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正斯诺克模式的规则 bug,补全可自动化的标准规则(正确罚分、红球阶段进彩犯规、犯规后母球留原地、自由球几何检测、僵局重摆)。

**Architecture:** 纯规则逻辑放 `rules.py`(无 pygame 依赖,易单测);几何障碍检测也放 `rules.py`;状态机/交互改动放 `billiar_ball.py`。测试在 `tests/test_rules.py` 用伪造的 physics 事件与 Ball 列表驱动,Game 层改动靠现有 `tests/test_game_fire_spin.py` 的 SDL dummy 模式覆盖。

**Tech Stack:** Python 3, pygame 2.6(仅 Game 层),pytest。运行测试统一用 `./venv/bin/python -m pytest`。

---

## 测试运行约定

本仓库无全局 pytest,必须用 venv:
```bash
./venv/bin/python -m pytest <路径> -v
```
`rules.py` 与 `balls.py` 无 pygame 依赖,测试直接 import 即可。

## 文件结构

| 文件 | 职责 | 本计划改动 |
|------|------|-----------|
| `rules.py` | 纯规则判定 + 几何障碍检测 | 修 `evaluate_snooker_shot`;新增 `snooker_balls_on`、`is_snookered` |
| `billiar_ball.py` | 状态机/交互 | 犯规后母球处理、自由球状态、`G` 键、瞄准合法首碰放宽 |
| `tests/test_rules.py` | 规则单测 | 新增斯诺克测试块 |
| `tests/test_game_fire_spin.py` | Game 层回归 | 修 fixture 指向 `billiar_ball.py`(既有 bug) |

## physics 事件形状(参考,勿改)

```
EVENT_POCKETED  data = {'number': int, 'pocket': int}
EVENT_BALL_HIT  data = {'a': int, 'b': int}
EVENT_CUSHION   data = {'number': int}
```
斯诺克球号:0=母球,1–15=红球,16=黄,17=绿,18=棕,19=蓝,20=粉,21=黑。
`snooker_value`:红=1,黄=2,绿=3,棕=4,蓝=5,粉=6,黑=7(已存在于 `balls.py`)。

---

## Task 0: 修复既有的 test_game_fire_spin fixture

`23.py` 已改名为 `billiar_ball.py`,导致该测试文件全部 error。先修好,后续 Game 层改动才有回归保护。

**Files:**
- Modify: `tests/test_game_fire_spin.py:18-23`

- [ ] **Step 1: 运行确认当前是 error**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -q`
Expected: 5 errors, `FileNotFoundError: ... 23.py`

- [ ] **Step 2: 把 fixture 改为按模块名直接 import**

将 `tests/test_game_fire_spin.py` 顶部 fixture(第 15–25 行)整体替换为:

```python
@pytest.fixture(scope="module")
def game_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1000, 600))
    import billiar_ball
    yield billiar_ball
    pygame.quit()
```

同时删除文件顶部现在已无用的 `import importlib.util`(第 6 行)。保留 `import os`。同时把模块 docstring 里提到 `23.py` 的那段说明(第 2-5 行)改成:

```python
"""Game._fire 的杆法符号契约回归测试。需要 pygame,用 SDL dummy 驱动以免依赖真实显示。"""
```

- [ ] **Step 3: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -q`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add tests/test_game_fire_spin.py
git commit -m "test: 修复 fire_spin 测试 fixture 指向已改名的 billiar_ball.py"
```

---

## Task 1: ball-on 集合辅助函数 `snooker_balls_on`

返回当前阶段合法目标球号集合。供罚分计算与自由球检测复用。

**Files:**
- Modify: `rules.py`(在 `is_legal_snooker_contact` 附近新增函数)
- Test: `tests/test_rules.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_rules.py` 末尾追加。先在文件顶部 import 处加入 `snooker_balls_on`(与现有 import 同风格):

```python
from rules import snooker_balls_on
from balls import Ball


def _snooker_balls(reds=range(1, 16), colors=range(16, 22), cue=True):
    out = []
    if cue:
        out.append(Ball(number=0, x=0, y=0))
    for n in reds:
        out.append(Ball(number=n, x=0, y=0))
    for n in colors:
        out.append(Ball(number=n, x=0, y=0))
    return out


def test_balls_on_red_phase_is_all_reds():
    balls = _snooker_balls()
    assert snooker_balls_on('red', None, balls) == set(range(1, 16))


def test_balls_on_named_color_is_single():
    balls = _snooker_balls()
    assert snooker_balls_on('color', 19, balls) == {19}


def test_balls_on_free_choice_color_is_all_colors_on_table():
    # 红球已清空、next_color=None(自选彩球阶段),只剩黄绿在台
    balls = _snooker_balls(reds=[], colors=[16, 17])
    assert snooker_balls_on('color', None, balls) == {16, 17}
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k balls_on -v`
Expected: FAIL,`ImportError: cannot import name 'snooker_balls_on'`

- [ ] **Step 3: 实现函数**

在 `rules.py` 中 `is_legal_snooker_contact` 定义之后(约第 175 行后)新增:

```python
def snooker_balls_on(phase, next_color, balls):
    """当前阶段合法目标球号集合(ball-on)。

    红球阶段:台面所有红球(1-15)。
    定彩阶段(next_color 非 None):那一颗指定彩球。
    自选彩球阶段(next_color is None):台面所有彩球(16-21)。
    """
    on_table = {b.number for b in balls if b.on_table}
    if phase == 'red':
        return {n for n in on_table if 1 <= n <= 15}
    if next_color is not None:
        return {next_color}
    return {n for n in on_table if 16 <= n <= 21}
```

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k balls_on -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add rules.py tests/test_rules.py
git commit -m "feat(rules): 新增 snooker_balls_on 目标球集合辅助函数"
```

---

## Task 2: 红球阶段打进彩球判犯规 + 正确罚分

修正 `evaluate_snooker_shot` 的两处规则错误。

**Files:**
- Modify: `rules.py:183-301`(`evaluate_snooker_shot`)
- Test: `tests/test_rules.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_rules.py` 末尾追加(顶部 import 增加 `evaluate_snooker_shot`,与现有 import 同风格)。`Table` 来自 `table` 模块:

```python
from rules import evaluate_snooker_shot
from table import Table


def _table():
    return Table(0, 0, 1000, 500)


def test_red_phase_potting_color_is_foul():
    # 红球阶段,母球先碰红球(合法首碰)但把蓝球(19)打进 → 犯规,不得分
    balls = _snooker_balls()
    events = [hit(0, 3), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert pts == 0
    # 误进蓝球(5分),罚分取 max(4, 蓝5) = 5
    assert foul_pts == 5


def test_red_phase_potting_red_scores_one():
    balls = _snooker_balls()
    events = [hit(0, 3), pocket(3, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is False
    assert pts == 1
    assert phase == 'color'      # 打进红球后转打彩球
    assert nc is None            # 自选彩球


def test_foul_wrong_first_contact_black_penalty_seven():
    # 红球阶段,母球先碰黑球(21) → 犯规,罚 7
    balls = _snooker_balls()
    events = [hit(0, 21)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert foul_pts == 7


def test_foul_air_shot_min_penalty_four():
    # 空杆:母球没碰任何球 → 罚 4
    balls = _snooker_balls()
    events = [cushion(0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert foul_pts == 4
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k "red_phase or foul_wrong or air_shot" -v`
Expected: `test_red_phase_potting_color_is_foul` FAIL(现状会给蓝球加分、不算犯规);其余按现状部分通过/失败。

- [ ] **Step 3: 修改 evaluate_snooker_shot 的犯规与罚分段**

在 `rules.py` 的 `evaluate_snooker_shot` 内,定位"犯规判定"块(约第 203-215 行)。在该块**之后、罚分计算之前**,新增"红球阶段误进彩球"判定。把从 `# 犯规判定` 到罚分计算结束(约第 203-222 行)整体替换为:

```python
    # 当前合法目标球集合
    balls_on = snooker_balls_on(phase, next_color, balls)

    # 犯规判定
    if cue_pocketed:
        foul, reason = True, '母球落袋'
    elif first_contact is None:
        foul, reason = True, '母球未碰到任何球'
    elif phase == 'red' and not (1 <= first_contact <= 15):
        foul, reason = True, '应先碰红球'
    elif phase == 'color':
        if next_color is not None and first_contact != next_color:
            color_name = _SNOOKER_COLOR_NAMES.get(next_color, '?')
            foul, reason = True, f'应先碰{color_name}球'
        elif next_color is None and not (16 <= first_contact <= 21):
            foul, reason = True, '应先碰彩球'

    # 红球阶段打进彩球:即使首碰红球合法,落袋彩球也算犯规
    if not foul and phase == 'red':
        illegal_potted = [n for n in object_pocketed if 16 <= n <= 21]
        if illegal_potted:
            foul, reason = True, '红球阶段打进彩球'

    # 彩球阶段打进非目标球:落袋了不该进的球
    if not foul and phase == 'color':
        illegal_potted = [n for n in object_pocketed if n not in balls_on]
        if illegal_potted:
            foul, reason = True, '打进了非目标彩球'

    # 犯规罚分:取 4、目标球分值、误碰首球分值、误进球最高分值 的最大值
    if foul:
        candidates = [4]
        for n in balls_on:
            candidates.append(snooker_value(n))
        if first_contact is not None:
            candidates.append(snooker_value(first_contact))
        for n in object_pocketed:
            candidates.append(snooker_value(n))
        foul_points = max(candidates)
```

注意:此处引用了 `snooker_balls_on`(Task 1 已在同模块定义)与 `snooker_value`(函数顶部已 `from balls import snooker_value`)。删除原先 `if foul:` 罚分块(`foul_points = max(4, snooker_value(first_contact)) ...`),由上面新块取代。

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k "red_phase or foul_wrong or air_shot" -v`
Expected: 全部 passed

- [ ] **Step 5: 运行整体规则测试确认无回归**

Run: `./venv/bin/python -m pytest tests/test_rules.py -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add rules.py tests/test_rules.py
git commit -m "fix(rules): 红球阶段进彩判犯规 + 罚分取目标/误碰/误进最高值"
```

---

## Task 3: 清彩顺序与阶段推进回归测试

为已有但未测的红彩交替/清彩逻辑补测试,锁住行为(此 Task 不改产品代码,除非测试暴露 bug)。

**Files:**
- Test: `tests/test_rules.py`

- [ ] **Step 1: 写测试**

在 `tests/test_rules.py` 末尾追加:

```python
def test_red_phase_miss_keeps_red_phase():
    # 红球阶段碰红球但没进、有碰库 → 不犯规,仍是红球阶段
    balls = _snooker_balls()
    events = [hit(0, 3), cushion(3)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is False
    assert phase == 'red'
    assert nc is None


def test_color_order_yellow_then_green():
    # 清彩阶段:打进黄(16),下一颗应是绿(17)
    balls = _snooker_balls(reds=[], colors=[16, 17, 18, 19, 20, 21])
    # 模拟黄球已落袋
    for b in balls:
        if b.number == 16:
            b.on_table = False
    events = [hit(0, 16), pocket(16, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', 16, _table())
    assert result.foul is False
    assert pts == 2
    assert phase == 'color'
    assert nc == 17


def test_color_phase_no_respot_in_color_order():
    # 清彩阶段进的彩球不复位(respot 应为空)
    balls = _snooker_balls(reds=[], colors=[16, 17, 18, 19, 20, 21])
    events = [hit(0, 16), pocket(16, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', 16, _table())
    assert respot == []


def test_red_phase_color_respots():
    # 红彩交替:红球阶段后打彩(自选),彩球需复位
    balls = _snooker_balls()
    events = [hit(0, 19), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', None, _table())
    assert result.foul is False
    assert pts == 5
    assert respot == [19]   # 蓝球复位
    assert phase == 'red'   # 还有红球 → 回到打红球
```

- [ ] **Step 2: 运行**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k "red_phase_miss or color_order or color_phase_no_respot or red_phase_color_respots" -v`
Expected: 全部 passed。**若某条失败**,说明现有阶段推进逻辑有 bug:停下,改用 systematic-debugging,修 `rules.py` 后再继续,不要改测试去迁就错误行为。

- [ ] **Step 3: Commit**

```bash
git add tests/test_rules.py
git commit -m "test(rules): 补斯诺克清彩顺序与阶段推进回归测试"
```

---

## Task 4: 几何障碍检测 `is_snookered`

判断母球是否被障碍(无法直线打到任一 ball-on 两侧最薄边)。纯几何,放 `rules.py`。

**Files:**
- Modify: `rules.py`(新增 `_segment_hits_circle`、`is_snookered`)
- Test: `tests/test_rules.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_rules.py` 末尾追加(顶部 import 增加 `is_snookered`):

```python
from rules import is_snookered
import config


def _ball(n, x, y):
    return Ball(number=n, x=x, y=y)


def test_not_snookered_clear_path():
    # 母球在左,目标红球在右,中间无阻挡 → 没被障碍
    cue = _ball(0, 100, 250)
    target = _ball(1, 500, 250)
    balls = [cue, target]
    assert is_snookered(cue, {1}, balls) is False


def test_snookered_blocker_directly_between():
    # 母球与目标球同一水平线,正中间放一颗彩球完全挡住两侧切线 → 被障碍
    cue = _ball(0, 100, 250)
    target = _ball(1, 500, 250)
    r = config.BALL_RADIUS
    # 阻挡球放在两者中点,挡住整条通路(含两侧切线)
    blocker = _ball(20, 300, 250)
    balls = [cue, target, blocker]
    assert is_snookered(cue, {1}, balls) is True


def test_not_snookered_if_any_ball_on_reachable():
    # 两颗 ball-on:一颗被挡、一颗通路清晰 → 不算被障碍
    cue = _ball(0, 100, 250)
    blocked = _ball(1, 500, 250)
    blocker = _ball(20, 300, 250)
    clear = _ball(2, 100, 450)   # 母球正下方,通路清晰
    balls = [cue, blocked, blocker, clear]
    assert is_snookered(cue, {1, 2}, balls) is False
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k snookered -v`
Expected: FAIL,`ImportError: cannot import name 'is_snookered'`

- [ ] **Step 3: 实现几何检测**

在 `rules.py` 顶部已有 `from balls import group_of`,新增 import:把该行改为
```python
from balls import group_of, snooker_value
```
(注意:`evaluate_snooker_shot` 内部原本有局部 `from balls import snooker_value`,提到模块顶部后可删除那行局部 import,但保留也无害——本步骤只在顶部新增,不强制删局部。)

在文件末尾新增:

```python
import math
import config


def _segment_hits_circle(x0, y0, x1, y1, cx, cy, radius):
    """线段 (x0,y0)->(x1,y1) 是否与圆心 (cx,cy) 半径 radius 的圆相交。"""
    dx, dy = x1 - x0, y1 - y0
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return (x0 - cx) ** 2 + (y0 - cy) ** 2 <= radius ** 2
    # 投影参数 t,夹到 [0,1]
    t = ((cx - x0) * dx + (cy - y0) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    px, py = x0 + t * dx, y0 + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2 <= radius ** 2


def _path_clear_to_edge(cue, target, all_balls, edge_sign):
    """母球能否沿擦过 target 某侧最薄边的直线打到该 target。

    edge_sign: +1=右侧切线, -1=左侧切线。
    用半径 2*R 的扫掠圆检测路径上是否有其他球阻挡。
    """
    r = config.BALL_RADIUS
    dx, dy = target.x - cue.x, target.y - cue.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return True
    ux, uy = dx / dist, dy / dist
    # 法向(垂直于瞄准线),指向某侧偏移一个球半径,使射线擦过 target 边缘
    nx, ny = -uy, ux
    aim_x = target.x + edge_sign * r * nx
    aim_y = target.y + edge_sign * r * ny
    for b in all_balls:
        if b.number in (0, target.number) or not b.on_table:
            continue
        # 阻挡判定:其他球到 (cue->aim点) 线段距离 < 2R(母球扫掠)
        if _segment_hits_circle(cue.x, cue.y, aim_x, aim_y,
                                b.x, b.y, 2 * r):
            return False
    return True


def is_snookered(cue, balls_on, all_balls):
    """母球是否被障碍:对每颗 ball-on,两侧最薄边至少一侧可直线打到则不算障碍。

    所有 ball-on 的两侧都被挡 → 返回 True。
    """
    for tgt in all_balls:
        if tgt.number not in balls_on or not tgt.on_table:
            continue
        right_clear = _path_clear_to_edge(cue, tgt, all_balls, +1)
        left_clear = _path_clear_to_edge(cue, tgt, all_balls, -1)
        if right_clear or left_clear:
            return False
    return True
```

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k snookered -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add rules.py tests/test_rules.py
git commit -m "feat(rules): 新增 is_snookered 几何障碍检测"
```

---

## Task 5: Game 层 — 犯规后母球处理修正

只有母球落袋才回 D 区摆球;其他犯规母球留原地、对手原位打(无摆球特权)。

**Files:**
- Modify: `billiar_ball.py:202-220`(`resolve_shot` 内母球落袋复位 + 回合切换的犯规分支)
- Test: `tests/test_game_fire_spin.py`(同一 game_module fixture,新增斯诺克 Game 测试)

- [ ] **Step 1: 写失败测试**

在 `tests/test_game_fire_spin.py` 末尾追加。这些测试构造一个斯诺克 Game,手动塞入 shot_events 再调 `resolve_shot`,断言状态:

```python
from balls import find_cue as _find_cue
from physics import Event, EVENT_POCKETED, EVENT_BALL_HIT


def _snooker_game(game_module):
    g = game_module.Game(mode='snooker')
    g.state = game_module.STATE_AIMING
    g.current = 0
    return g


def test_snooker_foul_cue_stays_when_not_potted(game_module):
    # 犯规但母球未落袋:对手原位接着打,不进摆球状态
    g = _snooker_game(game_module)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 333.0, 222.0
    # 红球阶段先碰黑球(21) → 犯规,母球未落袋
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 21})]
    g._was_ball_in_hand = False
    g.resolve_shot()
    assert g.current == 1                      # 换对手
    assert g.state == game_module.STATE_AIMING # 原位打,不摆球
    assert g.place_mode is None                # 无摆球特权
    assert (cue.x, cue.y) == (333.0, 222.0)    # 母球没动


def test_snooker_foul_cue_potted_goes_to_d(game_module):
    # 犯规且母球落袋:对手在 D 区摆球
    g = _snooker_game(game_module)
    # 母球落袋(犯规)
    g.shot_events = [Event(EVENT_POCKETED, {'number': 0, 'pocket': 0})]
    g._was_ball_in_hand = False
    g.resolve_shot()
    assert g.current == 1
    assert g.state == game_module.STATE_BREAK_PLACE
    assert g.place_mode == 'kitchen'
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -k "foul_cue" -v`
Expected: `test_snooker_foul_cue_stays_when_not_potted` FAIL(现状斯诺克任何犯规都进 STATE_BREAK_PLACE)。

- [ ] **Step 3: 修改 resolve_shot**

在 `billiar_ball.py` 的 `resolve_shot` 中,定位"母球落袋:复位并交给对手自由球"块(约第 201-209 行)与紧随的"回合切换"犯规分支(约第 210-220 行)。

将犯规分支(`if result.foul:` 起,约第 211-220 行)替换为:

```python
        if result.foul:
            self.message = f"玩家{self.current + 1} 犯规：{result.foul_reason}"
            self.current = 1 - self.current
            if result.cue_pocketed:
                # 母球落袋:对手在 D 区(斯诺克)/开球区(8球)摆放
                if self.mode == 'snooker':
                    self.place_mode = 'kitchen'
                    self.state = STATE_BREAK_PLACE
                    self.message = "犯规后在D区移动鼠标摆放白球，点击确定"
                else:
                    self.place_mode = 'free'
                    self.state = STATE_BALL_IN_HAND
            else:
                # 母球未落袋:斯诺克原位接着打;8球给自由球
                if self.mode == 'snooker':
                    self.place_mode = None
                    self.state = STATE_AIMING
                else:
                    self.place_mode = 'free'
                    self.state = STATE_BALL_IN_HAND
```

说明:母球落袋复位的代码(`if result.cue_pocketed:` 块,约第 201-209 行)保持不动——它在犯规分支之前已把母球摆回 D 区中心/开球点。8 球行为维持原样(犯规一律自由球),仅斯诺克区分母球是否落袋。

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -k "foul_cue" -v`
Expected: 2 passed

- [ ] **Step 5: 运行整体测试确认无回归**

Run: `./venv/bin/python -m pytest -q`
Expected: all passed(此前的 5 个 error 已在 Task 0 修复)

- [ ] **Step 6: Commit**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "fix(snooker): 犯规后仅母球落袋才回D区,否则对手原位接着打"
```

---

## Task 6: Game 层 — 自由球判给与玩法

犯规后轮到对手时,若被障碍则判自由球;自由球阶段任意首碰合法,进球得 ball-on 分值,替身彩球复位。

**Files:**
- Modify: `billiar_ball.py`(`reset` 加 `self.free_ball`;Task 5 的犯规分支末尾判障碍;`resolve_shot` 斯诺克计分段处理自由球;`_fire` 清除标志;`_snooker_legal_contact` / 瞄准放宽;HUD 提示)
- Test: `tests/test_game_fire_spin.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_game_fire_spin.py` 末尾追加:

```python
def test_free_ball_set_when_snookered_after_foul(game_module):
    # 构造:对手犯规后,母球被一颗彩球完全挡住所有红球 → 判自由球
    g = _snooker_game(game_module)
    # 清掉除少量球外的所有球,手摆一个明确的障碍局面
    for b in g.balls:
        b.on_table = b.number in (0, 1, 20)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 100.0, 250.0
    red = next(b for b in g.balls if b.number == 1)
    red.x, red.y = 500.0, 250.0
    pink = next(b for b in g.balls if b.number == 20)
    pink.x, pink.y = 300.0, 250.0   # 正中间挡住
    # 对手犯规(先碰粉球),母球未落袋
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 20})]
    g._was_ball_in_hand = False
    g.resolve_shot()
    assert g.free_ball is True


def test_free_ball_cleared_after_fire(game_module):
    g = _snooker_game(game_module)
    g.free_ball = True
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g.free_ball is False
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -k "free_ball" -v`
Expected: FAIL,`AttributeError: 'Game' object has no attribute 'free_ball'`

- [ ] **Step 3a: reset 初始化标志**

在 `billiar_ball.py` 的 `reset()` 中,与其他实例标志一起(在 `self.place_mode = 'kitchen'` 附近,约第 84 行后)新增:

```python
        self.free_ball = False       # 自由球:本杆可把任意球当 ball-on
```

- [ ] **Step 3b: import is_snookered 与 snooker_balls_on**

在 `billiar_ball.py` 顶部的 rules import(第 15-17 行)中加入 `is_snookered`、`snooker_balls_on`:

```python
from rules import (evaluate_nine_ball_shot, evaluate_shot,
                   evaluate_snooker_shot, is_legal_first_contact,
                   is_legal_nine_ball_contact, is_snookered,
                   snooker_balls_on)
```

- [ ] **Step 3c: 犯规分支末尾判障碍(仅斯诺克、母球未落袋)**

在 Task 5 改好的犯规分支里,斯诺克"母球未落袋、原位打"那条(`self.place_mode = None; self.state = STATE_AIMING`)之后,追加自由球判定。把那两行替换为:

```python
                if self.mode == 'snooker':
                    self.place_mode = None
                    self.state = STATE_AIMING
                    cue = find_cue(self.balls)
                    balls_on = snooker_balls_on(
                        self._snooker_phase, self._snooker_next_color, self.balls)
                    if is_snookered(cue, balls_on, self.balls):
                        self.free_ball = True
                        self.message = "自由球：可击打任意球作为目标球"
```

- [ ] **Step 3d: _fire 清除标志**

在 `billiar_ball.py` 的 `_fire()` 末尾(`self.place_mode = None` 那行附近,约第 355 行)新增:

```python
        self.free_ball = False       # 出杆后自由球特权失效
```

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -k "free_ball" -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): 犯规后被障碍判自由球,出杆后清除"
```

---

## Task 7: 自由球计分 + 瞄准合法性放宽

自由球阶段:首碰任意球合法;进球得 ball-on 分值;被当替身的彩球复位。

**Files:**
- Modify: `rules.py`(`evaluate_snooker_shot` 增加 `free_ball` 参数)
- Modify: `billiar_ball.py`(`resolve_shot` 传入 `self.free_ball`;`_snooker_legal_contact` 放宽)
- Test: `tests/test_rules.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_rules.py` 末尾追加:

```python
def test_free_ball_pot_color_scores_ball_on_value():
    # 自由球 + 红球阶段:把蓝球(19)当红球打进 → 得 1 分(红球分值),蓝球复位,不犯规
    balls = _snooker_balls()
    events = [hit(0, 19), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table(), free_ball=True)
    assert result.foul is False
    assert pts == 1            # 红球阶段自由球得 1 分
    assert respot == [19]      # 替身彩球复位
    assert phase == 'color'    # 等同打进一颗红球 → 转打彩


def test_free_ball_any_first_contact_legal():
    # 自由球 + 红球阶段:首碰彩球(本应犯规)→ 不犯规
    balls = _snooker_balls()
    events = [hit(0, 20), cushion(20)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table(), free_ball=True)
    assert result.foul is False
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k "free_ball_pot or free_ball_any" -v`
Expected: FAIL,`evaluate_snooker_shot() got an unexpected keyword argument 'free_ball'`

- [ ] **Step 3a: evaluate_snooker_shot 增加 free_ball 参数**

把 `rules.py` 的 `evaluate_snooker_shot` 签名(约第 183 行)改为:

```python
def evaluate_snooker_shot(events, balls, phase, next_color, table, free_ball=False):
```

在"犯规判定"块的开头(`balls_on = ...` 之后),当 `free_ball` 为真时跳过首碰/误进类犯规——母球落袋仍犯规。具体:把 Task 2 写的犯规判定块用一个 `if not free_ball:` 包住首碰与误进相关分支,母球落袋判定保留在外。替换为:

```python
    # 当前合法目标球集合
    balls_on = snooker_balls_on(phase, next_color, balls)

    # 犯规判定
    if cue_pocketed:
        foul, reason = True, '母球落袋'
    elif first_contact is None:
        foul, reason = True, '母球未碰到任何球'
    elif not free_ball:
        # 非自由球:正常首碰/误进判定
        if phase == 'red' and not (1 <= first_contact <= 15):
            foul, reason = True, '应先碰红球'
        elif phase == 'color':
            if next_color is not None and first_contact != next_color:
                color_name = _SNOOKER_COLOR_NAMES.get(next_color, '?')
                foul, reason = True, f'应先碰{color_name}球'
            elif next_color is None and not (16 <= first_contact <= 21):
                foul, reason = True, '应先碰彩球'

    # 红球阶段打进彩球:非自由球时,即使首碰红球合法,落袋彩球也算犯规
    if not foul and not free_ball and phase == 'red':
        illegal_potted = [n for n in object_pocketed if 16 <= n <= 21]
        if illegal_potted:
            foul, reason = True, '红球阶段打进彩球'

    # 彩球阶段打进非目标球
    if not foul and not free_ball and phase == 'color':
        illegal_potted = [n for n in object_pocketed if n not in balls_on]
        if illegal_potted:
            foul, reason = True, '打进了非目标彩球'
```

(罚分块、`if foul:` 不变。)

- [ ] **Step 3b: 自由球计分**

在 `evaluate_snooker_shot` 的"计分"块(`if not foul:` 内,约 Task 2 之后的 `points_scored` 计算处)处理自由球。定位:
```python
    points_scored = 0
    respot_colors = []
    if not foul:
        for n in object_pocketed:
            points_scored += snooker_value(n)
            if phase == 'red' and n >= 16 and n <= 21:
                respot_colors.append(n)
```
替换为:

```python
    points_scored = 0
    respot_colors = []
    if not foul:
        if free_ball:
            # 自由球:进的球按当前 ball-on 分值计,替身彩球复位
            ball_on_value = min((snooker_value(n) for n in balls_on), default=1)
            for n in object_pocketed:
                points_scored += ball_on_value
                # 红球阶段把彩球当红球打进 → 复位
                if phase == 'red' and 16 <= n <= 21:
                    respot_colors.append(n)
        else:
            for n in object_pocketed:
                points_scored += snooker_value(n)
                if phase == 'red' and 16 <= n <= 21:
                    respot_colors.append(n)
```

说明:红球阶段 ball-on 是红球,`ball_on_value=1`;清彩自选阶段 `balls_on` 是台面彩球集合,取 `min` 对应"最低分彩球"作为 ball-on 值(与规则"自由球得活球相应分值"一致)。

- [ ] **Step 3c: Game 传入 free_ball**

在 `billiar_ball.py` 的 `resolve_shot` 中,斯诺克调用 `evaluate_snooker_shot` 处(约第 104-106 行)加上 `self.free_ball`:

```python
            result, pts, foul_pts, respot, new_phase, next_color = evaluate_snooker_shot(
                self.shot_events, self.balls, self._snooker_phase,
                self._snooker_next_color, self.table, free_ball=self.free_ball)
```

- [ ] **Step 3d: 瞄准合法首碰放宽**

在 `billiar_ball.py` 的 `draw()` 中,斯诺克 forbidden lambda(约第 491-492 行)改为自由球时任意球都合法:

```python
            elif self.mode == 'snooker':
                if self.free_ball:
                    forbidden = lambda n: n == 0
                else:
                    forbidden = lambda n: not _snooker_legal_contact(
                        n, self._snooker_phase, self._snooker_next_color)
```

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_rules.py -k "free_ball_pot or free_ball_any" -v`
Expected: 2 passed

- [ ] **Step 5: 运行整体测试确认无回归**

Run: `./venv/bin/python -m pytest -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add rules.py billiar_ball.py tests/test_rules.py
git commit -m "feat(snooker): 自由球计分(得ball-on分值/替身复位)+ 瞄准放宽"
```

---

## Task 8: Game 层 — `G` 键僵局重摆

`STATE_AIMING` 下按 `G`:本局作废重摆,跨局胜场保留。

**Files:**
- Modify: `billiar_ball.py`(`handle_event` 在 STATE_AIMING 段处理 KEYDOWN G)
- Test: `tests/test_game_fire_spin.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_game_fire_spin.py` 末尾追加:

```python
import pygame as _pygame


def test_stalemate_g_key_resets_frame(game_module):
    g = game_module.Game(mode='snooker')
    g.state = game_module.STATE_AIMING
    g._snooker_scores = [30, 20]
    g.scores = [2, 1]                      # 跨局胜场
    # 模拟台面被打乱:移走几颗球
    for b in g.balls[:5]:
        b.on_table = False
    ev = _pygame.event.Event(_pygame.KEYDOWN, key=_pygame.K_g)
    g.handle_event(ev, (0, 0))
    assert g._snooker_scores == [0, 0]     # 本局分清零
    assert g.scores == [2, 1]              # 跨局胜场保留
    assert all(b.on_table for b in g.balls)  # 重新摆球
```

- [ ] **Step 2: 运行确认失败**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -k "stalemate" -v`
Expected: FAIL(G 键当前无效,`_snooker_scores` 不会清零)

- [ ] **Step 3: handle_event 处理 G 键**

在 `billiar_ball.py` 的 `handle_event` 中,定位 `if self.state != STATE_AIMING: return`(约第 384-385 行)之前,在 STATE_AIMING 处理段开头插入。具体在 `if self.state != STATE_AIMING:` 这段**之前**加:

```python
        if (self.state == STATE_AIMING and self.mode == 'snooker'
                and ev.type == pygame.KEYDOWN and ev.key == pygame.K_g):
            self.reset()
            self.message = "僵局：重新摆球，按原顺序重赛"
            return
```

- [ ] **Step 4: 运行验证通过**

Run: `./venv/bin/python -m pytest tests/test_game_fire_spin.py -k "stalemate" -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): G键僵局重摆,跨局胜场保留"
```

---

## Task 9: HUD 提示 G 键与自由球状态

让玩家看得到自由球状态与 G 键提示。

**Files:**
- Modify: `renderer.py`(`draw_hud` 已接收 message;自由球已通过 message 体现)。本 Task 仅补一行 G 键操作提示。
- Test: 视觉,无单测;运行冒烟。

- [ ] **Step 1: 查看 draw_hud 当前签名与 message 渲染**

Run: `grep -n "def draw_hud\|def draw_back_hint\|message" renderer.py`
Expected: 确认 message 已被绘制(`billiar_ball.py:506` 传入 message)。

- [ ] **Step 2: 在斯诺克 HUD 追加 G 键提示**

定位 `renderer.py` 的 `draw_hud`,在斯诺克分支(渲染 `snooker_scores` 处)附近,追加一行小字提示。若 `draw_hud` 已有 `mode` 参数,在 `mode == 'snooker'` 时多绘一行:

```python
    if mode == 'snooker':
        hint = font.render("G=僵局重摆", True, config.COLOR_TEXT)
        screen.blit(hint, (config.TABLE_LEFT, config.TABLE_BOTTOM + 30))
```

(具体坐标按 `draw_hud` 内既有布局微调,确保不与现有文字重叠;`COLOR_TEXT` 若不存在,用 `draw_hud` 内现用的文字颜色常量。)

- [ ] **Step 3: 冒烟运行(手动)**

Run: `./venv/bin/python billiar_ball.py`
进斯诺克模式,确认底部出现 "G=僵局重摆" 提示,自由球触发时顶部 message 显示 "自由球：可击打任意球作为目标球"。关闭窗口结束。

- [ ] **Step 4: Commit**

```bash
git add renderer.py
git commit -m "feat(snooker): HUD 增加 G 键僵局提示"
```

---

## Task 10: 全量回归与清理

**Files:** 无新增

- [ ] **Step 1: 跑全部测试**

Run: `./venv/bin/python -m pytest -q`
Expected: all passed,0 error。

- [ ] **Step 2: 冒烟跑四种入口**

Run: `./venv/bin/python billiar_ball.py`
依次进 8 球 / 9 球 / 斯诺克,各打一杆,确认无异常报错,斯诺克犯规后母球行为正确、被障碍时出现自由球提示。

- [ ] **Step 3: 检查 git 状态干净**

Run: `git status`
Expected: 仅余本计划相关已提交改动,无遗漏未跟踪文件(`__pycache__` 已在忽略或可无视)。

---

## 自检对照(spec 覆盖)

- 第 1 部分(规则引擎):Task 1(ball-on)+ Task 2(红球进彩犯规、罚分)✓
- 第 2 部分(犯规后母球):Task 5 ✓
- 第 3 部分(自由球):Task 4(几何)+ Task 6(判给)+ Task 7(计分/瞄准)✓
- 第 4 部分(G 键僵局):Task 8 + Task 9(提示)✓
- 第 5 部分(测试):Task 1/2/3/4/7 的单测 + Task 5/6/8 的 Game 测试 ✓
- 附:Task 0 修复既有 fixture(非 spec 范围,但阻塞 Game 层测试)
