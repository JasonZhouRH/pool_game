# 进袋缩小动画 — 设计文档

日期:2026-06-19

## 背景

目前球一进袋(`physics.step` 把 `on_table` 置 False),渲染层立即跳过它(`renderer.draw_balls` 开头 `if not b.on_table: continue`),视觉上是**瞬间消失**,略显突兀。

本设计在球消失前加一段**原地缩小**动画:球在落袋位置从正常半径线性缩到 0,约 0.25 秒,纯视觉,不触碰物理与规则判定。

## 效果(已与用户确认)

- **原地缩小**:动画在落袋瞬间的位置播放,不移动、不被吸向袋心。
- **时长约 0.25 秒**:60fps 下 15 帧,线性缩小,无缓动。
- 缩小期间只画**纯色圆**,不画号码、不画花色带(小尺寸下细节很丑)。

## 关键设计:用独立快照,与物理/规则解耦

不把动画绑在球对象上。原因:球落袋后 `resolve_shot` 可能立即**复位重用**该球——母球落袋复位到开球点/D 区;斯诺克彩球复位到点位。若动画状态绑在球上,复位会让"球又出现在别处"与动画打架。

因此用一个**独立快照列表** `Game.pocketing`,每项记录落袋瞬间的 `{号码, x, y, 帧计数}`。球对象自身不变。

## 范围

| 部分 | 内容 | 主要文件 |
|------|------|---------|
| 1 | 动画快照列表的增加/推进/到点移除(纯逻辑) | `billiar_ball.py` |
| 2 | 落袋时压入快照 + 每帧推进 | `billiar_ball.py` |
| 3 | 绘制缩小中的球 | `renderer.py` |
| 4 | 测试(纯逻辑部分) | `tests/test_pocketing_anim.py` |

## 第 1、2 部分:动画状态(`billiar_ball.py`)

### 常量

落袋动画时长,放 `config.py`:

```python
POCKET_ANIM_FRAMES = 15      # 进袋缩小动画帧数(60fps ≈ 0.25 秒)
```

### 状态字段(`reset()` 中初始化)

```python
self.pocketing = []   # 进袋缩小动画:[{'number','x','y','frame'}, ...]
```

`reset()` 重置时清空,避免重开局残留正在播放的动画。

### 压入快照

`update()` 已在遍历本帧物理事件放音效。在该循环里,遇到 `pocketed` 事件时,按事件携带的球号找到该球的当前坐标,压入快照:

```python
for e in new_events:
    if e.type == 'pocketed':
        self.sound.play_pocket()
        b = next((x for x in self.balls if x.number == e.data['number']), None)
        if b is not None:
            self.pocketing.append({'number': b.number, 'x': b.x, 'y': b.y, 'frame': 0})
    elif e.type == 'ball_hit':
        self.sound.play_ball_hit()
```

> 取坐标的时机:事件在 `physics.step` 内产生,球进袋时 `vx/vy` 被清零、`x/y` 停在袋口附近,本帧 `step` 返回后位置不再变。`update()` 拿到的就是落袋位置,符合"原地"。

### 每帧推进(独立于球是否在动)

新增 `_advance_pocketing()`,每帧无条件调用(**不**放在 `STATE_MOVING` 分支内),保证最后一颗球落袋、状态已切到结算/GAMEOVER 时动画仍能播完:

```python
def _advance_pocketing(self):
    for p in self.pocketing:
        p['frame'] += 1
    self.pocketing = [p for p in self.pocketing
                      if p['frame'] < config.POCKET_ANIM_FRAMES]
```

在 `update()` 末尾调用(在 `STATE_MOVING` 的物理推进之后):

```python
def update(self):
    if self.state == STATE_MOVING:
        ...  # 现有物理推进 + 压入快照 + resolve_shot
    self._advance_pocketing()
```

用**帧计数**而非真实时间:确定性好、可测、与现有 60fps 固定步长一致。

## 第 3 部分:绘制(`renderer.py`)

新增 `draw_pocketing(screen, pocketing, mode)`,在 `draw_pockets` 之后、`draw_balls` 之前或之后调用均可(画在袋口黑洞之上即"缩进洞里"观感;放 `draw_balls` 之后亦可,因落袋球已不在 `draw_balls` 绘制集中,两者不重叠)。本设计放在 `draw_balls` 之后:

```python
def draw_pocketing(screen, pocketing, mode='eight'):
    """绘制正在进袋缩小的球:按 frame 线性缩小的纯色圆,不画号码/花色带。"""
    is_snooker = (mode == 'snooker')
    for p in pocketing:
        t = p['frame'] / config.POCKET_ANIM_FRAMES   # 0→1
        r = max(1, int(config.BALL_RADIUS * (1 - t)))
        color = snooker_ball_color(p['number']) if is_snooker else ball_color(p['number'])
        cx, cy = int(p['x']), int(p['y'])
        pygame.draw.circle(screen, color, (cx, cy), r)
        pygame.draw.circle(screen, (0, 0, 0), (cx, cy), r, 1)
```

`Game.draw` 在 `draw_balls(...)` 之后插入 `renderer.draw_pocketing(screen, self.pocketing, mode=self.mode)`。

> 颜色复用 `ball_color`/`snooker_ball_color`,与 `draw_balls` 一致——母球(0 号)缩小时显示白色圆,无需特殊分支。

## 第 4 部分:测试(`tests/test_pocketing_anim.py`)

纯逻辑可测,不依赖 pygame 绘制。沿用现有 game fixture 的构造方式(SDL dummy 驱动)。

- **压入快照**:构造一颗球落袋,`update()` 一帧后 `pocketing` 含一项,坐标=落袋位置,`frame==1`(压入时 0,本帧推进 +1)。
- **逐帧推进**:连续调用 `_advance_pocketing()`,`frame` 递增。
- **到点移除**:`frame` 达到 `POCKET_ANIM_FRAMES` 后该项被移除,列表空。
- **动画独立于球运动**:即使所有球已停(`state != MOVING`),`_advance_pocketing()` 仍推进并最终清空(验证不卡在某状态)。
- **reset 清空**:`pocketing` 有内容时 `reset()` 后清空。
- **多球同时落袋**:一帧内压入多项,各自独立计时。

## 不做(超出范围)

- 不做"吸向袋心"的位移动画(用户选了原地缩小)。
- 不做缓动曲线(线性即可)。
- 不为母球/8号/特定球做差异化动画。
- 不改动 `physics`、`rules` 任何判定逻辑——动画对规则结算完全无影响。
- 绘制函数本身不单测(依赖 pygame surface,与项目既有 `draw_*` 一致)。
