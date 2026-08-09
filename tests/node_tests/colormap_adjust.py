import numpy as np
from backend.data_types import DataField, datafield_to_uint8


def test_colormap_adjust():
    from backend.nodes.colormap_adjust import ColormapAdjust

    node = ColormapAdjust()
    field = DataField(data=np.array([[0.0, 0.25, 0.5, 0.75, 1.0]], dtype=np.float64), xreal=5.0, yreal=1.0, colormap="gray")

    adjusted, = node.process(field, offset=0.25, scale=0.5)
    assert np.array_equal(adjusted.data, field.data)
    assert adjusted.display_offset == 0.25
    assert adjusted.display_scale == 0.5
    assert adjusted.colormap == field.colormap

    rgb = datafield_to_uint8(adjusted, "gray")
    intensities = rgb[0, :, 0]
    assert intensities[0] == 0
    assert intensities[1] == 0
    assert 110 <= intensities[2] <= 145
    assert intensities[3] == 255
    assert intensities[4] == 255

    auto_like, = node.process(field, offset=0.0, scale=1.0)
    auto_rgb = datafield_to_uint8(auto_like, "gray")
    auto_intensities = auto_rgb[0, :, 0]
    assert auto_intensities[0] == 0
    assert auto_intensities[-1] == 255

    # "auto" keeps the field's current colormap; a preset replaces it
    kept, = node.process(field, colormap="auto", offset=0.0, scale=1.0)
    assert kept.colormap == field.colormap
    swapped, = node.process(field, colormap="hot", offset=0.0, scale=1.0)
    assert swapped.colormap == "hot"
    assert np.array_equal(swapped.data, field.data)
    assert swapped.display_offset == 0.0 and swapped.display_scale == 1.0

    # A connected Color Map socket overrides the dropdown
    from backend.nodes.colormap import ColorMap
    spec, = ColorMap().build(mode="preset", preset="magma")
    socket, = node.process(field, colormap="hot", colormap_map=spec, offset=0.0, scale=1.0)
    assert socket.colormap == spec

    try:
        node.process(field, offset=0.0, scale=0.0)
        raise AssertionError("Expected non-positive scale to raise ValueError")
    except ValueError:
        pass
