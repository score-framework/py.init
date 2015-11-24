import pytest

from score.init import parse_host_port


def test_empty():
    with pytest.raises(ValueError):
        parse_host_port('')
    with pytest.raises(ValueError):
        parse_host_port('\n\n')
    with pytest.raises(ValueError):
        parse_host_port('\n\n', None)
    with pytest.raises(ValueError):
        parse_host_port('', '\n')


def test_not_valid():
    with pytest.raises(ValueError):
        parse_host_port('localhost')


def test_nofallback():
    assert parse_host_port('localhost:80') == ('localhost', 80)


def test_fallback():
    assert parse_host_port('localhost', '127.0.0.1:8080') == ('localhost', 8080)
