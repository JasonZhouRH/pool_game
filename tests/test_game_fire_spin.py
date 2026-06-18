"""Game._fire 的杆法符号契约回归测试。需要 pygame,用 SDL dummy 驱动以免依赖真实显示。"""
import os

import pygame
import pytest

from balls import find_cue
from balls import find_cue as _find_cue
from physics import Event, EVENT_POCKETED, EVENT_BALL_HIT


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


def _snooker_game(game_module):
    g = game_module.Game(mode='snooker')
    g.state = game_module.STATE_AIMING
    g.current = 0
    return g


def test_snooker_foul_cue_stays_when_not_potted(game_module):
    # 犯规但母球未落袋:对手原位接着打,不进摆球状态
    g = _snooker_game(game_module)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 333.0, 222.0
    # 红球阶段先碰黑球(21) → 犯规,母球未落袋
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 21})]
    g._was_ball_in_hand = False
    g.resolve_shot()
    assert g.current == 1                      # 换对手
    assert g.state == game_module.STATE_AIMING # 原位打,不摆球
    assert g.place_mode is None                # 无摆球特权
    assert (cue.x, cue.y) == (333.0, 222.0)    # 母球没动


def test_snooker_foul_cue_potted_goes_to_d(game_module):
    # 犯规且母球落袋:对手在 D 区摆球
    g = _snooker_game(game_module)
    g.shot_events = [Event(EVENT_POCKETED, {'number': 0, 'pocket': 0})]
    g._was_ball_in_hand = False
    g.resolve_shot()
    assert g.current == 1
    assert g.state == game_module.STATE_BREAK_PLACE
    assert g.place_mode == 'kitchen'


def test_free_ball_set_when_snookered_after_foul(game_module):
    # 对手犯规后,母球被一颗彩球完全挡住所有红球 → 判自由球
    g = _snooker_game(game_module)
    for b in g.balls:
        b.on_table = b.number in (0, 1, 20)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 100.0, 250.0
    red = next(b for b in g.balls if b.number == 1)
    red.x, red.y = 500.0, 250.0
    pink = next(b for b in g.balls if b.number == 20)
    pink.x, pink.y = 300.0, 250.0   # 正中间挡住
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 20})]
    g._was_ball_in_hand = False
    g.resolve_shot()
    assert g.free_ball is True


def test_free_ball_cleared_after_fire(game_module):
    g = _snooker_game(game_module)
    g.free_ball = True
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g.free_ball is False


def test_free_ball_scoring_end_to_end(game_module):
    # 自由球出杆后,把蓝球(19)当红球打进,应得 1 分(红球分值,非蓝5分)
    g = _snooker_game(game_module)
    g._snooker_phase = 'red'
    g._snooker_next_color = None
    g.current = 0
    g.free_ball = True
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()                       # 快照 _was_free_ball=True,清 free_ball
    assert g._was_free_ball is True
    before = g._snooker_scores[0]
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 19}),
                     Event(EVENT_POCKETED, {'number': 19, 'pocket': 0})]
    g.resolve_shot()
    assert g._snooker_scores[0] == before + 1


def test_stalemate_g_key_resets_frame(game_module):
    g = game_module.Game(mode='snooker')
    g.state = game_module.STATE_AIMING
    g._snooker_scores = [30, 20]
    g.scores = [2, 1]                      # 跨局胜场
    for b in g.balls[:5]:
        b.on_table = False
    ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g)
    g.handle_event(ev, (0, 0))
    assert g._snooker_scores == [0, 0]     # 本局分清零
    assert g.scores == [2, 1]              # 跨局胜场保留
    assert all(b.on_table for b in g.balls)  # 重新摆球


def test_reset_initializes_replay_fields(game_module):
    g = game_module.Game(mode='snooker')
    assert g._can_replay is False
    assert g._snooker_pre_shot is None


def test_fire_snapshots_balls_and_clears_replay(game_module):
    g = _snooker_game(game_module)
    g._can_replay = True            # 上一轮残留资格,出杆应清除
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g._can_replay is False
    assert g._snooker_pre_shot is not None
    assert g._snooker_pre_shot['current'] == g.current
    assert g._snooker_pre_shot['phase'] == g._snooker_phase
    assert len(g._snooker_pre_shot['balls']) == len(g.balls)


def test_fire_no_snapshot_in_eight_ball(game_module):
    g = game_module.Game()          # 8 球模式
    g.state = game_module.STATE_AIMING
    g.aim_dir = (1.0, 0.0)
    g.power = 0.5
    g._fire()
    assert g._snooker_pre_shot is None


def test_can_replay_when_opponent_misses_ball_on(game_module):
    # 红球阶段先碰黑球(21)=没碰红球(ball-on),母球未落袋且未被斯诺克 → 做斯诺克方可复位
    g = _snooker_game(game_module)
    g._snooker_phase = 'red'
    g._snooker_next_color = None
    # 只留母球与一颗红球且直线无遮挡,确保未触发自由球
    for b in g.balls:
        b.on_table = b.number in (0, 1)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 100.0, 250.0
    red = next(b for b in g.balls if b.number == 1)
    red.x, red.y = 500.0, 250.0
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 21})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g.free_ball is False
    assert g._can_replay is True


def test_cannot_replay_when_opponent_hits_ball_on(game_module):
    # 红球阶段先碰红球(7=ball-on)但空杆犯规 → 解到了,不可复位
    g = _snooker_game(game_module)
    g._snooker_phase = 'red'
    g._snooker_next_color = None
    # 只留母球与该红球且直线无遮挡,排除自由球干扰,确保因碰到 ball-on 而不可复位
    for b in g.balls:
        b.on_table = b.number in (0, 7)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 100.0, 250.0
    red = next(b for b in g.balls if b.number == 7)
    red.x, red.y = 500.0, 250.0
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 7})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g.free_ball is False
    assert g._can_replay is False


def test_cannot_replay_when_cue_potted(game_module):
    # 犯规且母球落袋 → 走 D 区,不可复位
    g = _snooker_game(game_module)
    g.shot_events = [Event(EVENT_POCKETED, {'number': 0, 'pocket': 0})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g._can_replay is False


def test_cannot_replay_when_free_ball_awarded(game_module):
    # 对手犯规且你被斯诺克拿到自由球 → 不可复位
    g = _snooker_game(game_module)
    for b in g.balls:
        b.on_table = b.number in (0, 1, 20)
    cue = _find_cue(g.balls)
    cue.x, cue.y = 100.0, 250.0
    red = next(b for b in g.balls if b.number == 1)
    red.x, red.y = 500.0, 250.0
    pink = next(b for b in g.balls if b.number == 20)
    pink.x, pink.y = 300.0, 250.0   # 挡住唯一红球
    g.shot_events = [Event(EVENT_BALL_HIT, {'a': 0, 'b': 20})]
    g._was_ball_in_hand = False
    g._was_free_ball = False
    g.resolve_shot()
    assert g.free_ball is True
    assert g._can_replay is False
