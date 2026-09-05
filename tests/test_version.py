from jnotes2hinote import CONVERTER_CORE_VERSION, TESTED_HUAWEI_NOTES_VERSION, TESTED_JNOTES_VERSION, __version__
from jnotes2hinote.converter import __version__ as converter_core_version


def test_version_metadata():
    assert __version__ == "1.6.0"
    assert CONVERTER_CORE_VERSION == __version__
    assert converter_core_version == __version__
    assert TESTED_JNOTES_VERSION == "3.2.3.2"
    assert TESTED_HUAWEI_NOTES_VERSION == "15.0.14.295"
