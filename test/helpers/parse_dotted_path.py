import pytest

from score.init import parse_dotted_path


def test_empty():
    with pytest.raises(ValueError):
        parse_dotted_path('')
    with pytest.raises(ValueError):
        parse_dotted_path('\n\n')


def test_invalid_value():
    with pytest.raises(ValueError):
        parse_dotted_path('foo.bar.baz')
    with pytest.raises(ValueError):
        parse_dotted_path('foobar')


def test_valid_self():
    assert parse_dotted_path('score.init.parse_dotted_path') == \
           parse_dotted_path
