import pytest


pytest.importorskip("tkinter")
from jnotes2hinote.gui import parse_page_limit  # noqa: E402


def test_parse_page_limit():
    assert parse_page_limit("0") is None
    assert parse_page_limit("5") == 5

    with pytest.raises(ValueError):
        parse_page_limit("-1")

    with pytest.raises(ValueError):
        parse_page_limit("pages")
