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
                'modules': 'test.bogus_init_return'
            }
        })


def test_single_module_success():
    conf = init({
        'score.init': {
            'modules': 'test.single_module_success'
        }
    })
    assert isinstance(conf, ConfiguredScore)
    assert isinstance(conf._modules, dict)
    assert conf._modules
    assert 'test.single_module_success' in conf._modules
    modconf = conf._modules['test.single_module_success']
    assert isinstance(modconf, ConfiguredModule)
    assert modconf._module == 'test.single_module_success'
