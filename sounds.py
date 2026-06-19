"""音效模块：加载 sounds/ 目录下的音效与背景音乐。"""
import os

import pygame

_SOUND_DIR = os.path.join(os.path.dirname(__file__), 'sounds')

# 背景音乐候选文件（按顺序取第一个存在的；ogg 优先，回退 mp3）
_BGM_CANDIDATES = ['bgm.ogg', 'bgm.mp3']


def _load(name, exts=('wav',)):
    """加载 sounds/<name>.<ext>（按 exts 顺序取第一个存在的），返回 Sound 或 None。"""
    for ext in exts:
        path = os.path.join(_SOUND_DIR, f'{name}.{ext}')
        if os.path.exists(path):
            return pygame.mixer.Sound(path)
    return None


def _find_bgm():
    """返回第一个存在的背景音乐文件路径，都不存在则 None。"""
    for name in _BGM_CANDIDATES:
        path = os.path.join(_SOUND_DIR, name)
        if os.path.exists(path):
            return path
    return None


class SoundManager:
    """管理并播放台球音效。"""

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.muted = False
        self._cue_hit = _load('cue_hit')
        self._ball_hit = _load('ball_hit')
        self._pocket = _load('pocket')
        self._btn_click = _load('btn_click')
        self._win = _load('win', exts=('ogg', 'wav'))   # 获胜音效（ogg 优先）

        # 背景音乐：用 pygame.mixer.music（流式、原生循环），与上面的 Sound 音效分开
        self._bgm_loaded = False
        self._bgm_should_play = False   # 逻辑上"现在是否应播 BGM"，用于静音恢复判断
        bgm_path = _find_bgm()
        if bgm_path is not None:
            try:
                pygame.mixer.music.load(bgm_path)
                self._bgm_loaded = True
            except pygame.error:
                self._bgm_loaded = False

    def play_cue_hit(self):
        if self._cue_hit and not self.muted:
            self._cue_hit.play()

    def play_ball_hit(self):
        if self._ball_hit and not self.muted:
            self._ball_hit.play()

    def play_pocket(self):
        if self._pocket and not self.muted:
            self._pocket.play()

    def play_btn_click(self):
        if self._btn_click and not self.muted:
            self._btn_click.play()

    def play_win(self):
        if self._win and not self.muted:
            self._win.play()

    def play_bgm(self):
        """开始循环播放背景音乐。无文件则仅置标志（优雅降级）。"""
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
        """切换静音；背景音乐随之暂停/恢复（仅当逻辑上应播时才恢复）。"""
        self.muted = muted
        if not self._bgm_loaded:
            return
        if muted:
            pygame.mixer.music.pause()
        elif self._bgm_should_play:
            pygame.mixer.music.unpause()