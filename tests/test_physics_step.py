import config
from balls import Ball
from table import Table
from physics import step, all_stopped, EVENT_POCKETED, EVENT_BALL_HIT, EVENT_CUSHION


def make_table():
    return Table(config.TABLE_LEFT, config.TABLE_TOP, config.TABLE_RIGHT, config.TABLE_BOTTOM)


def run_until_stopped(balls, table, max_frames=2000):
    events = []
    for _ in range(max_frames):
        events.extend(step(balls, table))
        if all_stopped(balls):
            break
    return events


def test_moving_ball_eventually_stops_due_to_friction():
    t = make_table()
    b = Ball(number=1, x=t.center_y * 0 + (t.left + t.right) / 2, y=t.center_y, vx=8.0, vy=0.0)
    run_until_stopped([b], t)
    assert all_stopped([b])


def test_ball_aimed_at_pocket_is_pocketed():
    t = make_table()
    px, py = t.pocket_positions()[5]    # 右下角袋
    b = Ball(number=3, x=px - 60, y=py - 60, vx=6.0, vy=6.0)
    events = run_until_stopped([b], t)
    assert any(e.type == EVENT_POCKETED and e.data['number'] == 3 for e in events)
    assert b.on_table is False


def test_collision_emits_ball_hit_event():
    t = make_table()
    cx = (t.left + t.right) / 2
    a = Ball(number=0, x=cx - 40, y=t.center_y, vx=6.0, vy=0.0)
    b = Ball(number=1, x=cx + 40, y=t.center_y, vx=0.0, vy=0.0)
    events = run_until_stopped([a, b], t)
    hits = [e for e in events if e.type == EVENT_BALL_HIT]
    assert hits, "应至少有一次球间碰撞"
    assert {hits[0].data['a'], hits[0].data['b']} == {0, 1}


def test_wall_bounce_emits_cushion_event():
    t = make_table()
    b = Ball(number=2, x=t.right - 30, y=t.center_y, vx=6.0, vy=0.0)
    events = run_until_stopped([b], t)
    assert any(e.type == EVENT_CUSHION and e.data['number'] == 2 for e in events)
