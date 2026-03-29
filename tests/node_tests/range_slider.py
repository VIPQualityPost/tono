def test_range_slider():
    from backend.nodes.range_slider import RangeSlider

    node = RangeSlider()

    result = node.process(min_value=0.0, max_value=10.0, value=3.25)
    assert result == (3.25,)

    result_high = node.process(min_value=0.0, max_value=10.0, value=12.0)
    assert result_high == (10.0,)

    result_reversed = node.process(min_value=5.0, max_value=-1.0, value=4.0)
    assert result_reversed == (4.0,)

    result_fixed = node.process(min_value=2.5, max_value=2.5, value=99.0)
    assert result_fixed == (2.5,)
