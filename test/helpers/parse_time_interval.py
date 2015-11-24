import pytest

from score.init import parse_time_interval


def test_empty():
    with pytest.raises(ValueError):
        parse_time_interval('')
    with pytest.raises(ValueError):
        parse_time_interval('\n\n')
    with pytest.raises(ValueError):
        parse_time_interval(None)
    with pytest.raises(ValueError):
        parse_time_interval(False)


def test_invalid_value():
    with pytest.raises(ValueError):
        parse_time_interval('1 year')


def test_valid_value():
    assert parse_time_interval('5 days') == 5 * 60 * 60 * 24
    assert parse_time_interval('3 millisecond') == 3 * 0.001
    assert parse_time_interval('9\ns') == 9
    assert parse_time_interval('6\n\nmin') == 6 * 60
