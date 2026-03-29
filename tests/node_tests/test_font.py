def test_font_node():
    from backend.nodes.font import Font
    from backend.data_types import CUSTOM_FILE_FONT, SYSTEM_DEFAULT_FONT

    node = Font()

    system_default, = node.build(SYSTEM_DEFAULT_FONT)
    assert system_default is None

    named, = node.build("Arial")
    assert named == {"family": "Arial", "path": ""}

    custom, = node.build(CUSTOM_FILE_FONT, "/tmp/example-font.ttf")
    assert custom == {"family": "", "path": "/tmp/example-font.ttf"}
