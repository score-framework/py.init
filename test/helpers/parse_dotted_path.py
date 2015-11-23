import pytest

from score.init import parse_dotted_path


def test_empty():
    with pytest.raises(ValueError):
        parse_dotted_path('')
    with pytest.raises(ValueError):
        parse_dotted_path('\n\n')


def test_not_valid():
    with pytest.raises(ValueError):
        parse_dotted_path('foo.bar.baz')


def test_self():
    assert parse_dotted_path('score.init.parse_dotted_path') == \
           parse_dotted_path
