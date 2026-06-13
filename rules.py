"""8 球规则判定：消费 physics 事件，输出本杆结果。无 pygame 依赖。"""
from dataclasses import dataclass

from balls import group_of
from physics import EVENT_POCKETED, EVENT_BALL_HIT, EVENT_CUSHION


@dataclass
class ShotResult:
    pocketed: list            # 本杆落袋的目标球号（不含母球）
    cue_pocketed: bool
    foul: bool
    foul_reason: str
    continue_turn: bool
    assigned_group: str | None       # 'solid'/'stripe' 或 None
    winner_is_shooter: bool | None   # True=胜, False=负, None=继续


def _first_cue_contact(events):
    """返回 (首个被母球碰到的球号, 该事件在列表中的下标)；无接触则 (None, -1)。"""
    for i, e in enumerate(events):
        if e.type == EVENT_BALL_HIT and (e.data['a'] == 0 or e.data['b'] == 0):
            other = e.data['b'] if e.data['a'] == 0 else e.data['a']
            return other, i
    return None, -1


def evaluate_shot(events, open_table, shooter_group, shooter_on_eight):
    pocketed_all = [e.data['number'] for e in events if e.type == EVENT_POCKETED]
    cue_pocketed = 0 in pocketed_all
    object_pocketed = [n for n in pocketed_all if n != 0]
    eight_pocketed = 8 in pocketed_all
    first_contact, contact_idx = _first_cue_contact(events)
    # 仅统计"母球首次碰到目标球之后"的碰库，碰库发生在接触前不算解球
    cushion_after_contact = first_contact is not None and any(
        e.type == EVENT_CUSHION for e in events[contact_idx + 1:])

    foul = False
    reason = ''
    if cue_pocketed:
        foul, reason = True, '母球落袋'
    elif first_contact is None:
        foul, reason = True, '母球未碰到任何球'
    else:
        fc_group = group_of(first_contact)
        if open_table:
            if first_contact == 8:
                foul, reason = True, '开放球台不能先碰8号球'
        elif shooter_on_eight:
            if first_contact != 8:
                foul, reason = True, '应先碰8号球'
        elif fc_group != shooter_group:
            foul, reason = True, '先碰到对方或错误的球'
    # 空杆：无目标球进袋，且接触目标球后没有任何球碰库
    if not foul and not object_pocketed and not cushion_after_contact:
        foul, reason = True, '空杆：碰球后无球进袋也无球碰库'

    # 胜负
    winner_is_shooter = None
    if eight_pocketed:
        winner_is_shooter = bool(shooter_on_eight and not foul)

    # 开放球台认领分组
    assigned_group = None
    if open_table and not foul and object_pocketed and not eight_pocketed:
        groups = {group_of(n) for n in object_pocketed}
        if groups == {'solid'}:
            assigned_group = 'solid'
        elif groups == {'stripe'}:
            assigned_group = 'stripe'
        else:
            assigned_group = group_of(object_pocketed[0])

    # 续打
    effective_group = assigned_group or shooter_group
    continue_turn = False
    if not foul and winner_is_shooter is None and effective_group:
        if any(group_of(n) == effective_group for n in object_pocketed):
            continue_turn = True

    return ShotResult(
        pocketed=object_pocketed,
        cue_pocketed=cue_pocketed,
        foul=foul,
        foul_reason=reason,
        continue_turn=continue_turn,
        assigned_group=assigned_group,
        winner_is_shooter=winner_is_shooter,
    )
