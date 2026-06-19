"""SoundManager 的滴答/超时音效接口测试。

真实音频不单测;验证方法存在、静音守卫、缺音效时优雅降级。
需要 pygame mixer(SoundManager 构造依赖),用 SDL dummy 音频驱动。
"""
import os

import pygame
import pytest


@pytest.fixture(scope="module")
def _pygame_audio():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    yield
    pygame.quit()


def test_soundmanager_has_play_tick(_pygame_audio):
    import sounds
    sm = sounds.SoundManager()
    assert hasattr(sm, 'play_tick')


def test_soundmanager_has_play_timeout(_pygame_audio):
    import sounds
    sm = sounds.SoundManager()
    assert hasattr(sm, 'play_timeout')


def test_play_tick_graceful_when_missing(_pygame_audio):
    # 合成失败导致 _tick=None 时,play_tick 不应抛异常
    import sounds
    sm = sounds.SoundManager()
    sm._tick = None
    sm.play_tick()   # 不抛即通过


def test_play_timeout_graceful_when_missing(_pygame_audio):
    import sounds
    sm = sounds.SoundManager()
    sm._timeout = None
    sm.play_timeout()


def test_play_tick_silent_when_muted(_pygame_audio):
    # 静音时不实际播放:用假 Sound 记录 play 调用
    import sounds
    sm = sounds.SoundManager()

    class _FakeSound:
        def __init__(self): self.plays = 0
        def play(self): self.plays += 1

    fake = _FakeSound()
    sm._tick = fake
    sm.muted = True
    sm.play_tick()
    assert fake.plays == 0
    sm.muted = False
    sm.play_tick()
    assert fake.plays == 1
