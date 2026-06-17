from physics import Event, EVENT_POCKETED, EVENT_BALL_HIT, EVENT_CUSHION
from rules import evaluate_shot, is_legal_first_contact, snooker_balls_on
from rules import evaluate_snooker_shot, is_snookered
from table import Table
from balls import Ball
import config


def hit(a, b):
    return Event(EVENT_BALL_HIT, {'a': a, 'b': b})


def pocket(n, idx=0):
    return Event(EVENT_POCKETED, {'number': n, 'pocket': idx})


def cushion(n):
    return Event(EVENT_CUSHION, {'number': n})


def test_legal_break_no_foul_no_assignment():
    events = [hit(0, 5), cushion(5), cushion(3)]
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is False
    assert r.assigned_group is None
    assert r.continue_turn is False
    assert r.winner_is_shooter is None


def test_cue_scratch_is_foul():
    events = [hit(0, 1), pocket(0, 5)]
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is True
    assert r.cue_pocketed is True


def test_no_contact_is_foul():
    events = [cushion(0)]
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is True
    assert '未碰' in r.foul_reason


def test_no_rail_no_pocket_is_foul():
    events = [hit(0, 2)]   # 碰到球但既没进球也没有球碰库
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is True


def test_cushion_before_contact_is_still_no_rail_foul():
    # 母球先碰库再撞上球后停下：碰库发生在接触之前，仍算空杆
    events = [cushion(0), hit(0, 2)]
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is True
    assert '空杆' in r.foul_reason


def test_cushion_after_contact_is_legal():
    # 撞球后有球碰库：合法，不算空杆
    events = [hit(0, 2), cushion(0)]
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is False


def test_open_table_legal_pocket_assigns_group_and_continues():
    events = [hit(0, 3), pocket(3), cushion(5)]
    r = evaluate_shot(events, open_table=True, shooter_group=None, shooter_on_eight=False)
    assert r.foul is False
    assert r.assigned_group == 'solid'
    assert r.continue_turn is True


def test_hitting_opponent_group_first_is_foul():
    # 我是 solid，先碰到花色 9 号
    events = [hit(0, 9), cushion(9)]
    r = evaluate_shot(events, open_table=False, shooter_group='solid', shooter_on_eight=False)
    assert r.foul is True


def test_pocket_own_group_continues():
    events = [hit(0, 2), pocket(2)]
    r = evaluate_shot(events, open_table=False, shooter_group='solid', shooter_on_eight=False)
    assert r.foul is False
    assert r.continue_turn is True


def test_pocket_eight_when_on_eight_wins():
    events = [hit(0, 8), pocket(8)]
    r = evaluate_shot(events, open_table=False, shooter_group='solid', shooter_on_eight=True)
    assert r.winner_is_shooter is True


def test_pocket_eight_early_loses():
    events = [hit(0, 8), pocket(8)]
    r = evaluate_shot(events, open_table=False, shooter_group='solid', shooter_on_eight=False)
    assert r.winner_is_shooter is False


def test_pocket_eight_with_scratch_loses():
    events = [hit(0, 8), pocket(8), pocket(0, 4)]
    r = evaluate_shot(events, open_table=False, shooter_group='solid', shooter_on_eight=True)
    assert r.winner_is_shooter is False


# ---- 合法首球判定（瞄准时鬼球禁止样式用） ----

def test_legal_first_open_table_non_eight_is_legal():
    assert is_legal_first_contact(3, open_table=True, shooter_group=None, shooter_on_eight=False) is True
    assert is_legal_first_contact(11, open_table=True, shooter_group=None, shooter_on_eight=False) is True


def test_legal_first_open_table_eight_is_illegal():
    assert is_legal_first_contact(8, open_table=True, shooter_group=None, shooter_on_eight=False) is False


def test_legal_first_assigned_own_group_legal_opponent_illegal():
    # 我是 solid：碰 solid 合法，碰 stripe / 8 非法
    assert is_legal_first_contact(2, open_table=False, shooter_group='solid', shooter_on_eight=False) is True
    assert is_legal_first_contact(9, open_table=False, shooter_group='solid', shooter_on_eight=False) is False
    assert is_legal_first_contact(8, open_table=False, shooter_group='solid', shooter_on_eight=False) is False


def test_legal_first_on_eight_only_eight_legal():
    assert is_legal_first_contact(8, open_table=False, shooter_group='solid', shooter_on_eight=True) is True
    assert is_legal_first_contact(2, open_table=False, shooter_group='solid', shooter_on_eight=True) is False


def _snooker_balls(reds=range(1, 16), colors=range(16, 22), cue=True):
    out = []
    if cue:
        out.append(Ball(number=0, x=0, y=0))
    for n in reds:
        out.append(Ball(number=n, x=0, y=0))
    for n in colors:
        out.append(Ball(number=n, x=0, y=0))
    return out


def test_balls_on_red_phase_is_all_reds():
    balls = _snooker_balls()
    assert snooker_balls_on('red', None, balls) == set(range(1, 16))


def test_balls_on_named_color_is_single():
    balls = _snooker_balls()
    assert snooker_balls_on('color', 19, balls) == {19}


def test_balls_on_free_choice_color_is_all_colors_on_table():
    # 红球已清空、next_color=None(自选彩球阶段),只剩黄绿在台
    balls = _snooker_balls(reds=[], colors=[16, 17])
    assert snooker_balls_on('color', None, balls) == {16, 17}


def _table():
    return Table(0, 0, 1000, 500)


def test_red_phase_potting_color_is_foul():
    # 红球阶段,母球先碰红球(合法首碰)但把蓝球(19)打进 → 犯规,不得分
    balls = _snooker_balls()
    events = [hit(0, 3), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert pts == 0
    # 误进蓝球(5分),罚分取 max(4, 蓝5) = 5
    assert foul_pts == 5


def test_red_phase_potting_red_scores_one():
    balls = _snooker_balls()
    events = [hit(0, 3), pocket(3, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is False
    assert pts == 1
    assert phase == 'color'      # 打进红球后转打彩球
    assert nc is None            # 自选彩球


def test_foul_wrong_first_contact_black_penalty_seven():
    # 红球阶段,母球先碰黑球(21) → 犯规,罚 7
    balls = _snooker_balls()
    events = [hit(0, 21)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert foul_pts == 7


def test_foul_air_shot_min_penalty_four():
    # 空杆:母球没碰任何球 → 罚 4
    balls = _snooker_balls()
    events = [cushion(0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert foul_pts == 4


def test_red_phase_miss_keeps_red_phase():
    # 红球阶段碰红球但没进、有碰库 → 不犯规,仍是红球阶段
    balls = _snooker_balls()
    events = [hit(0, 3), cushion(3)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is False
    assert phase == 'red'
    assert nc is None


def test_color_order_yellow_then_green():
    # 清彩阶段:打进黄(16),下一颗应是绿(17)
    balls = _snooker_balls(reds=[], colors=[16, 17, 18, 19, 20, 21])
    for b in balls:
        if b.number == 16:
            b.on_table = False
    events = [hit(0, 16), pocket(16, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', 16, _table())
    assert result.foul is False
    assert pts == 2
    assert phase == 'color'
    assert nc == 17


def test_color_phase_no_respot_in_color_order():
    # 清彩阶段进的彩球不复位
    balls = _snooker_balls(reds=[], colors=[16, 17, 18, 19, 20, 21])
    for b in balls:
        if b.number == 16:
            b.on_table = False
    events = [hit(0, 16), pocket(16, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', 16, _table())
    assert respot == []


def test_red_phase_color_respots():
    # 红彩交替:自选彩球阶段打进蓝球,蓝球复位,还有红球 → 回到打红球
    balls = _snooker_balls()
    events = [hit(0, 19), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', None, _table())
    assert result.foul is False
    assert pts == 5
    assert respot == [19]
    assert phase == 'red'


def test_red_phase_foul_color_pot_respots():
    # 红球阶段误把蓝球打进 → 犯规,该彩球必须复位
    balls = _snooker_balls()
    events = [hit(0, 3), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table())
    assert result.foul is True
    assert respot == [19]


def test_last_red_free_color_then_ascending_sequence():
    # 红球已清完,自选彩球槽打进蓝球(19,已离台) → 进入升序,从黄(16)开始
    balls = _snooker_balls(reds=[], colors=[16, 17, 18, 20, 21])
    events = [hit(0, 19), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'color', None, _table())
    assert result.foul is False
    assert pts == 5
    assert respot == [19]
    assert phase == 'color'
    assert nc == 16


def _ball(n, x, y):
    return Ball(number=n, x=x, y=y)


def test_not_snookered_clear_path():
    # 母球在左,目标红球在右,中间无阻挡 → 没被障碍
    cue = _ball(0, 100, 250)
    target = _ball(1, 500, 250)
    balls = [cue, target]
    assert is_snookered(cue, {1}, balls) is False


def test_snookered_blocker_directly_between():
    # 母球与目标球同一水平线,正中间放一颗彩球完全挡住两侧切线 → 被障碍
    cue = _ball(0, 100, 250)
    target = _ball(1, 500, 250)
    r = config.BALL_RADIUS
    blocker = _ball(20, 300, 250)
    balls = [cue, target, blocker]
    assert is_snookered(cue, {1}, balls) is True


def test_not_snookered_if_any_ball_on_reachable():
    # 两颗 ball-on:一颗被挡、一颗通路清晰 → 不算被障碍
    cue = _ball(0, 100, 250)
    blocked = _ball(1, 500, 250)
    blocker = _ball(20, 300, 250)
    clear = _ball(2, 100, 450)   # 母球正下方,通路清晰
    balls = [cue, blocked, blocker, clear]
    assert is_snookered(cue, {1, 2}, balls) is False


def test_snookered_narrow_gap_too_tight_for_cue():
    # 目标球两侧各有一颗阻挡球,垂直间距 ~3.4R(落在 3R~4R 带内):
    # 真实母球(半径R)无法从任一侧的缝隙穿过 → 应判被障碍。
    # 此用例区分切线偏移 R(错误,会判没障碍) 与 2R(正确,判被障碍)。
    r = config.BALL_RADIUS
    d = int(3.4 * r)                       # 37 (在 3R=33 与 4R=44 之间)
    cue = _ball(0, 100, 250)
    target = _ball(1, 500, 250)
    block_a = _ball(20, 500, 250 + d)
    block_b = _ball(19, 500, 250 - d)
    balls = [cue, target, block_a, block_b]
    assert is_snookered(cue, {1}, balls) is True


def test_free_ball_pot_color_scores_ball_on_value():
    # 自由球 + 红球阶段:把蓝球(19)当红球打进 → 得 1 分,蓝球复位,转打彩球
    balls = _snooker_balls()
    events = [hit(0, 19), pocket(19, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table(), free_ball=True)
    assert result.foul is False
    assert pts == 1
    assert respot == [19]
    assert phase == 'color'


def test_free_ball_any_first_contact_legal():
    # 自由球 + 红球阶段:首碰彩球(本应犯规)→ 不犯规
    balls = _snooker_balls()
    events = [hit(0, 20), cushion(20)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table(), free_ball=True)
    assert result.foul is False


def test_free_ball_cue_potted_still_foul():
    # 自由球不豁免母球落袋
    balls = _snooker_balls()
    events = [hit(0, 19), pocket(0, 0)]
    result, pts, foul_pts, respot, phase, nc = evaluate_snooker_shot(
        events, balls, 'red', None, _table(), free_ball=True)
    assert result.foul is True
