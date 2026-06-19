"""射钟音效触发时机:最后10秒每秒滴答一次、超时一声。用 spy 验证触发,不发真声。

帧驱动:剩余秒边界(_shot_clock 是 FPS 的整数倍且 ≤10s)各触发一次 play_tick;
归零触发 play_timeout。同一秒内多帧不重复,>10s 不触发,斯诺克不触发。
"""
import os

import pygame
import pytest

import config


@pytest.fixture(scope="module")
def game_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1000, 600))
    import billiar_ball
    yield billiar_ball
    pygame.quit()


class _SpySound:
    """记录 tick/timeout 调用次数的假音效管理器。"""
    def __init__(self):
        self.muted = False
        self.tick_calls = 0
        self.timeout_calls = 0

    def play_tick(self): self.tick_calls += 1
    def play_timeout(self): self.timeout_calls += 1
    # Game 可能用到的其它方法,空实现
    def play_cue_hit(self): pass
    def play_ball_hit(self): pass
    def play_pocket(self): pass
    def play_btn_click(self): pass
    def play_win(self): pass
    def play_bgm(self): pass
    def stop_bgm(self): pass
    def set_muted(self, m): self.muted = m


def _aiming_game(game_module, mode='eight'):
    g = game_module.Game(mode=mode, sound=_SpySound())
    g.state = game_module.STATE_AIMING
    return g


def test_tick_at_ten_second_boundary(game_module):
    # 剩余正好 11 秒整 → update 后变 10s 边界,响一声滴答
    g = _aiming_game(game_module)
    g._shot_clock = 10 * config.FPS + 1
    g.update()
    assert g._shot_clock == 10 * config.FPS
    assert g.sound.tick_calls == 1


def test_no_tick_above_ten_seconds(game_module):
    # 剩余 11 秒边界(>10s)不响
    g = _aiming_game(game_module)
    g._shot_clock = 11 * config.FPS + 1
    g.update()
    assert g.sound.tick_calls == 0


def test_no_tick_mid_second(game_module):
    # 非秒边界帧不响
    g = _aiming_game(game_module)
    g._shot_clock = 5 * config.FPS - 13   # 落在某秒中间
    g.update()
    assert g.sound.tick_calls == 0


def test_one_tick_per_second_not_per_frame(game_module):
    # 从 10s 边界连跑一整秒(FPS 帧),只应响 1 次(下一秒边界)
    g = _aiming_game(game_module)
    g._shot_clock = 10 * config.FPS
    for _ in range(config.FPS):
        g.update()
    assert g._shot_clock == 9 * config.FPS
    assert g.sound.tick_calls == 1     # 仅 9s 边界这一声


def test_ten_ticks_total_over_last_ten_seconds(game_module):
    # 从刚好高于 10s 边界一帧跑到归零:10,9,...,1 秒各一声 = 10 声,且超时响一次
    g = _aiming_game(game_module)
    g._shot_clock = 10 * config.FPS + 1
    for _ in range(10 * config.FPS + 1):
        g.update()
    assert g._shot_clock == config.SHOT_CLOCK_FRAMES   # 超时已重置满血
    assert g.sound.tick_calls == 10
    assert g.sound.timeout_calls == 1


def test_timeout_plays_timeout_sound(game_module):
    g = _aiming_game(game_module)
    g._shot_clock = 1
    g.update()
    assert g.sound.timeout_calls == 1


def test_timeout_frame_does_not_also_tick(game_module):
    # 归零那一帧(_shot_clock→0)只响超时,不响滴答(0 不算秒边界)
    g = _aiming_game(game_module)
    g._shot_clock = 1
    g.update()
    assert g.sound.tick_calls == 0
    assert g.sound.timeout_calls == 1


def test_snooker_no_tick(game_module):
    g = _aiming_game(game_module, mode='snooker')
    g._shot_clock = 10 * config.FPS + 1
    g.update()
    assert g.sound.tick_calls == 0


def test_no_tick_when_not_aiming(game_module):
    g = _aiming_game(game_module)
    g.state = game_module.STATE_BALL_IN_HAND
    g._shot_clock = 10 * config.FPS + 1
    g.update()
    assert g.sound.tick_calls == 0
