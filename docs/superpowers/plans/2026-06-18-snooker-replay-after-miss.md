# 斯诺克 F 键「让对手重打」实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 斯诺克模式下,对手解斯诺克失败(犯规且没碰到目标球、母球未落袋、未形成自由球)后,做斯诺克的一方可按 `F` 把球复位、让对手重打。

**Architecture:** 出杆前在 `_fire()` 拍整桌快照;`resolve_shot()` 在斯诺克犯规换人分支里依据"对手是否碰到 ball-on(用击球前阶段)"设置 `_can_replay` 标志;`STATE_AIMING` 下按 `F`(仿现有 `G` 键)调 `_replay_after_miss()` 还原球位、交还回合、保留罚分。判定"没解到"用 `rules.first_cue_contact` + 现有 `snooker_balls_on`。

**Tech Stack:** Python 3.14, pygame(SDL dummy 驱动跑测试), pytest, dataclass。

**关键陷阱:** `resolve_shot()` 走到犯规分支(`billiar_ball.py:213`)时,斯诺克阶段已在上方(约 `:128-129`)被推进。计算 ball-on 必须用**击球前**的 `phase`/`next_color`,所以要在斯诺克分支最顶端先把它们快照成局部变量 `phase_before` / `next_color_before`。

---

### Task 1: `rules.first_cue_contact` 公开辅助

**Files:**
- Modify: `rules.py`(在 `_first_cue_contact` 之后新增)
- Test: `tests/test_rules.py`

- [ ] **Step 1: 写失败测试**

加到 `tests/test_rules.py` 末尾。先确认文件顶部已 `from physics import Event, EVENT_BALL_HIT`(若没有则在该测试内 import)。

```python
def test_first_cue_contact_returns_number_when_cue_hits_ball():
    from rules import first_cue_contact
    from physics import Event, EVENT_BALL_HIT
    events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 7})]
    assert first_cue_contact(events) == 7


def test_first_cue_contact_returns_none_when_no_contact():
    from rules import first_cue_contact
    assert first_cue_contact([]) is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_rules.py::test_first_cue_contact_returns_number_when_cue_hits_ball -v`
Expected: FAIL — `ImportError: cannot import name 'first_cue_contact'`

- [ ] **Step 3: 实现**

在 `rules.py` 的 `_first_cue_contact` 函数定义之后新增:

```python
def first_cue_contact(events):
    """母球首个碰到的球号(无接触返回 None)。供 Game 层判断解球是否成功。"""
    number, _idx = _first_cue_contact(events)
    return number
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_rules.py -k first_cue_contact -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add rules.py tests/test_rules.py
git commit -m "feat(rules): 新增公开 first_cue_contact 辅助

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `reset()` 初始化复位状态字段

**Files:**
- Modify: `billiar_ball.py`(`reset()` 方法,约 `:73-91` 之间的状态初始化块)
- Test: `tests/test_game_fire_spin.py`

- [ ] **Step 1: 写失败测试**

加到 `tests/test_game_fire_spin.py` 末尾(沿用文件已有的 `game_module` fixture):

```python
def test_reset_initializes_replay_fields(game_module):
    g = game_module.Game(mode='snooker')
    assert g._can_replay is False
    assert g._snooker_pre_shot is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_game_fire_spin.py::test_reset_initializes_replay_fields -v`
Expected: FAIL — `AttributeError: 'Game' object has no attribute '_can_replay'`

- [ ] **Step 3: 实现**

在 `billiar_ball.py` 的 `reset()` 中,`self._was_free_ball = False`(约 `:87`)之后新增两行:

```python
        # F 键复位（斯诺克）：对手解球失败后做斯诺克方可让其重打
        self._snooker_pre_shot = None   # 出杆前整桌快照
        self._can_replay = False        # 当前是否可按 F 复位
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_game_fire_spin.py::test_reset_initializes_replay_fields -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): reset 初始化 F 复位状态字段

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `_fire()` 出杆前拍快照并清复位资格

**Files:**
- Modify: `billiar_ball.py`(`_fire()` 方法,约 `:348-376`)
- Test: `tests/test_game_fire_spin.py`

- [ ] **Step 1: 写失败测试**

加到 `tests/test_game_fire_spin.py` 末尾。复用文件已有的 `_snooker_game` helper。

```python
def test_fire_snapshots_balls_and_clears_replay(game_module):
    g = _snooker_game(game_module)
    g._can_replay = True            # 上一轮残留资格,出杆应清除
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g._can_replay is False
    assert g._snooker_pre_shot is not None
    assert g._snooker_pre_shot['current'] == g.current
    assert g._snooker_pre_shot['phase'] == g._snooker_phase
    # 快照含所有球
    assert len(g._snooker_pre_shot['balls']) == len(g.balls)


def test_fire_no_snapshot_in_eight_ball(game_module):
    g = game_module.Game()          # 8 球模式
    g.state = game_module.STATE_AIMING
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g._snooker_pre_shot is None
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_game_fire_spin.py::test_fire_snapshots_balls_and_clears_replay -v`
Expected: FAIL — `KeyError` / 快照为 None

- [ ] **Step 3: 实现**

在 `billiar_ball.py` 的 `_fire()` 中,`self.shot_events = []`(约 `:356`)之后新增:

```python
        # 斯诺克：出杆前拍整桌快照，供对手解球失败后 F 复位；自己出杆清除上一轮资格
        if self.mode == 'snooker':
            self._snooker_pre_shot = {
                'balls': [(b.number, b.x, b.y, b.vx, b.vy, b.on_table) for b in self.balls],
                'phase': self._snooker_phase,
                'next_color': self._snooker_next_color,
                'current': self.current,
            }
        self._can_replay = False
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_game_fire_spin.py -k "fire_snapshots or fire_no_snapshot" -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): _fire 出杆前拍整桌快照

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `resolve_shot` 设置 `_can_replay`

**Files:**
- Modify: `billiar_ball.py`(`resolve_shot()` 斯诺克分支顶端约 `:106-109` + 犯规分支约 `:226-235`;import 行 `:15-18`)
- Test: `tests/test_game_fire_spin.py`

判定逻辑:对手犯规、母球未落袋、用**击球前**阶段算出的 ball-on 里**不含**首碰球(或首碰为 None)、且未拿到自由球 → `_can_replay = True`。其余所有路径 `_can_replay = False`。

- [ ] **Step 1: 写失败测试**

加到 `tests/test_game_fire_spin.py` 末尾:

```python
def test_can_replay_when_opponent_misses_ball_on(game_module):
    # 红球阶段先碰黑球(21)=没碰红球(ball-on),母球未落袋 → 做斯诺克方可复位
    g = _snooker_game(game_module)
    g._snooker_phase = 'red'
    g._snooker_next_color = None
    g._snooker_pre_shot = {'balls': [], 'phase': 'red', 'next_color': None, 'current': 0}
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 21})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g._can_replay is True


def test_cannot_replay_when_opponent_hits_ball_on(game_module):
    # 红球阶段先碰红球(7=ball-on)但空杆犯规 → 解到了,不可复位
    g = _snooker_game(game_module)
    g._snooker_phase = 'red'
    g._snooker_next_color = None
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 7})]  # 碰红球后无球进袋/碰库 → 空杆犯规
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g._can_replay is False


def test_cannot_replay_when_cue_potted(game_module):
    # 犯规且母球落袋 → 走 D 区,不可复位
    g = _snooker_game(game_module)
    g.shot_events = [Event(EVENT_POCKETED, {'number': 0, 'pocket': 0})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g._can_replay is False


def test_cannot_replay_when_free_ball_awarded(game_module):
    # 对手犯规且你被斯诺克拿到自由球 → 不可复位
    g = _snooker_game(game_module)
    for b in g.balls:
        b.on_table = b.number in (0, 1, 20)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 100.0, 250.0
    red = next(b for b in g.balls if b.number == 1)
    red.x, red.y = 500.0, 250.0
    pink = next(b for b in g.balls if b.number == 20)
    pink.x, pink.y = 300.0, 250.0   # 挡住唯一红球
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 20})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g.free_ball is True
    assert g._can_replay is False
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_game_fire_spin.py -k "can_replay or cannot_replay" -v`
Expected: FAIL(`_can_replay` 未被 resolve_shot 设置 / 未导入 first_cue_contact)

- [ ] **Step 3: 实现**

(a) 更新 `billiar_ball.py` 顶部 `from rules import (...)`(约 `:15-18`),加入 `first_cue_contact`:

```python
from rules import (evaluate_nine_ball_shot, evaluate_shot,
                   evaluate_snooker_shot, first_cue_contact,
                   is_legal_first_contact,
                   is_legal_nine_ball_contact, is_snookered,
                   snooker_balls_on)
```

(b) 在 `resolve_shot()` 斯诺克分支最顶端(`elif self.mode == 'snooker':` 之后、调用 `evaluate_snooker_shot` 之前,约 `:107`)快照击球前阶段:

```python
            phase_before = self._snooker_phase
            next_color_before = self._snooker_next_color
```

(c) 在犯规分支「母球未落袋 + 斯诺克」块里(约 `:227-235`),在设置 `self.free_ball` 之后、补一段计算 `_can_replay`。改写该 `if self.mode == 'snooker':` 块为:

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
                    # 对手没碰到 ball-on(用击球前阶段判定)且未拿自由球 → 可让其重打
                    fc = first_cue_contact(self.shot_events)
                    balls_on_before = snooker_balls_on(
                        phase_before, next_color_before, self.balls)
                    self._can_replay = (
                        (fc is None or fc not in balls_on_before)
                        and not self.free_ball)
```

(d) 确保其他路径 `_can_replay` 为 False:由 Task 3 的 `_fire()` 已在每次出杆时置 False,而 `resolve_shot` 仅在上述唯一分支置 True,故非该分支自然保持 False。无需额外赋值。

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_game_fire_spin.py -k "can_replay or cannot_replay" -v`
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): resolve_shot 判定 F 复位资格

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `_replay_after_miss()` + `F` 键处理

**Files:**
- Modify: `billiar_ball.py`(新增 `_replay_after_miss` 方法 + `handle_event` 中 `G` 键块附近约 `:404-409` 加 `F` 键块)
- Test: `tests/test_game_fire_spin.py`

- [ ] **Step 1: 写失败测试**

加到 `tests/test_game_fire_spin.py` 末尾:

```python
def test_f_key_replays_after_miss(game_module):
    g = _snooker_game(game_module)
    g.current = 0                     # 做斯诺克方是玩家1
    g._snooker_scores = [0, 4]        # 对手犯规已罚 4 分给玩家1,复位后应保留
    # 记录"对手击球前"的球位快照(把一颗红球放在已知位置)
    red = next(b for b in g.balls if b.number == 1)
    snapshot_balls = [(b.number, b.x, b.y, 0.0, 0.0, b.on_table) for b in g.balls]
    g._snooker_pre_shot = {
        'balls': snapshot_balls,
        'phase': 'red', 'next_color': None,
        'current': 1,                 # 对手是玩家2
    }
    g._snooker_phase = 'color'        # 推进后的脏值,复位应还原成 'red'
    g._snooker_next_color = 19
    g._can_replay = True
    # 把红球挪走,验证复位会还原
    red.x, red.y = 12.0, 34.0
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
    g.handle_event(ev, (0, 0))
    red_after = next(b for b in g.balls if b.number == 1)
    assert (red_after.x, red_after.y) != (12.0, 34.0)   # 已还原
    assert g.current == 1                                # 交还给对手
    assert g._snooker_phase == 'red'                     # 阶段还原
    assert g._snooker_next_color is None
    assert g._can_replay is False                        # 资格清除
    assert g._snooker_scores == [0, 4]                   # 罚分保留


def test_f_key_ignored_when_cannot_replay(game_module):
    g = _snooker_game(game_module)
    g.current = 0
    g._can_replay = False
    g._snooker_pre_shot = None
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f)
    g.handle_event(ev, (0, 0))
    assert g.current == 0             # 没有任何变化
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_game_fire_spin.py::test_f_key_replays_after_miss -v`
Expected: FAIL(红球未还原 / `current` 未变)

- [ ] **Step 3: 实现**

(a) 在 `billiar_ball.py` 新增方法(放在 `resolve_shot` 之后、`_placement_valid` 之前,约 `:269`):

```python
    def _replay_after_miss(self):
        """斯诺克:把球复位到对手击球前,交还回合让其重打。罚分保留。"""
        snap = self._snooker_pre_shot
        by_number = {num: (x, y, on) for num, x, y, vx, vy, on in snap['balls']}
        for b in self.balls:
            if b.number in by_number:
                x, y, on = by_number[b.number]
                b.x, b.y, b.vx, b.vy, b.on_table = x, y, 0.0, 0.0, on
        self._snooker_phase = snap['phase']
        self._snooker_next_color = snap['next_color']
        self.current = snap['current']
        self._can_replay = False
        self.free_ball = False
        self.place_mode = None
        self.state = STATE_AIMING
        self.message = "复位：对手重新解斯诺克"
```

(b) 在 `handle_event` 的 `G` 键块(约 `:404-409`)之后新增 `F` 键块:

```python
        # F 复位:做斯诺克方让解球失败的对手在原局面重打
        if (self.state == STATE_AIMING and self.mode == 'snooker'
                and self._can_replay and self._snooker_pre_shot is not None
                and ev.type == pygame.KEYDOWN and ev.key == pygame.K_f):
            self._replay_after_miss()
            return
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_game_fire_spin.py -k "f_key" -v`
Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): F 键复位让对手重打

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: HUD 显示 `F=让对手重打`

**Files:**
- Modify: `renderer.py`(`draw_hud` 签名 + snooker 提示块约 `:216-237`)
- Modify: `billiar_ball.py`(`draw` 中 `draw_hud` 调用约 `:532-534`)
- Test: `tests/test_game_fire_spin.py`(冒烟:带 can_replay 调用 draw 不报错)

- [ ] **Step 1: 写失败测试**

加到 `tests/test_game_fire_spin.py` 末尾(验证 `draw_hud` 接受 `can_replay` 参数):

```python
def test_draw_hud_accepts_can_replay(game_module):
    import renderer
    screen = pygame.display.get_surface()
    font = pygame.font.SysFont('arial', 18)
    # 不抛异常即可(关键字参数存在)
    renderer.draw_hud(screen, font, [None, None], 0, "msg",
                      mode='snooker', snooker_scores=[0, 0], can_replay=True)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python -m pytest tests/test_game_fire_spin.py::test_draw_hud_accepts_can_replay -v`
Expected: FAIL — `TypeError: draw_hud() got an unexpected keyword argument 'can_replay'`

- [ ] **Step 3: 实现**

(a) `renderer.py` 修改 `draw_hud` 签名(约 `:216-217`):

```python
def draw_hud(screen, font, player_groups, current_player, message, mode='eight',
             snooker_scores=None, can_replay=False):
```

(b) 替换 snooker 提示块(约 `:236-237`)为:

```python
    if mode == 'snooker':
        hint_text = "G=僵局重摆"
        if can_replay:
            hint_text += "   F=让对手重打"
        hint = font.render(hint_text, True, config.COLOR_TEXT)
        screen.blit(hint, (40, 78))
```

(c) `billiar_ball.py` 的 `draw` 中更新调用(约 `:532-534`):

```python
        renderer.draw_hud(screen, font, self.player_groups, self.current, self.message,
                          mode=self.mode,
                          snooker_scores=self._snooker_scores if self.mode == 'snooker' else None,
                          can_replay=self._can_replay)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `python -m pytest tests/test_game_fire_spin.py::test_draw_hud_accepts_can_replay -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add renderer.py billiar_ball.py tests/test_game_fire_spin.py
git commit -m "feat(snooker): HUD 显示 F=让对手重打 提示

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 全量回归 + 收尾

**Files:** 无新增改动,仅验证。

- [ ] **Step 1: 跑全部测试**

Run: `python -m pytest -q`
Expected: 全绿(原有测试 + 本次新增全部 PASS)

- [ ] **Step 2: 手动冒烟(可选,需显示器)**

Run: `python billiar_ball.py`
进入斯诺克模式,制造一杆对手犯规且没碰目标球(母球未落袋),确认 HUD 出现 `F=让对手重打`,按 `F` 后球位还原、轮到对手。

- [ ] **Step 3: 若有未提交改动则提交**

```bash
git status
# 若干净则跳过;否则:
git add -A && git commit -m "test(snooker): F 复位全量回归

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 自检

**1. Spec 覆盖:**
- 触发四条件 → Task 4(犯规+母球未落袋+没碰 ball-on+无自由球)✓
- 出杆前快照 → Task 3 ✓
- F 键还原+交还回合+罚分保留 → Task 5 ✓
- `first_cue_contact` 辅助 → Task 1 ✓
- HUD 提示 → Task 6 ✓
- 测试 → 每个 Task 含 TDD,Task 7 回归 ✓

**2. 占位符扫描:** 无 TBD/TODO,每个代码步骤含完整代码。

**3. 类型/命名一致性:** `_snooker_pre_shot`(dict: balls/phase/next_color/current)、`_can_replay`(bool)、`first_cue_contact`(返回 number|None)、`_replay_after_miss`(无参方法)在 Task 1/2/3/4/5/6 间命名一致。快照 balls 元组顺序 `(number, x, y, vx, vy, on_table)` 在 Task 3 写、Task 5 读一致。
