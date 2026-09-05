import io

from PIL import Image, JpegImagePlugin

from jnotes2hinote.thumbnail import (
    THUMBNAIL_MAX_EDGE,
    render_regular_thumbnail,
    thumbnail_dimensions,
)


def _render_thumbnail(page_width: float, page_height: float, end_x: float, end_y: float) -> Image.Image:
    payload = render_regular_thumbnail(
        page_width=page_width,
        page_height=page_height,
        strokes=[
            {
                "c": {
                    "a": 2,
                    "c": -16777216,
                    "d": 3,
                    "k": [{"x": 20, "y": 30}, {"x": end_x, "y": end_y}],
                },
            }
        ],
        images=[],
        texts=[{"x": 40, "y": 100, "g": 40, "e": "中文 English"}],
        cover=None,
    )
    image = Image.open(io.BytesIO(payload))
    image.load()
    return image


def _assert_native_jpeg(image: Image.Image, expected_size: tuple[int, int]) -> None:
    assert image.format == "JPEG"
    assert image.size == expected_size
    assert JpegImagePlugin.get_sampling(image) == 2
    assert {value for table in image.quantization.values() for value in table} == {1}
    assert image.convert("L").getextrema()[0] < 240


def test_native_thumbnail_dimensions_match_observed_hinote_samples():
    assert thumbnail_dimensions(675, 1080) == (675, 1080)
    assert thumbnail_dimensions(0.706, 1) == (762, 1080)


def test_thumbnail_longest_edge_is_limited_for_both_orientations():
    assert thumbnail_dimensions(4, 3) == (1080, 810)
    assert thumbnail_dimensions(1.4142856382232933, 1) == (1080, 764)


def test_portrait_thumbnail_uses_native_resolution_and_jpeg_quality():
    image = _render_thumbnail(1240, 1754, 1100, 1500)
    _assert_native_jpeg(image, (round(1240 / 1754 * THUMBNAIL_MAX_EDGE), THUMBNAIL_MAX_EDGE))


def test_landscape_thumbnail_keeps_native_quality_with_longest_edge_limit():
    image = _render_thumbnail(1754, 1240, 1500, 1100)
    _assert_native_jpeg(image, (THUMBNAIL_MAX_EDGE, round(1240 / 1754 * THUMBNAIL_MAX_EDGE)))


def test_thumbnail_renders_bilingual_text():
    payload = render_regular_thumbnail(
        page_width=1240,
        page_height=1754,
        strokes=[],
        images=[],
        texts=[{"x": 20, "y": 20, "e": "中文 English"}],
        cover=None,
    )
    assert payload.startswith(b"\xff\xd8")
