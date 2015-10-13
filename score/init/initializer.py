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

import abc
import importlib
from inspect import signature
import logging
import networkx as nx
import re
from .config import parse_list, parse_config_file
from .exceptions import ConfigurationError, DependencyLoop


log = logging.getLogger(__name__)


def init(confdict):
    """
    The only module initializer you will ever need. This function automates
    the process of initializing all other modules. It will scan the
    :term:`namespace package` ``score`` for packages that contain an ``init``-
    function. It will then call the ``init`` functions one by one, respecting
    their dependencies.

    The *confdict* to this function needs to be a 2-dimensional `dict` mapping
    names of modules to their respective :term:`confdicts <confdict>`. This
    can be an instance of :class:`configparser.ConfigParser`.

    This function also accepts the following configuration keys (which need to
    be accessible as ``confdict['score.init']['configuration-key']``):

    :confkey:`modules` :faint:`[optional]`
        A list of module names that shall be initialized. If this value is
        missing, *all* modules in the score namespace will be initialized.

    This function returns a :class:`.ConfiguredScore` object.
    """
    def initializer(module, modconf, kwargs):
        log.debug('Initializing %s' % module.__name__)
        return module.init(modconf, **kwargs)
    return _init(_get_modules, confdict, initializer)


class ConfiguredScore:
    """
    The return value of :func:`.init`. Contains the resulting
    :class:`.ConfiguredModule` of every initialized module as a member. It is
    also possible to access configured modules as a dictionary value:

    >>> conf.ctx == conf['score.ctx']
    """

    def __init__(self, confdict, modules):
        self.conf = {}
        for section in confdict:
            self.conf[section] = dict(confdict[section].items())
        self._modules = modules
        for module, conf in modules.items():
            setattr(self, module[6:], conf)

    def __hasitem__(self, module):
        return module in self._modules

    def __getitem__(self, module):
        return self._modules[module]


class ConfiguredModule(metaclass=abc.ABCMeta):
    """
    The return value of an ``init`` function. This class is abstract and
    modules must create sub-classes containing their respective configuration.
    """

    def __init__(self, module):
        self._module = module

    @property
    def log(self):
        try:
            return self._log
        except AttributeError:
            self._log = logging.getLogger(self._module)
            return self._log


def init_from_file(file, overrides={}, modules=None, init_logging=True):
    """
    Reads configuration from given *file* using
    :func:`.config.parse_config_file` and initializes score using :func:`.init`.

    The provided *overrides* will be integrated into the configuration file
    prior to initialization. It is possible to enforce certain configuration
    values this way.

    The parameter *modules* can contain a list of module names — but also a
    single module name — which should be initialized. The exact same behaviour
    can be achieved by providing the appropriate *overrides*, but this
    convenience parameter was added since this was such a common use case.

    The final parameter *init_logging* makes sure python's own logging
    facility is initialized with the config *file*, too.
    """
    return _init_from_file(parse_config_file(file),
                           overrides, modules, init_logging, init)


def _init_from_file(settings, overrides, modules, init_logging, init):
    """
    Helper function for harmonizing the default init process and the one
    involving pyramid. The parameters are that of :func:`.init_from_file`, the
    only new parameter *init* is the callback to use for initializing all
    modules, once the :term:`confdict` was initialized.
    """
    if init_logging:
        import logging.config
        logging.config.fileConfig(settings)
    for section in overrides:
        if section not in settings:
            settings[section] = {}
        for key, value in overrides[section].items():
            settings[section][key] = value
    if modules:
        if isinstance(modules, str):
            modules = (modules,)
        settings['score.init']['modules'] = '\n'.join(modules)
    return init(settings)


def _get_modules(filter_=None):
    import score
    dependencyre = re.compile(r'^(.*)_conf$')
    modules = dict()
    for path in score.__path__:
        from setuptools import find_packages
        for modname in find_packages(path):
            if modname.startswith('init'):
                continue
            fullname = 'score.%s' % modname
            if filter_ and fullname not in filter_:
                continue
            module = importlib.import_module(fullname)
            if not hasattr(module, 'init'):
                continue
            dependencies = []
            sig = signature(module.init)
            for paramname in sig.parameters:
                match = dependencyre.match(paramname)
                if match:
                    dependencies.append('score.%s' % match.group(1))
            modules[module] = dependencies
    return modules


def _init(load_modules, confdict, init_module):
    filter_ = None
    if 'score.init' in confdict and 'modules' in confdict['score.init']:
        filter_ = parse_list(confdict['score.init']['modules'])
    modules = load_modules(filter_)
    if filter_:
        names = set(map(lambda m: m.__name__, modules))
        missing = set(filter_) - names
        if missing:
            raise ConfigurationError(
                __package__,
                'Could not find the following modules:\n - ' +
                '\n - '.join(missing))
    graph = nx.DiGraph()
    for module, dependencies in modules.items():
        if not dependencies:
            graph.add_edge(None, module.__name__)
        for dep in dependencies:
            graph.add_edge(dep, module.__name__)
    for loop in nx.simple_cycles(graph):
        raise DependencyLoop(loop)
    initialized = dict()
    for mod in nx.topological_sort(graph):
        try:
            module = next(m for m in modules if m.__name__ == mod)
        except StopIteration:
            # module listed as dependency, but it's not in the list of modules
            # to initialize. we'll just skip it and let the depending module's
            # init function fail if the dependency was not optional.
            continue
        dependencies = modules[module]
        modconf = {}
        if module.__name__ in confdict:
            modconf = confdict[module.__name__]
        kwargs = {}
        for dep in dependencies:
            if dep not in initialized:
                # let's hope this is an optional dependency
                continue
            kwargs[dep[6:] + '_conf'] = initialized[dep]
        initialized[module.__name__] = init_module(module, modconf, kwargs)
    conf = ConfiguredScore(confdict, initialized)
    if hasattr(conf, 'ctx'):
        conf.ctx.register('score', lambda _: conf)
    return conf
