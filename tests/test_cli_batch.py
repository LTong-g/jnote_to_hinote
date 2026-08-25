from pathlib import Path

from jnotes2hinote.batch import CONFLICT_OVERWRITE, CONFLICT_RENAME, CONFLICT_SKIP, convert_batch
from jnotes2hinote.cli import collect_input_files, plan_output_paths


def test_directory_collection_is_one_level_by_default(tmp_path: Path):
    root = tmp_path / "notes"
    nested = root / "nested"
    nested.mkdir(parents=True)
    top = root / "top.Jnotes"
    deep = nested / "deep.jnote"
    top.touch()
    deep.touch()

    files, errors = collect_input_files([root])

    assert files == [top.resolve()]
    assert errors == []

    files, errors = collect_input_files([root], recursive=True)

    assert files == [deep.resolve(), top.resolve()]
    assert errors == []


def test_manifest_uses_its_directory_and_keeps_errors(tmp_path: Path):
    manifest_dir = tmp_path / "lists"
    manifest_dir.mkdir()
    source = manifest_dir / "note.Jnotes"
    source.touch()
    manifest = manifest_dir / "paths.txt"
    manifest.write_text("# comment\n\nnote.Jnotes\nmissing.Jnotes\n", encoding="utf-8")

    files, errors = collect_input_files([manifest])

    assert files == [source.resolve()]
    assert len(errors) == 1
    assert errors[0]["path"].endswith("paths.txt:4")


def test_batch_output_names_are_disambiguated(tmp_path: Path):
    first = tmp_path / "one" / "note.Jnotes"
    second = tmp_path / "two" / "note.Jnotes"
    first.parent.mkdir()
    second.parent.mkdir()
    first.touch()
    second.touch()
    output_dir = tmp_path / "output"

    planned = plan_output_paths([first, second], output_dir)

    assert planned[first] == output_dir / "note.hinote"
    assert planned[second] == output_dir / "note_2.hinote"


def test_output_conflict_strategies(tmp_path: Path):
    source = tmp_path / "note.Jnotes"
    source.touch()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "note.hinote").touch()

    renamed = plan_output_paths([source], output_dir, conflict_strategy=CONFLICT_RENAME)
    skipped = plan_output_paths([source], output_dir, conflict_strategy=CONFLICT_SKIP)
    overwritten = plan_output_paths([source], output_dir, conflict_strategy=CONFLICT_OVERWRITE)

    assert renamed[source] == output_dir / "note_2.hinote"
    assert skipped[source] is None
    assert overwritten[source] == output_dir / "note.hinote"


def test_batch_runner_emits_progress_and_continues_after_failure(tmp_path: Path, monkeypatch):
    first = tmp_path / "first.Jnotes"
    second = tmp_path / "second.Jnotes"
    first.touch()
    second.touch()
    updates = []

    def fake_convert(source: Path, output: Path, page_limit=None):
        if source == second:
            raise ValueError("bad test input")
        output.write_bytes(b"hinote")
        return {"source": str(source), "output": str(output), "pages": 1}

    monkeypatch.setattr("jnotes2hinote.batch.convert", fake_convert)
    summary = convert_batch(
        [first, second],
        tmp_path / "output",
        progress_callback=updates.append,
    )

    assert summary["converted"] == 1
    assert summary["failed"] == 1
    assert [update.status for update in updates] == ["converted", "failed"]
