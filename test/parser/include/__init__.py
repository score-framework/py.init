import os
from score.init import parse_config_file as parse, parse_list


ROOT = os.path.dirname(__file__)


def test_basic():
    conf = parse(os.path.join(ROOT, 'basic', 'main.conf'))
    assert 'foo' in conf
    assert 'bar' in conf['foo']
    assert conf['foo']['bar'] == '42'


def test_diff():
    conf = parse(os.path.join(ROOT, 'diff', 'main.conf'))
    assert 'score.init' in conf
    assert 'modules' in conf['score.init']
    print(parse_list(conf['score.init']['modules']))
    assert parse_list(conf['score.init']['modules']) == ['module1', 'module2']


def test_multidiff():
    conf = parse(os.path.join(ROOT, 'multidiff', 'main.conf'))
    assert 'score.init' in conf
    assert 'modules' in conf['score.init']
    print(parse_list(conf['score.init']['modules']))
    assert parse_list(conf['score.init']['modules']) == (
        ['module1', 'module2', 'module3'])


def test_based_on_and_include():
    conf = parse(os.path.join(ROOT, 'based_on_and_include', 'main.conf'))
    assert 'score.init' in conf
    assert 'modules' in conf['score.init']
    print(conf['score.init']['modules'])
    assert parse_list(conf['score.init']['modules']) == (
        ['module1', 'module2', 'module3'])
