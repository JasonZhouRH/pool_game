"""碎纸粒子系统与标题弹入缓动的纯逻辑测试。无 pygame 依赖。

确定性伪随机:同一 frame 多次调用结果一致,不依赖全局随机状态。
"""
import confetti


W, H = 1000, 600


def test_particles_at_frame0_near_top():
    ps = confetti.particles_at(0, W, H)
    assert len(ps) == confetti.CONFETTI_COUNT
    # 第 0 帧所有碎纸在屏幕上部(从顶部洒落)
    assert all(p['y'] <= H * 0.25 for p in ps)


def test_particles_fall_over_time():
    p0 = confetti.particles_at(0, W, H)
    p30 = confetti.particles_at(30, W, H)
    # 取同一个粒子(列表顺序按序号稳定),后续帧 y 应更大(下落)
    assert p30[0]['y'] > p0[0]['y']


def test_particles_empty_after_fall_complete():
    ps = confetti.particles_at(confetti.CONFETTI_FALL_FRAMES, W, H)
    assert ps == []
    ps2 = confetti.particles_at(confetti.CONFETTI_FALL_FRAMES + 50, W, H)
    assert ps2 == []


def test_particles_count_while_active():
    # 落完之前任一帧都应有全部粒子
    ps = confetti.particles_at(confetti.CONFETTI_FALL_FRAMES - 1, W, H)
    assert len(ps) == confetti.CONFETTI_COUNT


def test_particles_deterministic():
    a = confetti.particles_at(42, W, H)
    b = confetti.particles_at(42, W, H)
    assert a == b


def test_particles_have_color_and_angle():
    ps = confetti.particles_at(10, W, H)
    p = ps[0]
    assert 'x' in p and 'y' in p and 'color' in p and 'angle' in p
    # 颜色是 RGB 三元组
    assert len(p['color']) == 3


def test_title_scale_starts_near_zero():
    assert confetti.title_scale(0) < 0.2


def test_title_scale_overshoots_above_one():
    # 弹入过程中存在超过 1 的峰值(回弹效果);扫描整个弹入区间
    peak = max(confetti.title_scale(f)
               for f in range(0, confetti._TITLE_BOUNCE_FRAMES))
    assert peak > 1.0


def test_title_scale_settles_at_one():
    # 弹入结束后稳定为 1.0
    assert abs(confetti.title_scale(confetti._TITLE_BOUNCE_FRAMES) - 1.0) < 1e-9
    assert abs(confetti.title_scale(confetti._TITLE_BOUNCE_FRAMES + 100) - 1.0) < 1e-9
