# 获胜界面动画(碎纸洒落 + 标题弹入)— 设计文档

日期:2026-06-19

## 背景

当前 `renderer.draw_gameover` 是无状态纯绘制:半透明黑底 + 一行正文字号(22)白字
「玩家X 获胜! 按 R 重新开始」,居中。朴素、缺少胜利的仪式感。

本设计为获胜界面加动画:进入 GAMEOVER 瞬间,**彩带碎纸从顶部洒落一波**(约 2.5 秒落完),
同时**标题从小弹大、略回弹后定住**(用 64 号大字),下方小字提示「按 R 重新开始」。

## 效果(已与用户确认)

- **碎纸**:五彩小方块从屏幕顶部洒落,边飘边转,约 2.5 秒落完即消失(**一波**,不循环)。
- **标题弹入**:从小缩放到大、略微回弹后**定住不动**(不做持续呼吸)。
- **提示小字**:标题下方一行「按 R 重新开始」。

## 关键设计:引入"进入界面后的帧计数"

现绘制无状态。动画需要时间量 → 在 `Game` 加 `_gameover_frame` 计数器,进入 GAMEOVER
后每帧 +1。用**帧计数**而非真实时间(确定性、可测,与进袋动画一致)。

复用 `update()` 末尾已有的"刚进入 GAMEOVER"检测(获胜音效那段):
- 首次进入:置 `_gameover_frame = 0`(随 `_win_sound_played` 一起)。
- 之后每帧 `update()`:若处于 GAMEOVER,`_gameover_frame += 1`。
- `reset()`:`_gameover_frame = 0`。

## 范围

| 部分 | 内容 | 主要文件 |
|------|------|---------|
| 1 | 碎纸粒子系统(纯逻辑,可测) | `confetti.py`(新) |
| 2 | 标题弹入缓动函数(纯逻辑,可测) | `confetti.py` 或 `renderer.py` |
| 3 | `_gameover_frame` 计数 | `billiar_ball.py` |
| 4 | `draw_gameover` 扩展:大标题缩放 + 画碎纸 + 提示 | `renderer.py` |
| 5 | 测试 | `tests/test_confetti.py` |

## 第 1 部分:碎纸粒子系统(`confetti.py`,无 pygame 依赖)

纯数学,独立于台球逻辑,可单测。

### 常量(放本模块或 config)

```python
CONFETTI_COUNT = 80          # 粒子数
CONFETTI_FALL_FRAMES = 150   # 一波落完的帧数(60fps ≈ 2.5 秒)
CONFETTI_SIZE = 8            # 方块边长(像素)
CONFETTI_COLORS = [...]      # 复用球色等鲜艳 RGB 列表
```

### 确定性伪随机

测试与 resume 需确定性 → **不使用 `random` 全局状态**。每个粒子的初始 x、初速、
旋转速度由其**序号 i** 经简单哈希式公式导出(如 `math.sin(i*K)` 取小数部分),
保证每次运行一致、可测。

### 接口

```python
def particles_at(frame, width, height):
    """返回第 frame 帧所有在场碎纸的状态列表:
    [{'x','y','color','angle'}, ...]。frame 超过 CONFETTI_FALL_FRAMES 后返回 []。
    """
```

- 第 0 帧:所有粒子在顶部附近(y ≤ 0 或屏幕上沿)。
- 随 frame 增大:y 增大(下落,初速 + 重力),x 轻微横摆,angle 随帧旋转。
- frame ≥ CONFETTI_FALL_FRAMES:返回 `[]`(落完消失)。

> 下落用初速 + 重力模型(`y = y0 + v0*t + 0.5*g*t^2` 的离散化),让碎纸先快后慢/
> 自然加速;x 用正弦摆动模拟飘。

## 第 2 部分:标题弹入缓动

```python
def title_scale(frame):
    """标题缩放系数:frame=0 时≈0,快速放大越过 1(回弹),最终收敛到 1。"""
```

- 用带回弹的缓动(overshoot):如在前 ~20 帧内从 0 升到 ~1.15 再回落到 1.0,之后恒为 1.0。
- 实现可用分段:`t = min(frame/BOUNCE_FRAMES, 1)`,套一个 overshoot 缓动公式
  (如 `1 + c*(t-1)^3 + d*(t-1)^2` 之类),并对 `frame ≥ BOUNCE_FRAMES` 直接返回 1.0。
- frame=0 返回接近 0(从无到有弹出)。

## 第 3 部分:`_gameover_frame` 计数(`billiar_ball.py`)

`reset()` 中初始化:`self._gameover_frame = 0`。

`update()` 末尾现有逻辑(获胜音效检测)扩展:

```python
if self.state == STATE_GAMEOVER:
    if not self._win_sound_played:
        self.sound.play_win()
        self._win_sound_played = True
        self._gameover_frame = 0
    else:
        self._gameover_frame += 1
```

> 首帧(刚进入)为 0,之后递增。draw 用它驱动动画。

## 第 4 部分:`draw_gameover` 扩展(`renderer.py`)

签名增加 `title_font` 与 `frame`:

```python
def draw_gameover(screen, font, title_font, winner_player, frame=0):
    # 半透明黑底(同现有)
    # 1. 碎纸:confetti.particles_at(frame, W, H) → 画旋转小方块
    # 2. 标题:64 号大字渲染「玩家X 获胜!」,按 title_scale(frame) 缩放后居中 blit
    # 3. 提示:小字「按 R 重新开始」在标题下方
```

- 标题缩放:`title_font.render(...)` 得到 surface,再 `pygame.transform.rotozoom`/`smoothscale`
  按 `title_scale(frame)` 缩放,以中心对齐 blit。scale≈0 时跳过绘制(避免 0 尺寸 surface)。
- 碎纸方块:可用 `pygame.transform.rotate` 旋转一个小 Surface,或简化为画无旋转的小方块
  (若旋转开销大);先实现旋转版,smoke test 验证性能可接受。

`Game.draw` 调用处(`billiar_ball.py`)改为传 `title_font` 和 `self._gameover_frame`。
注意:`Game.draw` 当前只接收 `font`,需把 `title_font` 传入 —— `main()` 已有 `title_font`,
经 `game.draw(screen, font, mouse_pos)` 调用;需扩展 `Game.draw` 签名带上 `title_font`。

## 第 5 部分:测试(`tests/test_confetti.py`,纯逻辑)

- **第 0 帧在顶部**:`particles_at(0, W, H)` 所有粒子 y ≤ 屏幕上部小阈值。
- **随帧下落**:某粒子在 frame=30 的 y > 它在 frame=0 的 y。
- **落完消失**:`frame >= CONFETTI_FALL_FRAMES` 时返回 `[]`。
- **粒子数量**:在场期间返回 `CONFETTI_COUNT` 个(落完前)。
- **确定性**:同一 frame 两次调用结果完全一致(不依赖全局随机)。
- **title_scale**:`title_scale(0)` ≈ 0;中途存在 > 1 的峰值(回弹);足够大的 frame 返回 1.0。

绘制函数依赖 pygame surface,按项目惯例不单测,用 smoke test(各 frame 调用不抛异常)。

## 不做(超出范围)

- 不做标题持续呼吸、不做无限循环彩带(用户选"弹入静止""一波洒完")。
- 不做胜利者球闪烁、奖杯图标。
- 不改胜负判定与获胜音效逻辑(仅复用其状态转换点)。
- 不改其它界面(菜单/暂停/HUD)。
