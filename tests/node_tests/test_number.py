def test_number():
    from backend.nodes.number import Number

    node = Number()

    result = node.process(value=1.25)
    assert result == (1.25,)

    result_neg = node.process(value=-3.5)
    assert result_neg == (-3.5,)
