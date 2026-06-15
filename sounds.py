"""音效模块：加载 sounds/ 目录下的 WAV 文件。"""
import os

import pygame

_SOUND_DIR = os.path.join(os.path.dirname(__file__), 'sounds')


def _load(name):
    """加载 sounds/<name>.wav，返回 pygame.mixer.Sound。"""
    path = os.path.join(_SOUND_DIR, f'{name}.wav')
    if not os.path.exists(path):
        return None
    return pygame.mixer.Sound(path)


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