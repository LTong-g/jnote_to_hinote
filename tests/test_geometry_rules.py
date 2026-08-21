from jnotes2hinote.converter_v1_0_0 import J_GEOMETRY_TO_HW_SHAPE


def test_device_tested_geometry_mapping():
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 0)] == 0
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 12)] == 16
    assert J_GEOMETRY_TO_HW_SHAPE[(6, 4)] == 10
    assert J_GEOMETRY_TO_HW_SHAPE[(7, 3)] == 7
    assert J_GEOMETRY_TO_HW_SHAPE[(7, 4)] == 10
