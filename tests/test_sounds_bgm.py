"""背景音乐(BGM)的接口契约与优雅降级测试。

真实音频播放依赖音频后端、不单测(同现有 Sound 音效);这里只测 SoundManager
这层的接口存在、_bgm_should_play 状态机、静音联动标志,以及无文件时不抛异常。
用 SDL dummy 音频驱动,避免依赖真实声卡。
"""
import os

import pygame
import pytest


@pytest.fixture(scope="module")
def sound_mod():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    import sounds
    yield sounds
    pygame.quit()


def _muted_manager(sound_mod):
    """构造一个 SoundManager,强制当作"无 BGM 文件"以测降级路径,与真实音频设备解耦。"""
    sm = sound_mod.SoundManager()
    sm._bgm_loaded = False
    return sm


def test_soundmanager_has_bgm_interface(sound_mod):
    sm = sound_mod.SoundManager()
    assert hasattr(sm, 'play_bgm')
    assert hasattr(sm, 'stop_bgm')
    assert hasattr(sm, 'set_muted')


def test_play_bgm_sets_should_play(sound_mod):
    sm = _muted_manager(sound_mod)
    sm.play_bgm()
    assert sm._bgm_should_play is True


def test_stop_bgm_clears_should_play(sound_mod):
    sm = _muted_manager(sound_mod)
    sm.play_bgm()
    sm.stop_bgm()
    assert sm._bgm_should_play is False


def test_set_muted_toggles_flag(sound_mod):
    sm = _muted_manager(sound_mod)
    sm.set_muted(True)
    assert sm.muted is True
    sm.set_muted(False)
    assert sm.muted is False


def test_bgm_methods_graceful_without_file(sound_mod):
    # 无 BGM 文件时,所有 BGM 相关调用都不应抛异常
    sm = _muted_manager(sound_mod)
    sm.play_bgm()
    sm.set_muted(True)
    sm.set_muted(False)
    sm.stop_bgm()
    # 走到这里没抛异常即通过
    assert sm._bgm_loaded is False
