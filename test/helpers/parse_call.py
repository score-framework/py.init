import pytest

from score.init import parse_call


def test_empty():
    with pytest.raises(ValueError):
        parse_call('')
    with pytest.raises(ValueError):
        parse_call('\n\n')


def test_invalid_function():
    with pytest.raises(ValueError):
        parse_call('foo.bar()')


def test_valid_parse_bool():
    assert parse_call('score.init.parse_bool', ('True',)) == True
