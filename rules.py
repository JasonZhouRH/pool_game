"""8 球/9 球/斯诺克规则判定：消费 physics 事件，输出本杆结果。无 pygame 依赖。"""
import math
from dataclasses import dataclass

import config
from balls import group_of, snooker_value
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


def is_legal_first_contact(number, open_table, shooter_group, shooter_on_eight):
    """该球作为母球首个碰到的球是否合法。与 evaluate_shot 的犯规判定一致。

    开放球台：除 8 号外都合法；打 8 阶段：仅 8 号合法；已分组：仅本组合法。
    """
    if open_table:
        return number != 8
    if shooter_on_eight:
        return number == 8
    return group_of(number) == shooter_group


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
    elif not is_legal_first_contact(first_contact, open_table, shooter_group, shooter_on_eight):
        if open_table:
            reason = '开放球台不能先碰8号球'
        elif shooter_on_eight:
            reason = '应先碰8号球'
        else:
            reason = '先碰到对方或错误的球'
        foul = True
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


def is_lowest_ball_on_table(number, balls):
    """返回 `number` 是否是台面上编号最小的球（不含母球 0）。"""
    lowest = None
    for b in balls:
        if b.on_table and b.number != 0:
            if lowest is None or b.number < lowest:
                lowest = b.number
    return lowest is not None and number == lowest


def is_legal_nine_ball_contact(number, balls):
    """该球作为母球首个碰到的球是否合法。9 球必须始终先碰台面最小号球。"""
    return is_lowest_ball_on_table(number, balls)


def evaluate_nine_ball_shot(events, lowest_on_table, is_ball_in_hand=False):
    """评估一杆 9 球，返回 ShotResult。

    lowest_on_table: 击球前台面上编号最小的球号（快照）；物理推进后落袋球已移除，不能事后判断。
    is_ball_in_hand: 自由球状态下，传进（连击）9 号判对手胜。
    """
    pocketed_all = [e.data['number'] for e in events if e.type == EVENT_POCKETED]
    cue_pocketed = 0 in pocketed_all
    object_pocketed = [n for n in pocketed_all if n != 0]
    nine_pocketed = 9 in pocketed_all
    first_contact, contact_idx = _first_cue_contact(events)

    # 碰库判定：仅统计母球首次碰到目标球之后的碰库事件
    cushion_after_contact = first_contact is not None and any(
        e.type == EVENT_CUSHION for e in events[contact_idx + 1:])

    foul = False
    reason = ''
    if cue_pocketed:
        foul, reason = True, '母球落袋'
    elif first_contact is None:
        foul, reason = True, '母球未碰到任何球'
    elif first_contact != lowest_on_table:
        foul, reason = True, '未先碰到台面最小号球'
    elif not object_pocketed and not cushion_after_contact:
        foul, reason = True, '空杆：碰球后无球进袋也无球碰库'

    # 胜负判定
    winner_is_shooter = None
    if nine_pocketed:
        if foul:
            winner_is_shooter = False    # 犯规打进 9 球 → 对手胜
        elif is_ball_in_hand and first_contact != 9:
            # 自由球不能传进 9 号（非首先碰到 9 号却打进 9 号），判对手胜
            winner_is_shooter = False
            foul = True
            reason = '自由球传进9号，对手胜'
        else:
            winner_is_shooter = True     # 合法打进 9 球 → 胜

    # 续打判定：无犯规、未分胜负、且至少打进一球
    continue_turn = False
    if not foul and winner_is_shooter is None and object_pocketed:
        continue_turn = True

    return ShotResult(
        pocketed=object_pocketed,
        cue_pocketed=cue_pocketed,
        foul=foul,
        foul_reason=reason,
        continue_turn=continue_turn,
        assigned_group=None,            # 9 球无花色分组
        winner_is_shooter=winner_is_shooter,
    )


def is_legal_snooker_contact(number, balls):
    """斯诺克台面任何球都可碰（简化规则，后续完善）。"""
    return number != 0


def snooker_balls_on(phase, next_color, balls):
    """当前阶段合法目标球号集合(ball-on)。

    红球阶段:台面所有红球(1-15)。
    定彩阶段(next_color 非 None):那一颗指定彩球。
    自选彩球阶段(next_color is None):台面所有彩球(16-21)。
    """
    on_table = {b.number for b in balls if b.on_table}
    if phase == 'red':
        return {n for n in on_table if 1 <= n <= 15}
    if next_color is not None:
        return {next_color}
    return {n for n in on_table if 16 <= n <= 21}


# 斯诺克彩球号 → 颜色名映射
_SNOOKER_COLOR_NAMES = {16: 'yellow', 17: 'green', 18: 'brown',
                         19: 'blue', 20: 'pink', 21: 'black'}


def evaluate_snooker_shot(events, balls, phase, next_color, table):
    """评估一杆斯诺克，返回 ShotResult。

    phase: 'red' (必须打红球) 或 'color' (必须打指定彩球)
    next_color: phase='color' 时要求的彩球号 (16-21)，phase='red' 时为 None
    table: Table 实例，用于彩球复位
    """
    from balls import snooker_value
    pocketed_all = [e.data['number'] for e in events if e.type == EVENT_POCKETED]
    cue_pocketed = 0 in pocketed_all
    object_pocketed = [n for n in pocketed_all if n != 0]
    first_contact, contact_idx = _first_cue_contact(events)

    cushion_after_contact = first_contact is not None and any(
        e.type == EVENT_CUSHION for e in events[contact_idx + 1:])

    foul = False
    reason = ''
    foul_points = 0

    # 当前合法目标球集合
    balls_on = snooker_balls_on(phase, next_color, balls)

    # 犯规判定
    if cue_pocketed:
        foul, reason = True, '母球落袋'
    elif first_contact is None:
        foul, reason = True, '母球未碰到任何球'
    elif phase == 'red' and not (1 <= first_contact <= 15):
        foul, reason = True, '应先碰红球'
    elif phase == 'color':
        if next_color is not None and first_contact != next_color:
            color_name = _SNOOKER_COLOR_NAMES.get(next_color, '?')
            foul, reason = True, f'应先碰{color_name}球'
        elif next_color is None and not (16 <= first_contact <= 21):
            foul, reason = True, '应先碰彩球'

    # 红球阶段打进彩球：即使首碰红球合法，落袋彩球也算犯规
    if not foul and phase == 'red':
        illegal_potted = [n for n in object_pocketed if 16 <= n <= 21]
        if illegal_potted:
            foul, reason = True, '红球阶段打进彩球'

    # 彩球阶段打进非目标球：仅升序阶段适用(自选槽任意彩球都是合法目标)
    if not foul and phase == 'color' and next_color is not None:
        illegal_potted = [n for n in object_pocketed if n not in balls_on]
        if illegal_potted:
            foul, reason = True, '打进了非目标彩球'

    # 犯规罚分：取 4、目标球分值、误碰首球分值、误进球最高分值 的最大值
    if foul:
        candidates = [4]
        for n in balls_on:
            candidates.append(snooker_value(n))
        if first_contact is not None:
            candidates.append(snooker_value(first_contact))
        for n in object_pocketed:
            candidates.append(snooker_value(n))
        foul_points = max(candidates)

    # 计分：仅未犯规时累加分值
    points_scored = 0
    if not foul:
        for n in object_pocketed:
            points_scored += snooker_value(n)

    # 彩球复位：误进的彩球(犯规)必复位；合法的自选彩球(跟在红球后)也复位；
    # 升序阶段合法打进的彩球不复位(留在袋中)；红球从不复位。
    respot_colors = []
    for n in object_pocketed:
        if not (16 <= n <= 21):
            continue
        if foul or next_color is None:
            respot_colors.append(n)

    # 确定下一阶段
    new_phase = phase
    new_next_color = next_color
    reds_left = any(b.on_table and 1 <= b.number <= 15 for b in balls)
    color_order = (16, 17, 18, 19, 20, 21)

    if phase == 'red':
        if not foul and any(1 <= n <= 15 for n in object_pocketed):
            # 打进红球 → 下一颗打自选彩球
            new_phase = 'color'
            new_next_color = None
        # 其余(未进红球的安全球/失误，或犯规)仍是红球阶段
    elif next_color is None:
        # 自选彩球槽(跟在红球之后)
        if reds_left:
            new_phase = 'red'        # 还有红球 → 回到打红球
            new_next_color = None
        else:
            # 红球已清完 → 进入彩球升序阶段，从最低在台彩球开始
            new_phase = 'color'
            new_next_color = None
            for cn in color_order:
                if any(b.on_table and b.number == cn for b in balls):
                    new_next_color = cn
                    break
    else:
        # 升序阶段
        if not foul and next_color in object_pocketed:
            idx = color_order.index(next_color)
            new_phase = 'color'
            new_next_color = None
            for j in range(idx + 1, len(color_order)):
                if any(b.on_table and b.number == color_order[j] for b in balls):
                    new_next_color = color_order[j]
                    break
        # 未进/犯规 → 保持 next_color

    # 续打
    continue_turn = not foul and object_pocketed and points_scored > 0

    # 胜负：所有球清完，比分高者胜（在 Game 层处理）
    winner_is_shooter = None
    all_off = not any(b.on_table and b.number != 0 for b in balls)
    if all_off:
        winner_is_shooter = None  # 比分决定，Game 层处理

    return ShotResult(
        pocketed=object_pocketed,
        cue_pocketed=cue_pocketed,
        foul=foul,
        foul_reason=reason,
        continue_turn=continue_turn,
        assigned_group=None,
        winner_is_shooter=None,
    ), points_scored, foul_points, respot_colors, new_phase, new_next_color


def _segment_hits_circle(x0, y0, x1, y1, cx, cy, radius):
    """线段 (x0,y0)->(x1,y1) 是否与圆心 (cx,cy) 半径 radius 的圆相交。"""
    dx, dy = x1 - x0, y1 - y0
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return (x0 - cx) ** 2 + (y0 - cy) ** 2 <= radius ** 2
    # 投影参数 t,夹到 [0,1]
    t = ((cx - x0) * dx + (cy - y0) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    px, py = x0 + t * dx, y0 + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2 <= radius ** 2


def _path_clear_to_edge(cue, target, all_balls, edge_sign):
    """母球能否沿擦过 target 某侧最薄边的直线打到该 target。

    edge_sign: +1=右侧切线, -1=左侧切线。
    用半径 2*R 的扫掠圆检测路径上是否有其他球阻挡。
    """
    r = config.BALL_RADIUS
    dx, dy = target.x - cue.x, target.y - cue.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return True
    ux, uy = dx / dist, dy / dist
    # 法向(垂直于瞄准线),指向某侧偏移一个球半径,使射线擦过 target 边缘
    nx, ny = -uy, ux
    aim_x = target.x + edge_sign * r * nx
    aim_y = target.y + edge_sign * r * ny
    for b in all_balls:
        if b.number in (0, target.number) or not b.on_table:
            continue
        # 阻挡判定:其他球到 (cue->aim点) 线段距离 < 2R(母球扫掠)
        if _segment_hits_circle(cue.x, cue.y, aim_x, aim_y,
                                b.x, b.y, 2 * r):
            return False
    return True


def is_snookered(cue, balls_on, all_balls):
    """母球是否被障碍:对每颗 ball-on,两侧最薄边至少一侧可直线打到则不算障碍。

    所有 ball-on 的两侧都被挡 → 返回 True。
    """
    for tgt in all_balls:
        if tgt.number not in balls_on or not tgt.on_table:
            continue
        right_clear = _path_clear_to_edge(cue, tgt, all_balls, +1)
        left_clear = _path_clear_to_edge(cue, tgt, all_balls, -1)
        if right_clear or left_clear:
            return False
    return True
