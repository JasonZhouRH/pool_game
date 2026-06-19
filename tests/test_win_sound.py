"""获胜音效:SoundManager.play_win 接口/降级 + Game 进入 GAMEOVER 时恰好播一次。

真实音频不单测;用一个记录调用次数的假 SoundManager 验证触发时机,
确保只在"刚进入 GAMEOVER"那一刻播一次,不漏不重。
"""
import os

import pygame
import pytest

from physics import Event, EVENT_POCKETED, EVENT_BALL_HIT


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
    """记录 play_win 调用次数的假音效管理器。"""
    def __init__(self):
        self.muted = False
        self.win_calls = 0

    def play_win(self):
        self.win_calls += 1

    # Game 可能调用到的其它音效方法,空实现即可
    def play_cue_hit(self): pass
    def play_ball_hit(self): pass
    def play_pocket(self): pass
    def play_btn_click(self): pass
    def play_bgm(self): pass
    def stop_bgm(self): pass
    def set_muted(self, m): self.muted = m


def test_soundmanager_has_play_win(game_module):
    import sounds
    sm = sounds.SoundManager()
    assert hasattr(sm, 'play_win')


def test_play_win_graceful_when_missing(game_module):
    # 即使没有 win 音效文件,play_win 也不应抛异常
    import sounds
    sm = sounds.SoundManager()
    sm._win = None
    sm.play_win()   # 不抛异常即通过


def test_win_sound_plays_once_on_gameover(game_module):
    # 8 球:合法打进 8 号获胜 → 进入 GAMEOVER,update() 应触发一次 play_win
    g = game_module.Game(sound=_SpySound())
    g.player_groups = [g.player_groups[0], g.player_groups[1]]
    g.current = 0
    g.player_groups[0] = 'solid'
    g.player_groups[1] = 'stripe'
    # 让玩家1只剩 8 号没进(其余全色已清),本杆打进 8 号 → 胜
    for b in g.balls:
        if 1 <= b.number <= 7:
            b.on_table = False
    g.shot_on_eight = True
    eight = next(b for b in g.balls if b.number == 8)
    eight.on_table = False
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 8}),
                     Event(EVENT_POCKETED, {'number': 8, 'pocket': 0})]
    g.state = game_module.STATE_MOVING
    g.resolve_shot()
    assert g.state == game_module.STATE_GAMEOVER   # 前置:确实获胜了
    # 进入 GAMEOVER 后调用 update(),应播一次获胜音效
    g.update()
    assert g.sound.win_calls == 1
    # 再 update 几次,不应重复播
    g.update()
    g.update()
    assert g.sound.win_calls == 1


def test_no_win_sound_during_normal_play(game_module):
    # 普通进行中(非 GAMEOVER)update() 不应触发获胜音效
    g = game_module.Game(sound=_SpySound())
    g.state = game_module.STATE_AIMING
    g.update()
    assert g.sound.win_calls == 0


def test_gameover_frame_counts_up(game_module):
    # 进入 GAMEOVER 后:首帧归零,之后每次 update() 递增
    g = game_module.Game(sound=_SpySound())
    g.state = game_module.STATE_GAMEOVER
    g.update()                       # 首帧:播音效 + 帧=0
    assert g._gameover_frame == 0
    g.update()
    assert g._gameover_frame == 1
    g.update()
    assert g._gameover_frame == 2


def test_reset_zeroes_gameover_frame(game_module):
    g = game_module.Game(sound=_SpySound())
    g._gameover_frame = 99
    g.reset()
    assert g._gameover_frame == 0
