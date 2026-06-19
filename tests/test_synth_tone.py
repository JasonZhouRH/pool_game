"""音频合成纯函数 synth_tone 的逻辑测试。

合成匹配 mixer 格式(44100Hz/16bit signed/stereo)的 PCM 字节,纯数学(struct+math),
不依赖 pygame mixer,可单测。验证字节长度与格式契约,而非听感。
"""
import sounds


SAMPLE_RATE = 44100
CHANNELS = 2
BYTES_PER_SAMPLE = 2   # 16-bit


def test_byte_length_matches_duration():
    # 100ms → 44100*0.1 帧,每帧 2 声道 * 2 字节
    ms = 100
    data = sounds.synth_tone(440, ms, 0.5)
    expected_frames = round(SAMPLE_RATE * ms / 1000)
    assert len(data) == expected_frames * CHANNELS * BYTES_PER_SAMPLE


def test_returns_bytes():
    data = sounds.synth_tone(880, 60, 0.5)
    assert isinstance(data, (bytes, bytearray))
    assert len(data) > 0


def test_length_independent_of_frequency():
    # 时长相同则字节数相同,与频率无关
    a = sounds.synth_tone(330, 80, 0.5)
    b = sounds.synth_tone(880, 80, 0.5)
    assert len(a) == len(b)


def test_starts_and_ends_at_silence():
    # 淡入淡出:首帧与末帧应接近静音(振幅≈0),避免爆音
    import struct
    data = sounds.synth_tone(440, 100, 0.8)
    first_l, first_r = struct.unpack_from('<hh', data, 0)
    last_l, last_r = struct.unpack_from('<hh', data, len(data) - 4)
    assert abs(first_l) < 1000 and abs(first_r) < 1000
    assert abs(last_l) < 1000 and abs(last_r) < 1000


def test_amplitude_respects_volume():
    # 峰值振幅随 volume 缩放:大音量峰值更高
    import struct
    quiet = sounds.synth_tone(440, 100, 0.2)
    loud = sounds.synth_tone(440, 100, 0.9)

    def peak(data):
        return max(abs(struct.unpack_from('<h', data, i)[0])
                   for i in range(0, len(data), 2))

    assert peak(loud) > peak(quiet)
    assert peak(loud) <= 32767   # 不溢出 16-bit
