from physics import Event, EVENT_POCKETED, EVENT_BALL_HIT, EVENT_CUSHION
from rules import evaluate_shot, is_legal_first_contact, snooker_balls_on
from balls import Ball


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
