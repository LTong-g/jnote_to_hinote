from jnotes2hinote import TESTED_HUAWEI_NOTES_VERSION, TESTED_JNOTES_VERSION, __version__


def test_version_metadata():
    assert __version__ == "1.1.0"
    assert TESTED_JNOTES_VERSION == "3.2.3.2"
    assert TESTED_HUAWEI_NOTES_VERSION == "15.0.14.295"
