"""进袋缩小动画(pocketing)的纯逻辑测试:快照的压入/推进/到点移除。

动画为纯视觉,绘制本身依赖 pygame surface 不单测;这里只测 Game 维护的
self.pocketing 列表行为。需要 pygame(Game 构造依赖),用 SDL dummy 驱动。
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


def test_reset_initializes_empty_pocketing(game_module):
    g = game_module.Game()
    assert g.pocketing == []


def test_reset_clears_existing_pocketing(game_module):
    g = game_module.Game()
    g.pocketing = [{'number': 3, 'x': 1.0, 'y': 2.0, 'frame': 5}]
    g.reset()
    assert g.pocketing == []


def test_advance_increments_frame(game_module):
    g = game_module.Game()
    g.pocketing = [{'number': 3, 'x': 1.0, 'y': 2.0, 'frame': 0}]
    g._advance_pocketing()
    assert g.pocketing[0]['frame'] == 1
    g._advance_pocketing()
    assert g.pocketing[0]['frame'] == 2


def test_advance_removes_at_end(game_module):
    g = game_module.Game()
    g.pocketing = [{'number': 3, 'x': 1.0, 'y': 2.0,
                    'frame': config.POCKET_ANIM_FRAMES - 1}]
    g._advance_pocketing()   # frame 达到 POCKET_ANIM_FRAMES → 移除
    assert g.pocketing == []


def test_multiple_balls_animate_independently(game_module):
    g = game_module.Game()
    g.pocketing = [
        {'number': 3, 'x': 1.0, 'y': 2.0, 'frame': 0},
        {'number': 5, 'x': 3.0, 'y': 4.0, 'frame': 10},
    ]
    g._advance_pocketing()
    frames = {p['number']: p['frame'] for p in g.pocketing}
    assert frames == {3: 1, 5: 11}


def test_animation_independent_of_ball_motion(game_module):
    # 即便没有球在运动(state 非 MOVING),update() 仍推进动画并最终清空,
    # 保证最后一颗球落袋、状态已切换后动画也能播完。
    g = game_module.Game()
    g.state = game_module.STATE_AIMING
    g.pocketing = [{'number': 3, 'x': 1.0, 'y': 2.0, 'frame': 0}]
    for _ in range(config.POCKET_ANIM_FRAMES):
        g.update()
    assert g.pocketing == []


def test_update_records_pocketed_ball_at_pocket_center(game_module):
    # 真实物理触发一次进袋:球落袋位置偏离袋心,但记录的应是袋口中心(动画在袋心缩小)。
    g = game_module.Game()
    # 仅留母球(resolve 需要)与 3 号球在台,其余移出,隔离副作用
    for b in g.balls:
        b.on_table = b.number in (0, 3)
    pocket = g.table.pocket_positions()[1]   # 上中袋,远离母球开球点
    three = next(b for b in g.balls if b.number == 3)
    # 放在袋口判定半径内、但明显偏离袋心(偏 10 像素),用来区分"落袋点"与"袋心"
    three.x, three.y = pocket[0] + 10.0, pocket[1] + 10.0
    three.vx, three.vy = 0.0, 0.0
    cue = find_cue(g.balls)
    cue.x, cue.y = g.table.head_spot()
    cue.vx, cue.vy = 0.0, 0.0
    g.state = game_module.STATE_MOVING
    g.update()
    recorded = [p for p in g.pocketing if p['number'] == 3]
    assert len(recorded) == 1
    p = recorded[0]
    assert p['frame'] == 1            # 压入(0)后本帧末尾 advance(+1)
    # 记录的是袋口中心,而非球的落袋位置
    assert (p['x'], p['y']) == (pocket[0], pocket[1])
