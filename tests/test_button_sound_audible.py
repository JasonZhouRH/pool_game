"""回归测试:按钮点击音必须足够响(可听见)。

曾因换入一个录制电平过低的 CC0 音效(峰值仅 ~5507,约其它音效的 1/6),
在背景音乐之上几乎听不到。此测试断言 btn_click.wav 的样本峰值达到可听阈值,
防止再次混入过轻的音效。

读取 16-bit PCM 样本峰值用标准库(wave + struct),不依赖 numpy/audioop。
"""
import os
import struct
import wave

import pytest

_SOUND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sounds')
_BTN = os.path.join(_SOUND_DIR, 'btn_click.wav')

# 其它音效峰值约 32000(满量程 32767)。低于此阈值视为过轻、可能听不到。
_AUDIBLE_PEAK = 15000


def _wav_peak(path):
    """返回 16-bit WAV 的样本绝对值峰值(0 = 纯静音)。"""
    with wave.open(path, 'rb') as w:
        assert w.getsampwidth() == 2, "本测试假设 16-bit PCM"
        frames = w.readframes(w.getnframes())
    peak = 0
    for i in range(0, len(frames) - 1, 2):
        v = struct.unpack_from('<h', frames, i)[0]
        if abs(v) > peak:
            peak = abs(v)
    return peak


def test_button_click_is_audible():
    assert os.path.exists(_BTN), "btn_click.wav 应存在"
    peak = _wav_peak(_BTN)
    assert peak >= _AUDIBLE_PEAK, (
        f"按钮音过轻:峰值 {peak} < {_AUDIBLE_PEAK},在背景音乐上会听不到")
