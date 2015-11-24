from score.init import parse_list


def test_empty():
    assert parse_list('') == []


def test_double_newline():
    assert parse_list('\n\n') == []


def test_multi_newlines_value():
    assert parse_list('\n\nfoo\nbar\n\n') == ['foo', 'bar']
