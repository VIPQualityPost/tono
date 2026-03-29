import numpy as np
from backend.data_types import DataField, ImageData, datafield_to_uint8, render_datafield_preview
from backend.execution_context import active_node, execution_callbacks


def test_annotations():
    from backend.nodes.annotations import Annotations
    from backend.nodes.font import Font

    node = Annotations()
    font_node = Font()
    annotation_input = Annotations.INPUT_TYPES()["required"]["input"]
    assert annotation_input[0] == "ANNOTATION_SOURCE"
    assert annotation_input[1]["accepted_types"] == ["DATA_FIELD", "IMAGE"]

    warnings = []
    field = DataField(
        data=np.linspace(0.0, 1.0, 64 * 64, dtype=np.float64).reshape(64, 64),
        xreal=1e-6, yreal=1e-6, si_unit_xy="m", si_unit_z="V", colormap="viridis",
    )

    base = datafield_to_uint8(field, "viridis")
    plain_preview = render_datafield_preview(field, "viridis")
    assert np.array_equal(plain_preview, base)

    with execution_callbacks(warning=lambda nid, msg: warnings.append(msg)), active_node("test"):
        plain_field, = node.render(input=field, colormap="auto", show_scale_bar=False, show_color_map=False)
        assert isinstance(plain_field, DataField)
        assert np.array_equal(plain_field.data, field.data)
        assert plain_field.colormap == "viridis"
        assert plain_field.overlays[-1]["kind"] == "annotation"
        plain = render_datafield_preview(plain_field, plain_field.colormap)
        assert plain.shape == base.shape
        assert np.array_equal(plain, base)

        with_scale_field, = node.render(input=field, colormap="auto", show_scale_bar=True, show_color_map=False)
        with_scale = render_datafield_preview(with_scale_field, with_scale_field.colormap)
        assert with_scale.shape == base.shape
        assert not np.array_equal(with_scale, base)

        with_legend_field, = node.render(input=field, colormap="auto", show_scale_bar=False, show_color_map=True)
        with_legend = render_datafield_preview(with_legend_field, with_legend_field.colormap)
        assert with_legend.shape[0] == base.shape[0]
        assert with_legend.shape[1] > base.shape[1]
        assert with_legend.shape[2] == 3

        larger_legend_field, = node.render(input=field, colormap="auto", show_scale_bar=False, show_color_map=True, text_size=28.0)
        larger_legend_text = render_datafield_preview(larger_legend_field, larger_legend_field.colormap)
        assert larger_legend_text.shape[0] == with_legend.shape[0]
        assert larger_legend_text.shape[1] > with_legend.shape[1]
        assert not np.array_equal(larger_legend_text, with_legend)

        annotation_font, = font_node.build("Arial")
        with_font_field, = node.render(input=field, colormap="auto", show_scale_bar=False, show_color_map=True, text_size=28.0, font=annotation_font)
        assert with_font_field.overlays[-1]["font"] == {"family": "Arial", "path": ""}
        with_font = render_datafield_preview(with_font_field, with_font_field.colormap)
        assert with_font.shape[1] > with_legend.shape[1]

        with_both_field, = node.render(input=field, colormap="auto", show_scale_bar=True, show_color_map=True)
        with_both = render_datafield_preview(with_both_field, with_both_field.colormap)
        assert with_both.shape == with_legend.shape
        assert not np.array_equal(with_both[:, :base.shape[1]], base)

        viewport_image = ImageData(
            np.zeros((48, 64, 3), dtype=np.uint8),
            metadata={"annotation_context": {"xreal": 2e-6, "si_unit_xy": "m", "legend_min": -1.5, "legend_mid": 0.0, "legend_max": 1.5, "legend_unit": "V", "colormap": "viridis"}},
        )
        annotated_image, = node.render(input=viewport_image, colormap="auto", show_scale_bar=True, show_color_map=True, text_size=18.0)
        assert isinstance(annotated_image, ImageData)
        assert annotated_image.shape[0] == viewport_image.shape[0]
        assert annotated_image.shape[1] > viewport_image.shape[1]
        assert annotated_image.metadata["annotation_context"]["legend_unit"] == "V"
        assert warnings == []

        plain_image = ImageData(np.zeros((32, 40, 3), dtype=np.uint8))
        passthrough_image, = node.render(input=plain_image, colormap="auto", show_scale_bar=True, show_color_map=True, text_size=18.0)
        assert isinstance(passthrough_image, ImageData)
        assert passthrough_image.shape == plain_image.shape
        assert np.array_equal(np.asarray(passthrough_image), np.asarray(plain_image))
        assert len(warnings) == 1
        assert "no scale metadata" in warnings[0]
