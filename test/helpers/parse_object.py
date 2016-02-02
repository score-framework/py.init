import collections
import pytest

from score.init import parse_object


def test_empty():
    with pytest.raises(ValueError):
        parse_object({}, '')


def test_invalid_dotted_path():
    with pytest.raises(ValueError):
        parse_object({'foobar': 'bar'}, 'foobar')


def test_invalid_call():
    with pytest.raises(ValueError):
        parse_object({
            'foobar': 'score.init.parse_bool()'
        }, 'foobar', ('baz',))


def test_function_call():
    assert parse_object({
        'foobar': 'score.init.parse_bool()'
    }, 'foobar', ('1',)) == True


def test_class_call():
    ordered_dict = [('0', 'a'), ('1', 'b')]
    parsed_object = parse_object({
        'orderedlist': 'collections.OrderedDict'
    }, 'orderedlist', (ordered_dict,))
    assert isinstance(parsed_object, collections.OrderedDict)
    assert parsed_object == collections.OrderedDict(ordered_dict)
