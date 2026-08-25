from jnotes2hinote import TESTED_HUAWEI_NOTES_VERSION, TESTED_JNOTES_VERSION, __version__
from jnotes2hinote.converter_v1_1_1 import __version__ as converter_core_version


def test_version_metadata():
    assert __version__ == "1.3.0"
    assert converter_core_version == "1.1.1"
    assert TESTED_JNOTES_VERSION == "3.2.3.2"
    assert TESTED_HUAWEI_NOTES_VERSION == "15.0.14.295"
