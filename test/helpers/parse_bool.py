import pytest

from score.init import parse_bool


def test_empty():
    with pytest.raises(ValueError):
        parse_bool('')
    with pytest.raises(ValueError):
        parse_bool('\n\n')


def test_invalid_value():
    with pytest.raises(ValueError):
        parse_bool('foobar')


def test_valid_true():
    assert parse_bool('True') is True
    assert parse_bool('true') is True
    assert parse_bool('1') is True
    assert parse_bool(1) is True


def test_valid_false():
    assert parse_bool('False') is False
    assert parse_bool('false') is False
    assert parse_bool(0) is False
