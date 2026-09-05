import json
from pathlib import Path
from threading import Event

from jnotes2hinote.batch import CONFLICT_OVERWRITE, CONFLICT_RENAME, CONFLICT_SKIP, convert_batch
from jnotes2hinote.cli import collect_input_files, main, plan_output_paths
from jnotes2hinote.reporting import redact_report


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
    assert summary["skipped"] == 0
    assert summary["inputErrors"] == 0
    assert summary["notRun"] == 0
    assert [update.status for update in updates] == ["converted", "failed"]


def test_batch_summary_separates_skips_input_errors_and_not_run(tmp_path: Path):
    source = tmp_path / "note.Jnotes"
    source.touch()
    output = tmp_path / "output"
    output.mkdir()
    (output / "note.hinote").touch()

    summary = convert_batch(
        [source],
        output,
        conflict_strategy=CONFLICT_SKIP,
        initial_errors=[{"path": "missing.Jnotes", "error": "missing"}],
    )

    assert summary["schemaVersion"] == 2
    assert summary["converted"] == 0
    assert summary["failed"] == 0
    assert summary["skipped"] == 1
    assert summary["inputErrors"] == 1
    assert summary["notRun"] == 0
    assert {item["kind"] for item in summary["errors"]} == {"input_error", "skipped"}

    cancel_event = Event()
    cancel_event.set()
    cancelled = convert_batch([source], output, cancel_event=cancel_event)
    assert cancelled["cancelled"] is True
    assert cancelled["notRun"] == 1


def test_cli_returns_two_for_partial_batch_failure(tmp_path: Path, monkeypatch, capsys):
    first = tmp_path / "first.Jnotes"
    second = tmp_path / "second.Jnotes"
    output = tmp_path / "output"

    monkeypatch.setattr(
        "jnotes2hinote.cli.collect_input_files",
        lambda *_args, **_kwargs: ([first, second], []),
    )
    monkeypatch.setattr(
        "jnotes2hinote.cli.convert_batch",
        lambda *_args, **_kwargs: {
            "converted": 1,
            "failed": 1,
            "skipped": 0,
            "inputErrors": 0,
            "cancelled": False,
            "errors": [{"path": str(second), "error": "bad input", "kind": "conversion_failed"}],
        },
    )

    assert main([str(first), str(second), str(output)]) == 2
    error_output = capsys.readouterr().err
    assert "转换失败" in error_output
    assert "bad input" in error_output


def test_single_file_expected_error_has_no_traceback(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "broken.Jnotes"
    source.touch()
    monkeypatch.setattr("jnotes2hinote.cli.convert", lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyError("bad zip")))

    assert main([str(source), str(tmp_path / "output")]) == 1
    captured = capsys.readouterr()
    assert "转换失败：'bad zip'" in captured.err
    assert "Traceback" not in captured.err


def test_report_redaction_removes_titles_and_full_paths():
    payload = {
        "source": r"C:\\Users\\name\\private.Jnotes",
        "outputDirectory": r"D:\\private\\output",
        "title": "私人笔记",
        "errors": [
            {
                "path": r"D:\\private\\missing.Jnotes:4",
                "error": r"输入路径不存在：C:\\Users\\name\\Private Notes\\missing.Jnotes",
            }
        ],
    }

    redacted = redact_report(payload)

    encoded = json.dumps(redacted, ensure_ascii=False)
    assert "私人笔记" not in encoded
    assert "Users" not in encoded
    assert "Private Notes" not in encoded
    assert "private.Jnotes" in encoded
    assert "missing.Jnotes" in encoded
