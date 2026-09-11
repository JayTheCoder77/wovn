from demo.models import Item


def test_item():
    assert Item("x").name == "x"
