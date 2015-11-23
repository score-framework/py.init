import pytest
from score.init import (
    init, ConfiguredScore, ConfiguredModule, InitializationError)


def test_empty():
    conf = init({})
    assert isinstance(conf, ConfiguredScore)
    assert isinstance(conf._modules, dict)
    assert not conf._modules


def test_bogus_init_return():
    with pytest.raises(InitializationError):
        init({
            'score.init': {
                'modules': 'test.initializer.bogus_init_return'
            }
        })


def test_single_module_success():
    conf = init({
        'score.init': {
            'modules': 'test.initializer.single_module_success'
        }
    })
    assert isinstance(conf, ConfiguredScore)
    assert isinstance(conf._modules, dict)
    assert len(conf._modules) == 1
    assert 'test.initializer.single_module_success' in conf._modules
    mod = conf._modules['test.initializer.single_module_success']
    assert isinstance(mod, ConfiguredModule)
    assert mod._module == 'test.initializer.single_module_success'


def test_dependency_success():
    conf = init({
        'score.init': {
            'modules':
                'test.initializer.dependency_success.pkg1\n'
                'test.initializer.dependency_success.pkg2'
        }
    })
    assert isinstance(conf, ConfiguredScore)
    assert isinstance(conf._modules, dict)
    assert len(conf._modules) == 2
    assert 'test.initializer.dependency_success.pkg1' in conf._modules
    assert 'test.initializer.dependency_success.pkg2' in conf._modules
    mod1 = conf._modules['test.initializer.dependency_success.pkg1']
    mod2 = conf._modules['test.initializer.dependency_success.pkg2']
    assert isinstance(mod1, ConfiguredModule)
    assert isinstance(mod2, ConfiguredModule)
    assert mod1._module == 'test.initializer.dependency_success.pkg1'
    assert mod2._module == 'test.initializer.dependency_success.pkg2'


def test_missing_dependency():
    with pytest.raises(InitializationError):
        init({
            'score.init': {
                'modules': 'test.initializer.missing_dependency'
            }
        })
