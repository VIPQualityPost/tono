import base64
import io

import numpy as np
from PIL import Image
from backend.data_types import DataField, ImageData, MeshModel
from backend.execution_context import active_node, execution_callbacks
from tests.node_tests._shared import make_field


def test_view3d_normalizes_small_physical_extents_for_display():
    from backend.nodes.view_3d import View3D

    data = np.linspace(0.0, 1.0, 64 * 64, dtype=np.float64).reshape(64, 64)
    field = DataField(data=data, xreal=1.0e-5, yreal=1.0e-5, si_unit_xy="m", si_unit_z="m")

    node = View3D()
    mesh, _ = node.render(field, colormap="auto", z_scale=1.0, resolution=64, make_solid=False)

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    spans = vertices.max(axis=0) - vertices.min(axis=0)

    assert np.isclose(spans[0], 1.0, atol=1e-6)
    assert np.isclose(spans[2], 1.0, atol=1e-6)
    assert spans[1] > 0.09


def test_view3d():
    from backend.nodes.view_3d import View3D

    node = View3D()
    field = make_field()

    captured = []
    mesh_callback = lambda nid, mesh: captured.append(mesh)

    preview_image = Image.new("RGB", (12, 10), (255, 0, 0))
    preview_buffer = io.BytesIO()
    preview_image.save(preview_buffer, format="PNG")
    viewport_snapshot = "data:image/png;base64," + base64.b64encode(preview_buffer.getvalue()).decode()

    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        result = node.render(
            field, colormap="viridis", z_scale=2.0, resolution=64, make_solid=False,
            camera_target_x=0.1, camera_target_y=-0.2, camera_target_z=0.3,
            viewport_snapshot=viewport_snapshot,
        )
    assert len(result) == 2
    assert isinstance(result[0], MeshModel)
    assert isinstance(result[1], ImageData)
    assert result[1].shape == (10, 12, 3)
    assert np.all(result[1][0, 0] == np.array([255, 0, 0], dtype=np.uint8))
    assert result[1].metadata["annotation_context"]["si_unit_xy"] == field.si_unit_xy
    assert result[1].metadata["viewport_camera"]["target_x"] == 0.1
    assert result[1].metadata["viewport_camera"]["target_y"] == -0.2
    assert result[1].metadata["viewport_camera"]["target_z"] == 0.3
    assert len(captured) == 1

    mesh = captured[0]
    assert "width" in mesh and "height" in mesh and "z_data" in mesh and "colors" in mesh
    assert mesh["z_scale"] == 0.2
    assert mesh["width"] <= 64
    assert mesh["height"] <= 64
    assert mesh["camera_target_x"] == 0.1
    assert mesh["z_min"] < mesh["z_max"]

    z_bytes = base64.b64decode(mesh["z_data"])
    assert len(z_bytes) == mesh["width"] * mesh["height"] * 4
    colors_bytes = base64.b64decode(mesh["colors"])
    assert len(colors_bytes) == mesh["width"] * mesh["height"] * 3

    big_field = make_field(shape=(256, 256))
    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        node.render(big_field, colormap="hot", z_scale=1.0, resolution=64, make_solid=False)
    assert captured[0]["width"] <= 64
    assert captured[0]["height"] <= 64

    mesh_field = make_field(data=np.zeros((64, 64), dtype=np.float64), xreal=2.0, yreal=3.0)
    map_field = make_field(data=np.tile(np.linspace(0.0, 1.0, 64, dtype=np.float64), (64, 1)), xreal=2.0, yreal=3.0)
    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        mapped_result = node.render(mesh_field, map_field=map_field, colormap="viridis", z_scale=1.0, resolution=32, make_solid=False)
    mapped_mesh = captured[0]
    assert mapped_mesh["x_range"] == [float(mesh_field.xoff), float(mesh_field.xoff + mesh_field.xreal)]
    assert np.isclose(mapped_mesh["surface_extent_x"] / mapped_mesh["surface_extent_y"], mesh_field.xreal / mesh_field.yreal)
    mapped_z = np.frombuffer(base64.b64decode(mapped_mesh["z_data"]), dtype=np.float32)
    assert np.allclose(mapped_z, 0.0)
    mapped_colors = np.frombuffer(base64.b64decode(mapped_mesh["colors"]), dtype=np.uint8)

    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        node.render(mesh_field, colormap="viridis", z_scale=1.0, resolution=32, make_solid=False)
    mesh_only_colors = np.frombuffer(base64.b64decode(captured[0]["colors"]), dtype=np.uint8)
    assert not np.array_equal(mapped_colors, mesh_only_colors)

    captured.clear()
    with execution_callbacks(mesh=mesh_callback), active_node("test"):
        solid_result = node.render(mesh_field, colormap="viridis", z_scale=1.0, resolution=16, make_solid=True)
    assert len(solid_result[0].vertices) > 16 * 16
    assert len(solid_result[0].faces) > (15 * 15 * 2)
    solid_payload = captured[0]
    assert solid_payload["make_solid"] is True
    assert "positions" in solid_payload
    assert "indices" in solid_payload
    assert "vertex_colors" in solid_payload
