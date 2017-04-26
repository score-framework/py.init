from score.init.initializer import _sort_modules
import pytest
from score.init import DependencyLoop


def test_empty():
    result = _sort_modules(dict(), dict(), 'testing')
    assert not result


def test_valid():
    result = _sort_modules({
        'a': ['b', 'c', 'd'],
        'b': ['c', 'e'],
        'e': ['c'],
        'c': ['d'],
        'd': [],
    }, dict(), 'testing')
    assert result
    assert result.index('a') > result.index('b')
    assert result.index('a') > result.index('c')
    assert result.index('a') > result.index('d')
    assert result.index('b') > result.index('c')
    assert result.index('b') > result.index('e')
    assert result.index('e') > result.index('c')
    assert result.index('c') > result.index('d')


def test_no_deps():
    result = _sort_modules({
        'a': [],
        'b': [],
        'e': [],
        'c': [],
        'd': [],
    }, dict(), 'testing')
    assert result
    assert 'a' in result
    assert 'b' in result
    assert 'c' in result
    assert 'd' in result
    assert 'e' in result


def test_simplest_cycle():
    with pytest.raises(DependencyLoop) as excinfo:
        _sort_modules({'a': ['b'], 'b': ['a']}, dict(), None)
    exc = excinfo.value
    assert set(exc.loop) == {'a', 'b'}


def test_longer_cycle():
    with pytest.raises(DependencyLoop) as excinfo:
        _sort_modules({'a': ['b'], 'b': ['c'], 'c': ['a']}, dict(), None)
    exc = excinfo.value
    assert set(exc.loop) == {'a', 'b', 'c'}
