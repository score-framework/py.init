from score.init import extract_conf


def test_empty():
    assert extract_conf({}, '') == {}
    assert extract_conf({'foo.bar': 'baz'}, 'baz.') == {}


def test_valid_value():
    assert extract_conf({'foo.bar': 'baz'}, 'foo.') == {'bar': 'baz'}
