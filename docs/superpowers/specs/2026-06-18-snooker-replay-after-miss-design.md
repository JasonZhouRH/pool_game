# 斯诺克 F 键「让对手重打」— 设计文档

日期:2026-06-18

## 背景

标准斯诺克的「miss(未解到)」补救:一方做上斯诺克(母球无法直线打到任一目标球),对手尝试解斯诺克失败(犯规且没碰到 ball-on)时,做斯诺克的一方除了"自己接着打剩下的局面"外,还可以选择**把球摆回对手击球前的位置,让对手重新解一次**。

现有实现(`2026-06-17-snooker-rules-design.md`)已支持"对手原位接着打"(标准犯规流程自然支持),但当时明确**未做** `F` 复位回滚。本设计补上这一项。

参照现有 `G` 键(僵局重摆)的实现模式:`STATE_AIMING` 下按键 → 改状态/还原 → 提示文字,HUD 显示按键提示。

## 范围

| 部分 | 内容 | 主要文件 |
|------|------|---------|
| 1 | "没解到"判定辅助 | `rules.py` |
| 2 | 出杆前快照 + 可复位标志 | `billiar_ball.py` |
| 3 | `F` 键复位处理 | `billiar_ball.py` |
| 4 | HUD 提示 `F=让对手重打` | `renderer.py` |
| 5 | 测试 | `tests/test_game_fire_spin.py` |

## 触发条件(宽松版)

上一杆对手解球后,满足**全部**条件时,轮到你的 `STATE_AIMING` 阶段可按 `F`:

1. 对手那一杆是**犯规**(`result.foul`);
2. 母球**没有落袋**(`not result.cue_pocketed`)——母球落袋走 D 区摆球流程,不适用复位;
3. 对手**没解到目标球**——首碰为空,或首碰的球不在对手的 ball-on 集合里;
4. 你**没有拿到自由球**(`not self.free_ball`)。

> 宽松版:不要求对手"确实被斯诺克"。只要犯规且没碰到 ball-on 就可复位。实现上少一个 `_shooter_snookered` 追踪状态。

判定时机:在 `resolve_shot()` 处理完犯规换人后,设置 `self._can_replay`。`F` 键仅在 `_can_replay` 为真时生效。任何后续动作(开始瞄准/出杆/重新摆球)都不会清除标志;`F` 一旦被按,或对手出杆进入 `STATE_MOVING` 后由 `_fire()` 清除。

## 第 1 部分:"没解到"判定辅助(`rules.py`)

新增公开薄包装(现有 `_first_cue_contact` 为私有):

```python
def first_cue_contact(events):
    """母球首个碰到的球号(无接触返回 None)。供 Game 层判断解球是否成功。"""
    number, _idx = _first_cue_contact(events)
    return number
```

Game 层判断"没解到":

```python
fc = first_cue_contact(self.shot_events)
balls_on = snooker_balls_on(phase_before, next_color_before, balls)
missed = fc is None or fc not in balls_on
```

注意 ball-on 必须用**对手击球前**的阶段(`phase_before` / `next_color_before`),在 `resolve_shot` 推进阶段之前快照。

## 第 2 部分:出杆前快照(`billiar_ball.py`)

新增状态字段(在 `reset()` 中初始化):
- `self._snooker_pre_shot = None` — 出杆前整桌快照
- `self._can_replay = False` — 当前是否可按 F 复位

在 `_fire()` 中,仅斯诺克模式,出杆前(物理推进之前)拍快照:

```python
if self.mode == 'snooker':
    self._snooker_pre_shot = {
        'balls': [(b.number, b.x, b.y, b.vx, b.vy, b.on_table) for b in self.balls],
        'phase': self._snooker_phase,
        'next_color': self._snooker_next_color,
        'current': self.current,
    }
self._can_replay = False   # 自己出杆 → 清除上一轮的可复位资格
```

`_fire()` 已有大量"出杆后清状态"逻辑,`_can_replay = False` 放在一起。

## 第 3 部分:`resolve_shot` 设置可复位标志 + `F` 键处理

### 设置标志

在 `resolve_shot()` 的斯诺克犯规分支(母球未落袋、换人后),计算:

```python
# 对手没碰到 ball-on(用击球前阶段),且未拿到自由球 → 允许做斯诺克方按 F 复位
fc = first_cue_contact(self.shot_events)
balls_on_before = snooker_balls_on(phase_before, next_color_before, self.balls)
self._can_replay = (fc is None or fc not in balls_on_before) and not self.free_ball
```

其余所有分支(非犯规、母球落袋、续杆等)将 `_can_replay = False`。

### `F` 键处理(仿 `G` 键,`handle_event` 中)

```python
if (self.state == STATE_AIMING and self.mode == 'snooker'
        and self._can_replay and self._snooker_pre_shot is not None
        and ev.type == pygame.KEYDOWN and ev.key == pygame.K_f):
    self._replay_after_miss()
    return
```

`_replay_after_miss()`:
- 按快照还原每颗球的 `x, y, vx(=0), vy(=0), on_table`(还原时速度归零,避免残留);
- 恢复 `_snooker_phase`、`_snooker_next_color`;
- `self.current = 快照里的 current`(交还给犯规方/解球失败方);
- `self._can_replay = False`;`self.free_ball = False`;
- `self.state = STATE_AIMING`;
- 提示:`"复位:对手重新解斯诺克"`。

**罚分保留**:已在 `resolve_shot` 给对手加的罚分不退。这是标准规则——只复位球位,不退分。

## 第 4 部分:HUD 提示(`renderer.py`)

`draw_hud` 现有 `mode == 'snooker'` 时显示 `G=僵局重摆`。可复位时追加 `F=让对手重打`。

新增参数 `can_replay=False`:

```python
if mode == 'snooker':
    hint = "G=僵局重摆"
    if can_replay:
        hint += "   F=让对手重打"
    screen.blit(font.render(hint, True, config.COLOR_TEXT), (40, 78))
```

`Game.draw` 调用处传 `can_replay=self._can_replay`(仅斯诺克意义上,非斯诺克恒 False)。

## 第 5 部分:测试(`tests/test_game_fire_spin.py`)

沿用现有 `_snooker_game` fixture(SDL dummy 驱动):
- **可复位资格**:对手红球阶段先碰黑球(犯规,没碰红球),母球未落袋 → `_can_replay is True`。
- **解到则不可复位**:对手先碰红球(合法 ball-on)但空杆犯规 → `_can_replay is False`(碰到了 ball-on)。
- **自由球时不可复位**:对手犯规且你被斯诺克拿到自由球 → `_can_replay is False`。
- **母球落袋不可复位**:对手犯规且母球落袋 → `_can_replay is False`(走 D 区)。
- **F 还原球位与回合**:设置快照 + `_can_replay`,移动几颗球,按 `K_f` → 球位还原、`current` 回到对手、`_can_replay` 复位、罚分不变。
- **出杆清除资格**:`_can_replay=True` 时自己 `_fire()` → `_can_replay is False`。
- `first_cue_contact`:有接触返回球号、无接触返回 None。

## 不做(超出范围)

- 8 球/9 球不受影响。
- 母球落袋后的复位(走 D 区摆球流程不变)。
- 严格版触发(要求对手确实被斯诺克)——本设计用宽松版。
- 红彩阶段推进、罚分计算等既有逻辑不改。
