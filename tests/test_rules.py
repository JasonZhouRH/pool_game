from physics import Event, EVENT_POCKETED, EVENT_BALL_HIT, EVENT_CUSHION
from rules import evaluate_shot


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
