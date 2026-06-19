"""碎纸粒子系统与标题弹入缓动的纯逻辑测试。无 pygame 依赖。

确定性伪随机:同一 frame 多次调用结果一致,不依赖全局随机状态。
"""
import confetti


W, H = 1000, 600


def _by_id(particles):
    return {p['id']: p for p in particles}


def test_released_particles_start_near_top():
    # 已释放的碎纸初始位置在屏幕上部(从顶部洒落)
    ps = confetti.particles_at(5, W, H)
    assert ps, "前几帧应已有部分碎纸释放"
    assert all(p['y'] <= H * 0.3 for p in ps)


def test_particle_falls_over_time():
    # 同一片碎纸(按 id 追踪)随帧推进 y 增大(下落)
    early = _by_id(confetti.particles_at(5, W, H))
    pid = next(iter(early))            # 取一片已释放的
    later = _by_id(confetti.particles_at(5 + 20, W, H))
    assert pid in later
    assert later[pid]['y'] > early[pid]['y']


def test_particles_empty_after_fall_complete():
    ps = confetti.particles_at(confetti.CONFETTI_FALL_FRAMES, W, H)
    assert ps == []
    ps2 = confetti.particles_at(confetti.CONFETTI_FALL_FRAMES + 50, W, H)
    assert ps2 == []


def test_particles_present_throughout_window():
    # 错开释放:在时长的前/中/后段都应有碎纸在屏幕内可见(速度不变,持续时间被拉长)
    for frac in (0.15, 0.5, 0.8):
        f = int(confetti.CONFETTI_FALL_FRAMES * frac)
        ps = confetti.particles_at(f, W, H)
        assert any(0 <= p['y'] <= H for p in ps), f"frame={f} 应有屏内碎纸"


def test_particles_deterministic():
    a = confetti.particles_at(42, W, H)
    b = confetti.particles_at(42, W, H)
    assert a == b


def test_particle_falls_at_natural_speed():
    # 自然(快)速度:某片碎纸从释放到落出屏幕底部不超过 ~120 帧(约 2 秒),
    # 而非被拖慢到铺满整个 5 秒。验证单片速度未被牺牲。
    # 追踪 0 号:找到它释放后的首帧,再看它何时落出屏外。
    first_seen = None
    fell_out = None
    for f in range(0, confetti.CONFETTI_FALL_FRAMES):
        present = 0 in _by_id(confetti.particles_at(f, W, H))
        if present and first_seen is None:
            first_seen = f
        if first_seen is not None and not present:
            fell_out = f
            break
    assert first_seen is not None and fell_out is not None
    assert fell_out - first_seen <= 120   # 单片快速穿屏,未被拖慢


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
