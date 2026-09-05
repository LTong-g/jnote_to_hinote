import re
from pathlib import Path

from jnotes2hinote import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_are_synchronized():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    project_version = re.search(r'^version\s*=\s*"([^"]+)"\s*$', pyproject, re.MULTILINE)
    citation_version = re.search(r"^version:\s*(\S+)\s*$", citation, re.MULTILINE)

    assert project_version is not None
    assert project_version.group(1) == __version__
    assert citation_version is not None
    assert citation_version.group(1) == __version__
