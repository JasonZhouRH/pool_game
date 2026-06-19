# 封面背景音乐 — 设计文档

日期:2026-06-19

## 背景

游戏目前只有 4 个短音效(`cue_hit`/`ball_hit`/`pocket`/`btn_click`),通过 `SoundManager`(`pygame.mixer.Sound`)播放,M 键全局静音。无背景音乐。

本设计在**封面菜单**循环播放一首免版权背景音乐;进入对局/暂停时停止;M 键静音时背景音乐一起静音。

## 决策(已与用户确认)

| 项 | 选择 |
|----|------|
| 音乐来源 | 网上找现成的免版权(CC0/royalty-free)曲子,下载为 `sounds/bgm.ogg` |
| 风格 | 由实现者挑选,适合台球/Lounge 氛围、可无缝循环 |
| 播放时机 | **仅封面菜单**(进入对局/暂停不播) |
| 静音联动 | M 键静音时,背景音乐与音效**一起**静(共用一个开关) |

## 技术方案:`pygame.mixer.music`,与音效分开

pygame 标准做法:短音效用 `mixer.Sound`(现状),长背景音乐用 `mixer.music`(流式、原生支持循环 `loops=-1`)。两者独立通道,互不影响。**不改现有 4 个音效逻辑。**

## 范围

| 部分 | 内容 | 主要文件 |
|------|------|---------|
| 1 | 获取并放入 `sounds/bgm.ogg`(免版权) | `sounds/` |
| 2 | `SoundManager` 加 BGM 加载/播放/停止/静音联动 | `sounds.py` |
| 3 | `main()` 场景切换处控制 BGM 起停 + M 键联动 | `billiar_ball.py` |
| 4 | 测试:接口存在 + 无文件时优雅降级 + 静音联动 | `tests/test_sounds_bgm.py` |

## 第 1 部分:音乐文件

- 下载一首 CC0/公共领域、适合氛围、可循环的曲子,存为 `sounds/bgm.ogg`。
- 优先 `.ogg`(pygame 兼容稳、体积小)。
- 下载后用 `pygame.mixer.music.load` 验证可加载。
- commit message 注明素材来源与许可。

## 第 2 部分:`SoundManager`(`sounds.py`)

新增字段与方法,职责单一(音乐归 SoundManager 管):

```python
_BGM_PATH = os.path.join(_SOUND_DIR, 'bgm.ogg')

class SoundManager:
    def __init__(self):
        ...                      # 现有音效加载不变
        self._bgm_loaded = False
        self._bgm_should_play = False   # 逻辑上"现在是否应播 BGM"(用于静音恢复)
        if os.path.exists(_BGM_PATH):
            try:
                pygame.mixer.music.load(_BGM_PATH)
                self._bgm_loaded = True
            except pygame.error:
                self._bgm_loaded = False

    def play_bgm(self):
        """开始循环播放背景音乐。无文件则无操作(优雅降级)。"""
        self._bgm_should_play = True
        if not self._bgm_loaded:
            return
        pygame.mixer.music.play(loops=-1)
        if self.muted:
            pygame.mixer.music.pause()

    def stop_bgm(self):
        """停止背景音乐。"""
        self._bgm_should_play = False
        if not self._bgm_loaded:
            return
        pygame.mixer.music.stop()

    def set_muted(self, muted):
        """切换静音;背景音乐随之暂停/恢复(仅当逻辑上应播时)。"""
        self.muted = muted
        if not self._bgm_loaded:
            return
        if muted:
            pygame.mixer.music.pause()
        elif self._bgm_should_play:
            pygame.mixer.music.unpause()
```

- `_bgm_should_play`:记录"逻辑上现在该不该播"(在封面=True,进对局=False)。静音恢复时据此决定要不要 unpause——避免在对局中按 M 解除静音却把已 stop 的音乐 unpause。
- `play_bgm`/`stop_bgm`/`set_muted` 在 `_bgm_loaded=False` 时都安全无操作。

> 现有代码直接写 `sound.muted = not sound.muted`。改为调用 `set_muted(...)` 以触发联动。

## 第 3 部分:`main()` 控制(`billiar_ball.py`)

### 进入封面时播、进对局时停

`main()` 的事件循环里,场景从 `menu` → `game`(点模式按钮)处加 `sound.stop_bgm()`;从 `game` → `menu`(暂停菜单"退出")处加 `sound.play_bgm()`。

启动时初始在 `menu` 场景:`main()` 开头创建 `SoundManager` 后调用一次 `sound.play_bgm()`。

### M 键联动

现有:
```python
if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
    sound.muted = not sound.muted
```
改为:
```python
if ev.type == pygame.KEYDOWN and ev.key == pygame.K_m:
    sound.set_muted(not sound.muted)
```

> 对局内也能按 M,此时 `_bgm_should_play=False`,`set_muted` 只切 `muted` 标志、不会误恢复音乐。音效静音行为不变。

## 第 4 部分:测试(`tests/test_sounds_bgm.py`)

`mixer.music` 是 pygame 全局单例、依赖音频后端,真实播放不单测(同现有 Sound 音效)。只测本层接口契约与降级:

- **接口存在**:`SoundManager` 有 `play_bgm`/`stop_bgm`/`set_muted` 方法。
- **无文件优雅降级**:当 `bgm.ogg` 不存在(或 `_bgm_loaded=False`)时,`play_bgm()`/`stop_bgm()`/`set_muted(True/False)` 均不抛异常。
- **should_play 状态机**:`play_bgm()` 后 `_bgm_should_play is True`;`stop_bgm()` 后 `False`。
- **静音联动标志**:`set_muted(True)` 后 `muted is True`;`set_muted(False)` 后 `muted is False`。

测试用 SDL dummy 音频驱动(`SDL_AUDIODRIVER=dummy`),避免依赖真实声卡;并通过临时把 `_bgm_loaded` 置 False 来测降级路径,避免对真实音频设备的依赖。

## 不做(超出范围)

- 不做音量滑条(只要 BGM 开关,跟随 M)。
- 对局/暂停不播 BGM(用户选仅封面)。
- 不做多首随机/切歌。
- 不改现有 4 个音效的加载与播放逻辑。
