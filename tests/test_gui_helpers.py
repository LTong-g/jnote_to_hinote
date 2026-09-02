import pytest

pytest.importorskip("tkinter")
import tkinter as tk

from jnotes2hinote.gui import Jnotes2HinoteApp, create_root, parse_drop_paths, parse_page_limit


def test_parse_page_limit():
    assert parse_page_limit("0") is None
    assert parse_page_limit("5") == 5

    with pytest.raises(ValueError):
        parse_page_limit("-1")

    with pytest.raises(ValueError):
        parse_page_limit("pages")


def test_parse_drop_paths_preserves_paths_with_spaces_and_unicode():
    payload = r"{C:\Notes Folder\first.Jnotes} {D:\资料\second.jnote}"

    def splitlist(value):
        if value == payload:
            return (
                r"C:\Notes Folder\first.Jnotes",
                r"D:\资料\second.jnote",
            )
        return ()

    assert parse_drop_paths(payload, splitlist) == (
        r"C:\Notes Folder\first.Jnotes",
        r"D:\资料\second.jnote",
    )


def test_parse_drop_paths_supports_multiple_simple_paths():
    def splitlist(value):
        return tuple(value.split())

    assert parse_drop_paths("/tmp/one.Jnotes /tmp/two.jnote", splitlist) == (
        "/tmp/one.Jnotes",
        "/tmp/two.jnote",
    )


def test_parse_drop_paths_returns_empty_for_blank_or_malformed_data():
    def malformed(_value):
        raise tk.TclError("malformed Tcl list")

    assert parse_drop_paths("", malformed) == ()
    assert parse_drop_paths("{unterminated", malformed) == ()


def test_layout_paned_windows_own_their_children():
    try:
        root = create_root()
    except tk.TclError:
        pytest.skip("Tk display is unavailable")

    try:
        root.withdraw()
        app = Jnotes2HinoteApp(root)
        for pane_name in app.workspace_pane.panes():
            assert root.nametowidget(pane_name).winfo_parent() == str(app.workspace_pane)
        for pane_name in app.results_log_pane.panes():
            assert root.nametowidget(pane_name).winfo_parent() == str(app.results_log_pane)
    finally:
        root.destroy()
