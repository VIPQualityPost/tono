import json


def test_color_map_node():
    from backend.nodes.colormap import ColorMap

    node = ColorMap()

    preset, = node.build(mode="preset", preset="magma", stops_json="[]")
    assert preset["mode"] == "preset"
    assert preset["preset"] == "magma"

    custom, = node.build(
        mode="custom",
        preset="viridis",
        stops_json=json.dumps([
            {"position": 0.0, "color": "#000000"},
            {"position": 0.4, "color": "#00ff00"},
            {"position": 1.0, "color": "#ffffff"},
        ]),
    )
    assert custom["mode"] == "custom"
    assert custom["stops"][0]["position"] == 0.0
    assert custom["stops"][-1]["position"] == 1.0
    assert len(custom["stops"]) == 3
