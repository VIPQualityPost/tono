def test_coordinate():
    from backend.nodes.coordinate import Coordinate

    node = Coordinate()

    result = node.process(x=0.3, y=0.7)
    assert len(result) == 1
    assert result[0] == (0.3, 0.7)

    result_zero = node.process(x=0.0, y=0.0)
    assert result_zero[0] == (0.0, 0.0)

    result_one = node.process(x=1.0, y=1.0)
    assert result_one[0] == (1.0, 1.0)
