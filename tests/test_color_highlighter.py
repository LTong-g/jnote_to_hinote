import struct

from jnotes2hinote.converter_v1_1_0 import _source_alpha, _write_huawei_bgr, f32be


def test_huawei_bgr_layout():
    style = bytearray(108)
    # ARGB FF 36 4C 7E
    _write_huawei_bgr(style, {"c": 0xFF364C7E})
    b, g, r = struct.unpack_from(">fff", style, 64)
    assert abs(b - 0x7E / 255) < 1e-6
    assert abs(g - 0x4C / 255) < 1e-6
    assert abs(r - 0x36 / 255) < 1e-6


def test_source_alpha():
    assert _source_alpha({"c": 0x50364C7E}) == 0x50
    assert _source_alpha({"c": -1}) == 255


def test_float_helper_is_big_endian():
    assert f32be(1.0) == b"\x3f\x80\x00\x00"
