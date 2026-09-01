import struct

from jnotes2hinote.converter_v1_1_2 import _parse_normal_pencilengine, build_pencilengine


def _stroke(x0, y0, x1, y1):
    return {
        "c": {
            "a": 2,
            "b": 0,
            "c": -16777216,
            "d": 3.0,
            "k": [
                {"x": x0, "y": y0, "p": 0.2},
                {"x": x1, "y": y1, "p": 0.3},
            ],
        }
    }


def test_self_contained_chain_generation():
    data, stats = build_pencilengine([_stroke(1, 2, 3, 4), _stroke(5, 6, 7, 8)], 1.0)
    assert data.startswith(b"PENCILENGINE")
    blocks = _parse_normal_pencilengine(data)
    assert len(blocks) == 2
    assert stats["normal"] == 2

    first_count = blocks[0][2]
    assert struct.unpack_from(">I", data, 148)[0] == first_count * 36 + 140
    assert struct.unpack_from(">I", data, 180)[0] == first_count * 36 + 20

    first_end = blocks[0][4]
    second_count = blocks[1][2]
    assert struct.unpack_from(">I", data, first_end + 16)[0] == second_count * 36 + 140
    assert struct.unpack_from(">I", data, first_end + 48)[0] == second_count * 36 + 20
