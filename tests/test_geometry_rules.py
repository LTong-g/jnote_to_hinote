import math
import struct

import pytest

from jnotes2hinote.converter_v1_1_1 import (
    J_GEOMETRY_TO_HW_SHAPE,
    _build_geometry_body,
    _geometry_width_direct,
)


def test_device_tested_geometry_mapping():
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 0)] == 0
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 12)] == 16
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 4)] == 10
    assert J_GEOMETRY_TO_HW_SHAPE[(7, 3)] == 7
    assert J_GEOMETRY_TO_HW_SHAPE[(7, 4)] == 10


def test_geometry_width_matches_ordinary_pen_directly():
    assert _geometry_width_direct(3) == 3
    assert _geometry_width_direct(3.04) == 3.04
    assert _geometry_width_direct(4.93) == 4.93
    assert _geometry_width_direct(12.72) == 12.72
    assert _geometry_width_direct(30) == 30


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_geometry_width_rejects_non_finite_values(value):
    with pytest.raises(ValueError, match="有限数值"):
        _geometry_width_direct(value)


def test_translucent_type6_b12_is_highlighter():
    # ARGB alpha=80，Jnotes 几何 d=30。这是设备验证中的半透明曲线样本。
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
