from pathlib import Path

from jnotes2hinote.converter_v1_1_2 import JNote, convert, render_thumbnail


def test_v1_1_2_converts_bilingual_text(tmp_path: Path, monkeypatch):
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
    thumbnail = render_thumbnail(note, note.pages[0], [], [], note.texts[page_id], None)
    assert thumbnail.startswith(b"\xff\xd8")

    output = tmp_path / "bilingual.hinote"
    monkeypatch.setattr("jnotes2hinote.converter_v1_1_2.parse_jnotes", lambda _: note)
    result = convert(Path("fixture.Jnotes"), output)
    assert result["converterVersion"] == "1.1.2"
    assert output.is_file()
