"""Game._fire 的杆法符号契约回归测试。需要 pygame,用 SDL dummy 驱动以免依赖真实显示。"""
import os

import pygame
import pytest

from balls import find_cue


@pytest.fixture(scope="module")
def game_module():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1000, 600))
    import billiar_ball
    yield billiar_ball
    pygame.quit()


def _fire_with_english(game_module, english):
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    g.english = english
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    return g


def test_fire_maps_dot_up_to_follow(game_module):
    # 红点偏上 dy<0 → 跟杆 spin_v>0
    g = _fire_with_english(game_module, (0.0, -1.0))
    cue = find_cue(g.balls)
    assert cue.spin_v == 1.0
    assert cue.spin_s == 0.0


def test_fire_maps_dot_down_to_draw(game_module):
    # 红点偏下 dy>0 → 缩杆 spin_v<0
    g = _fire_with_english(game_module, (0.0, 1.0))
    cue = find_cue(g.balls)
    assert cue.spin_v == -1.0


def test_fire_maps_dot_right_to_right_english(game_module):
    # 红点偏右 dx>0 → 右塞 spin_s>0
    g = _fire_with_english(game_module, (1.0, 0.0))
    cue = find_cue(g.balls)
    assert cue.spin_s == 1.0
    assert cue.spin_v == 0.0


def test_fire_general_offset_signs(game_module):
    # 右上：spin_v=-dy=0.5（跟），spin_s=dx=0.5（右）
    g = _fire_with_english(game_module, (0.5, -0.5))
    cue = find_cue(g.balls)
    assert cue.spin_v == 0.5
    assert cue.spin_s == 0.5


def test_fire_resets_spin_ui_state(game_module):
    g = _fire_with_english(game_module, (0.5, -0.5))
    assert g.english == (0.0, 0.0)
    assert g.spin_panel_open is False
    assert g.dragging_spin is False
