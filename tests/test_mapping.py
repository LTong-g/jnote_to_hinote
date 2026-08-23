import struct

from jnotes2hinote.converter_v1_1_1 import (
    _normal_tail,
    background_for_page,
)


def page(bg: str, hor_parts: float = 0.0):
    import json

    return {
        "d": bg,
        "p": json.dumps({"paperBg": bg, "horParts": hor_parts, "verParts": hor_parts}),
    }


def test_background_mapping():
    assert background_for_page(page("PageBg/White_Blank_Paper")) == "base1"
    assert background_for_page(page("PageBg/White_Line_paper_1_Paper", -2)) == "base5"  # 界面尺寸 1
    assert background_for_page(page("PageBg/White_Line_paper_1_Paper", -1)) == "base5"  # 界面尺寸 2
    assert background_for_page(page("PageBg/White_Line_paper_1_Paper", 0)) == "base4"   # 界面尺寸 3
    assert background_for_page(page("/storage/.../1000_2_0_v-narrow-line-white")) == "base4"
    assert background_for_page(page("PageBg/White_Dotted_Paper")) == "base6"
    assert background_for_page(page("PageBg/White_Graph_Paper", 0)) == "base3"         # 界面尺寸 3
    assert background_for_page(page("PageBg/White_Graph_Paper", 3)) == "base2"         # 界面尺寸 6
    assert background_for_page(page("PageBg/White_Wide_Grid_Paper", 0)) == "base2"


def test_next_count_tail_formulas():
    tail = _normal_tail(cur_count=12, next_count=19, stroke_uuid=b"1" * 16, seq=123)
    assert struct.unpack_from(">I", tail, 16)[0] == 19 * 36 + 140
    assert struct.unpack_from(">I", tail, 48)[0] == 19 * 36 + 20
    assert struct.unpack_from(">I", tail, 4)[0] == 48
    assert tail[20:36] == b"1" * 16
