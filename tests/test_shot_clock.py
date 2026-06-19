"""出杆计时器（射钟）纯逻辑测试。

仅 8 球 / 9 球生效，斯诺克不计时。计时帧驱动（与 _gameover_frame 同款），
不依赖真实墙钟，故可单测。需要 pygame（Game 构造依赖），用 SDL dummy 驱动。
"""
import os

import pygame
import pytest

import config
from balls import find_cue


@pytest.fixture(scope="module")
def game_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1000, 600))
    import billiar_ball
    yield billiar_ball
    pygame.quit()


# ---- 初始化 ----

def test_reset_initializes_full_clock_eight(game_module):
    g = game_module.Game()
    assert g._shot_clock == config.SHOT_CLOCK_FRAMES


def test_reset_initializes_full_clock_nine(game_module):
    g = game_module.Game(mode='nine')
    assert g._shot_clock == config.SHOT_CLOCK_FRAMES


def test_fire_resets_clock_to_full(game_module):
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    g._shot_clock = 5            # 消耗到所剩无几
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g._shot_clock == config.SHOT_CLOCK_FRAMES


# ---- 倒计时 ----

def test_update_decrements_clock_in_aiming_eight(game_module):
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    g._shot_clock = 100
    g.update()
    assert g._shot_clock == 99


def test_update_decrements_clock_in_aiming_nine(game_module):
    g = game_module.Game(mode='nine')
    g.state = game_module.STATE_AIMING
    g._shot_clock = 100
    g.update()
    assert g._shot_clock == 99


def test_snooker_clock_does_not_decrement(game_module):
    g = game_module.Game(mode='snooker')
    g.state = game_module.STATE_AIMING
    g._shot_clock = 100
    g.update()
    assert g._shot_clock == 100   # 斯诺克不计时


def test_clock_frozen_while_placing_ball(game_module):
    # 摆球状态(BREAK_PLACE/BALL_IN_HAND)冻结，不倒计时
    g = game_module.Game()
    g.state = game_module.STATE_BALL_IN_HAND
    g._shot_clock = 100
    g.update()
    assert g._shot_clock == 100


def test_clock_frozen_while_moving(game_module):
    # 球运动期间不倒计时(MOVING)；此处不放运动球，仅验证时钟不动
    g = game_module.Game()
    g.state = game_module.STATE_MOVING
    g._shot_clock = 100
    g.update()
    assert g._shot_clock == 100


# ---- 超时处罚：换手 + 对手自由球 ----

def test_timeout_switches_player_and_grants_ball_in_hand(game_module):
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    g.current = 0
    g._shot_clock = 1            # 本帧将归零
    g.update()
    assert g.current == 1                                  # 换手
    assert g.state == game_module.STATE_BALL_IN_HAND       # 对手自由球
    assert g.place_mode == 'free'
    assert g._shot_clock == config.SHOT_CLOCK_FRAMES       # 新一杆满血


def test_timeout_does_not_move_cue_ball(game_module):
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    cue = find_cue(g.balls)
    cue.x, cue.y = 333.0, 222.0
    g._shot_clock = 1
    g.update()
    assert (cue.x, cue.y) == (333.0, 222.0)   # 仅交控制权，白球不动


def test_no_timeout_while_clock_positive(game_module):
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    g.current = 0
    g._shot_clock = 2
    g.update()
    assert g._shot_clock == 1
    assert g.current == 0                      # 未超时，不换手
    assert g.state == game_module.STATE_AIMING
