"""射钟 HUD 显示的纯逻辑 + 冒烟测试。

帧→剩余秒数与预警色判定是纯逻辑，单测；实际 blit 依赖 surface，仅冒烟（不抛异常）。
"""
import os

import pygame
import pytest

import config


@pytest.fixture(scope="module")
def _pygame_display():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1000, 600))
    yield
    pygame.quit()


def test_display_seconds_ceil_full_clock():
    import renderer
    # 满帧 → 显示满秒数
    secs, warn = renderer.shot_clock_display(config.SHOT_CLOCK_FRAMES)
    assert secs == config.SHOT_CLOCK_SECONDS
    assert warn is False


def test_display_seconds_round_up():
    import renderer
    # 不足 1 秒的余帧向上取整：1 帧也显示为 1 秒，避免提前显示 0
    secs, _ = renderer.shot_clock_display(1)
    assert secs == 1


def test_display_zero_frames_is_zero():
    import renderer
    secs, _ = renderer.shot_clock_display(0)
    assert secs == 0


def test_display_warns_below_threshold():
    import renderer
    warn_frames = config.SHOT_CLOCK_WARN_SECONDS * config.FPS
    _, warn_at = renderer.shot_clock_display(warn_frames)
    assert warn_at is False                     # 恰好等于阈值秒数不预警
    _, warn_below = renderer.shot_clock_display(warn_frames - 1)
    assert warn_below is True                   # 低于阈值预警


def test_draw_shot_clock_smoke(_pygame_display):
    import renderer
    screen = pygame.display.get_surface()
    font = pygame.font.SysFont('arial', 18)
    # 不抛异常即可（正常色与预警色两条路径）
    renderer.draw_shot_clock(screen, font, config.SHOT_CLOCK_FRAMES)
    renderer.draw_shot_clock(screen, font, 1)
