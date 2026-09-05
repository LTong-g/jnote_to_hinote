from jnotes2hinote.reader import JNote
from jnotes2hinote.thumbnail import render_regular_thumbnail


def test_thumbnail_renders_bilingual_text():
    page_id = "page-id"
    note = JNote(
        note_uuid="note-id",
        title="中文 English",
        width=1240.0,
        height=1754.0,
        note_meta={},
        pages=[{"a": page_id, "d": "PageBg/White_Blank_Paper"}],
        records=[],
        texts={page_id: [{"x": 20, "y": 20, "e": "中文 English"}]},
    )
    thumbnail = render_regular_thumbnail(
        page_width=note.width,
        page_height=note.height,
        strokes=[],
        images=[],
        texts=note.texts[page_id],
        cover=None,
    )
    assert thumbnail.startswith(b"\xff\xd8")

