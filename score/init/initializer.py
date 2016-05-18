# Copyright © 2015,2016 STRG.AT GmbH, Vienna, Austria
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
from inspect import signature, Parameter
import logging
import networkx as nx
import pkgutil
import sys
from .config import parse_list, parse_config_file
from .exceptions import InitializationError, ConfigurationError, DependencyLoop
import pip


log = logging.getLogger(__name__)


def init(confdict, *, overrides={}, init_logging=True):
    """
    This function automates the process of initializing all other modules. It
    will operate on given *confdict*, which is expected to be a 2-dimensional
    `dict` mapping names of modules to their respective :term:`confdicts
    <confdict>`. The recommended way of acquiring such a confdict is through
    :func:`.parse_config_file`, but any 2-dimensional `dict` is fine.

    The *confdict* should also contain the configuration for this module, which
    interprets the configuration key ``modules`` (which should be accessible as
    ``confdict['score.init']['modules']``):

    :confkey:`modules` :faint:`[optional]`
        A list of module names that shall be initialized. If this value is
        missing, you will end up with an empty :class:`.ConfiguredScore` object.

    The provided *overrides* will be integrated into the actual *confdict*
    prior to initialization. While the confdict is assumed to be retrieved from
    external resources (like a configuration file), this parameter aims to make
    programmatic adjustment of the configuration a bit easier.

    The final parameter *init_logging* makes sure python's own logging
    facility is initialized with the provided configuration, too.

    This function returns a :class:`.ConfiguredScore` object.
    """
    if init_logging and 'formatters' in confdict:
        import logging.config
        # TODO: the fileConfig() function below expects a RawConfigParser
        # instance; this function, however, has no such limitation -> convert
        # the confdict if it is not an object of that type
        logging.config.fileConfig(confdict, disable_existing_loggers=False)
    for section in overrides:
        if section not in confdict:
            confdict[section] = {}
        for key, value in overrides[section].items():
            confdict[section][key] = value
    try:
        paths = confdict['score.init']['autoimport']
    except KeyError:
        pass
    else:
        _perform_autoimport(parse_list(paths))
    return _init(confdict)


def _perform_autoimport(paths):
    if isinstance(paths, str):
        return _perform_autoimport([paths])
    for path in paths:
        __import__(path)
        module = sys.modules.get(path)
        try:
            module.__path__
        except AttributeError:
            # not a package
            continue
        for importer, modname, ispkg in pkgutil.walk_packages(module.__path__):
            if modname[0] == '_':
                continue
            if ispkg:
                _perform_autoimport('%s.%s' % (path, modname))
            else:
                __import__('%s.%s' % (path, modname))


def _init(confdict):
    try:
        modconf = parse_list(confdict['score.init']['modules'])
    except KeyError:
        # TODO: issue a warning through the warnings module
        return ConfiguredScore(confdict, dict(), dict())
    modules, dependency_aliases = _collect_modules(modconf)
    dependency_map = _collect_dependencies(modules, dependency_aliases)
    initialized = dict()
    sorted_aliases = _sort_modules(
        dependency_map, dependency_aliases, 'initialization')
    for alias in sorted_aliases:
        modname = modules[alias]
        module_dependencies = dependency_map[alias]
        modconf = {}
        if alias in confdict:
            modconf = confdict[alias]
        kwargs = {}
        for dep in module_dependencies:
            try:
                dependency_alias = dependency_aliases[alias][dep]
            except KeyError:
                kwargs[dep] = initialized[dep]
            else:
                kwargs[dep] = initialized[dependency_alias]
        log.debug('Initializing %s as %s' % (modname, alias))
        conf = importlib.import_module(modname).init(modconf, **kwargs)
        if not isinstance(conf, ConfiguredModule):
            raise InitializationError(
                __package__,
                '%s initializer did not return ConfiguredModule but %s' %
                (alias, repr(conf)))
        initialized[alias] = conf
    score = ConfiguredScore(confdict, initialized, dependency_aliases)
    score._finalize()
    return score


def init_from_file(file, *, overrides={}, init_logging=True):
    """
    Reads configuration from given *file* using
    :func:`.config.parse_config_file` and initializes score using :func:`.init`.
    See the documentation of :func:`.init` for a description of all keyword
    arguments.
    """
    return init(parse_config_file(file),
                overrides=overrides,
                init_logging=init_logging)


def init_logging_from_file(file):
    """
    Just the part of :func:`.init_from_file` that would initialize logging.
    """
    import logging.config
    confdict = parse_config_file(file)
    if 'formatters' in confdict:
        logging.config.fileConfig(confdict, disable_existing_loggers=False)


class ConfiguredModule(metaclass=abc.ABCMeta):
    """
    The return value of an ``init`` function. This class is abstract and
    modules must create sub-classes containing their respective configuration.
    """

    _finalized = False

    def __init__(self, module):
        self._module = module

    def _finalize(self):
        """
        The final function that will be called before the score initialization
        is considered complete. The parameter *score* contains the
        :class:`.ConfiguredScore` object.
        """
        pass

    @property
    def log(self):
        try:
            return self._log
        except AttributeError:
            self._log = logging.getLogger(self._module.__name__)
            return self._log


class ConfiguredScore(ConfiguredModule):
    """
    The return value of :func:`.init`. Contains the resulting
    :class:`.ConfiguredModule` of every initialized module as a member.
    """

    def __init__(self, confdict, modules, dependency_aliases):
        import score.init
        ConfiguredModule.__init__(self, score.init)
        self.conf = {}
        for section in confdict:
            self.conf[section] = dict(confdict[section].items())
        self._modules = modules
        self._module_dependency_aliases = dependency_aliases
        for alias, conf in modules.items():
            setattr(self, alias, conf)

    def _finalize(self):
        dependency_map = {}
        for alias, conf in self._modules.items():
            module_dependencies = []
            if hasattr(conf, '_finalize_dependencies'):
                if isinstance(conf._finalize_dependencies, dict):
                    module_dependencies = conf._finalize_dependencies
                else:
                    module_dependencies = \
                        [(dep, True) for dep in conf._finalize_dependencies]
            else:
                sig = signature(conf._finalize)
                for i, (param_name, param) in enumerate(sig.parameters.items()):
                    module_dependencies.append(
                        (param_name, param.default != Parameter.empty))
            dependency_map[alias] = module_dependencies
        modules = self._modules.copy()
        modules['score'] = self
        _remove_missing_optional_dependencies(
            modules, dependency_map, self._module_dependency_aliases)
        sorted_aliases = _sort_modules(
            dependency_map, self._module_dependency_aliases, 'finalization')
        for alias in sorted_aliases:
            if alias == 'score':
                continue
            kwargs = {}
            for dep in dependency_map[alias]:
                try:
                    depalias = self._module_dependency_aliases[alias][dep]
                except KeyError:
                    kwargs[dep] = modules[dep]
                else:
                    kwargs[dep] = modules[depalias]
            log.debug('Finalizing %s' % (alias))
            conf = modules[alias]
            conf._finalize(**kwargs)
            conf._finalized = True


def _collect_modules(modconf):
    modules = {}
    dependency_aliases = {}
    for line in modconf:
        parts = line.split(':', 2)
        if len(parts) == 2:
            module, alias = parts
        elif '.' in line:
            module = line
            alias = line[line.rindex('.') + 1:]
        else:
            module = alias = line
        if '(' in alias:
            assignments = alias[alias.index('('):].strip(' ()').split(',')
            alias = alias[:alias.index('(')].strip()
            if '(' in module:
                module = module[:module.index('(')].strip()
            dependency_aliases[alias] = {}
            for assignment in assignments:
                key, value = assignment.split('=')
                dependency_aliases[alias][key.strip()] = value.strip()
        modules[alias] = module
    return modules, dependency_aliases


def _import(module_name):
    """
    Will import a given python package, using pip to install it, if it could not
    be found.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        if e.name != module_name:
            raise
    log.warn("Module `%s' not found, installing" % module_name)
    if pip.main(['install', module_name]) == 0:
        try:
            return importlib.import_module(module_name)
        except ImportError as e:
            if e.name != module_name:
                raise
    return None


def _collect_dependencies(modules, dependency_aliases):
    missing = []
    dependency_map = dict()
    for alias, modname in modules.items():
        if modname == 'score.init':
            continue
        module = _import(modname)
        if not module:
            missing.append(modname)
            continue
        if not hasattr(module, 'init'):
            raise InitializationError(
                __package__,
                'Cannot initialize %s: it has no init() function' % modname)
        if not callable(module.init):
            raise InitializationError(
                __package__,
                'Cannot initialize %s: its init is not a function' % modname)
        module_dependencies = []
        sig = signature(module.init)
        for i, (param_name, param) in enumerate(sig.parameters.items()):
            if i == 0:
                # this should be the confdict
                continue
            module_dependencies.append(
                (param_name, param.default != Parameter.empty))
        dependency_map[alias] = module_dependencies
    if missing:
        raise ConfigurationError(
            __package__,
            'Could not find the following modules:\n - ' +
            '\n - '.join(missing))
    _remove_missing_optional_dependencies(
        modules, dependency_map, dependency_aliases)
    return dependency_map


def _remove_missing_optional_dependencies(modules, dependency_map,
                                          dependency_aliases):
    missing = {}
    for alias, module_dependencies in dependency_map.items():
        newdeps = []
        for dependency, is_optional in module_dependencies:
            try:
                dependency_alias = dependency_aliases[alias][dependency]
            except KeyError:
                dependency_alias = dependency
            if dependency_alias in modules:
                newdeps.append(dependency)
                continue
            if is_optional:
                continue
            if dependency not in missing:
                missing[dependency] = []
            missing[dependency].append(alias)
        dependency_map[alias] = newdeps
    if not missing:
        return
    msglist = []
    for dependency, dependants in missing.items():
        msglist.append('%s (required by %s)' %
                       (dependency, ', '.join(dependants)))
    raise ConfigurationError(
        __package__,
        'Could not find the following dependencies:\n - ' +
        '\n - '.join(msglist))


def _sort_modules(dependency_map, dependency_aliases, operation):
    sorted_ = []
    graph = nx.DiGraph()
    for alias, module_dependencies in dependency_map.items():
        if not module_dependencies:
            graph.add_edge(None, alias)
        for dep in module_dependencies:
            try:
                dep = dependency_aliases[alias][dep]
            except KeyError:
                pass
            graph.add_edge(dep, alias)
    for loop in nx.simple_cycles(graph):
        raise DependencyLoop(__package__, operation, loop)
    for alias in nx.topological_sort(graph):
        if alias is None:
            continue
        sorted_.append(alias)
    return sorted_
