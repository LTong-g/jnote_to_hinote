import struct

from jnotes2hinote.converter_v1_1_0 import (
    J_GEOMETRY_TO_HW_SHAPE,
    _build_geometry_body,
    _geometry_width_tiered,
)


def test_device_tested_geometry_mapping():
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 0)] == 0
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 12)] == 16
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 4)] == 10
    assert J_GEOMETRY_TO_HW_SHAPE[(7, 3)] == 7
    assert J_GEOMETRY_TO_HW_SHAPE[(7, 4)] == 10


def test_restored_geometry_width_tiers():
    assert _geometry_width_tiered(3) == 2
    assert _geometry_width_tiered(4.93) == 4
    assert _geometry_width_tiered(12.72) == 8
    assert _geometry_width_tiered(30) == 8


def test_translucent_type6_b12_is_highlighter():
    # ARGB alpha=80，Jnotes 几何 d=30；这是经过设备验证的半透明曲线案例。
    c = {
        "a": 6, "b": 12, "d": 30.0, "c": (80 << 24) | 0x3366CC,
        "k": [
            {"x": 10.0, "y": 20.0, "p": 0.2},
            {"x": 30.0, "y": 40.0, "p": 0.3},
        ],
    }
    body, count, native_geometry = _build_geometry_body({"c": c}, 1.0)
    style = body[:108]
    assert native_geometry is False
    assert struct.unpack_from(">I", style, 56)[0] == 5  # 华为荧光笔
    assert round(struct.unpack_from(">f", style, 84)[0], 5) == 32.0
    assert abs(struct.unpack_from(">f", style, 76)[0] - 80 / 255) < 1e-6
    assert abs(struct.unpack_from(">f", style, 80)[0] - 80 / 255) < 1e-6
