import os
import pytest

from score.init import init_cache_folder


def test_empty():
    with pytest.raises(ValueError):
        init_cache_folder({}, '')


def test_valid_folder_no_autopurge():
    assert os.access(init_cache_folder({
        'tmp': '/tmp/score_test'
    }, 'tmp'), os.W_OK)


def test_valid_folder_autopurge():
    assert os.access(init_cache_folder({
        'tmp': '/tmp/score_test'
    }, 'tmp', True), os.W_OK)

