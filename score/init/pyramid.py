# Copyright © 2015 STRG.AT GmbH, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in the
# file named COPYING.LESSER.txt.
#
# The SCORE Framework and all its parts are distributed without any WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
# License.
#
# If you have not received a copy of the GNU Lesser General Public License see
# http://www.gnu.org/licenses/.
#
# The License-Agreement realised between you as Licensee and STRG.AT GmbH as
# Licenser including the issue of its valid conclusion and its pre- and
# post-contractual effects is governed by the laws of Austria. Any disputes
# concerning this License-Agreement including the issue of its valid conclusion
# and its pre- and post-contractual effects are exclusively decided by the
# competent court, in whose district STRG.AT GmbH has its registered seat, at
# the discretion of STRG.AT GmbH also the competent court, in whose district the
# Licensee has his registered seat, an establishment or assets.

"""
This package :ref:`integrates <framework_integration>` the module with
pyramid.
"""

import configparser
from importlib import import_module
from inspect import signature
import logging
import os
from pyramid.config import Configurator
import re
from setuptools import find_packages


log = logging.getLogger(__name__)


def init(confdict, configurator):
    """
    Does the same as :func:`score.init.init`, but will first search for a
    sub-package called ``pyramid`` and test if it has its own
    ``init``-function. If yes, it will call that one instead of the ``init``-
    function in the module's root.

    This initializer will also register its return value as a :ref:`request
    property <pyramid:adding_request_method>` called ``score``.
    """
    def initializer(module, modconf, kwargs):
        try:
            pyramid = import_module('%s.pyramid' % module.__name__)
        except ImportError:
            pass
        else:
            if hasattr(pyramid, 'init'):
                log.debug('Initializing %s [pyramid]' % module.__name__)
                return pyramid.init(modconf, configurator, **kwargs)
        log.debug('Initializing %s' % module.__name__)
        return module.init(modconf, **kwargs)
    from score.init import _init
    conf = _init(_get_modules, confdict, initializer)
    configurator.add_request_method(lambda _: conf, 'score', property=True)
    return conf


def init_from_file(file, overrides={}, modules=None,
                   init_logging=True, *, pyramid_kwargs={}):
    """
    Does the same as :func:`score.init.init_from_file`, but will use this
    file's :func:`.init` to initialize everything, once the :term:`confdict`
    was initialized.

    This function returns **two** values: A
    :class:`pyramid.config.Configurator` object, followed by the usual return
    value of :func:`score.init.init_from_file`.

    The additional `dict` parameter *pyramid_kwargs* will be passed as keyword
    arguments to the Configurator object.
    """
    settings = configparser.ConfigParser()
    settings['DEFAULT']['here'] = os.path.dirname(file)
    if not settings['DEFAULT']['here']:
        settings['DEFAULT']['here'] = '.'
    settings.read(file)
    configurator = Configurator(settings=settings['app:main'], **pyramid_kwargs)
    import score
    return configurator, \
        score.init._init_from_file(
            file, overrides, modules, init_logging,
            init=lambda settings: init(settings, configurator))


def _get_modules(filter_=None):
    import score
    dependencyre = re.compile(r'^(.*)_conf$')
    modules = dict()
    for path in score.__path__:
        for modname in find_packages(path):
            if modname.startswith('init'):
                continue
            fullname = 'score.%s' % modname
            if filter_ and fullname not in filter_:
                continue
            module = import_module(fullname)
            if not hasattr(module, 'init'):
                continue
            try:
                pyramid = import_module('%s.pyramid' % fullname)
                sig = signature(pyramid.init)
            except (ImportError, AttributeError):
                sig = signature(module.init)
            dependencies = []
            for paramname in sig.parameters:
                match = dependencyre.match(paramname)
                if match:
                    dependencies.append('score.%s' % match.group(1))
            modules[module] = dependencies
    return modules
