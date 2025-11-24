from app.service import add_numbers
import pytest


def test_add_numbers():
    assert add_numbers(2, 3) == 5


def test_add_numbers_error():

    with pytest.raises(ValueError):
        add_numbers(None, 5)
