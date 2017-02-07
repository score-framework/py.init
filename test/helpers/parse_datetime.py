import pytest
import datetime
from score.init import parse_datetime


def test_empty():
    with pytest.raises(ValueError):
        parse_datetime('')
    with pytest.raises(ValueError):
        parse_datetime('\n\n')
    with pytest.raises(ValueError):
        parse_datetime(' ')


def test_random_strings():
    with pytest.raises(ValueError):
        parse_datetime('foo')
    with pytest.raises(ValueError):
        parse_datetime('bar')


def test_zero_timestamp():
    assert parse_datetime('0') == datetime.datetime.fromtimestamp(0)


def test_valid_strings():
    assert parse_datetime('2011-02-03 12:34') == datetime.datetime(
        2011, 2, 3, 12, 34, 0, 0)
    assert parse_datetime('2011-02-03 12:34:56') == datetime.datetime(
        2011, 2, 3, 12, 34, 56, 0)
    assert parse_datetime('2011-02-03 12:34:56.100') == datetime.datetime(
        2011, 2, 3, 12, 34, 56, 100)
