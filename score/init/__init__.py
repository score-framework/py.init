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
import configparser
import importlib
from inspect import signature
import logging
import networkx as nx
import re
import os
import sys


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


def init_from_file(file, overrides={}, modules=None, init_logging=True):
    """
    Reads configuration from given *file* and initializes score
    using :func:`.init`.

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
    return _init_from_file(file, overrides, modules, init_logging, init)


def _init_from_file(file, overrides, modules, init_logging, init):
    """
    Helper function for harmonizing the default init process and the one
    involving pyramid. The parameters are that of :func:`.init_from_file`, the
    only new parameter *init* is the callback to use for initializing all
    modules, once the :term:`confdict` was initialized.
    """
    if init_logging:
        import logging.config
        logging.config.fileConfig(file)
    settings = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation())
    settings['DEFAULT']['here'] = os.path.dirname(file)
    if not settings['DEFAULT']['here']:
        settings['DEFAULT']['here'] = '.'
    settings.read(file)
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


def _calling_module():
    file2module = dict((v.__file__, v)
                       for k, v in sys.modules.items()
                       if hasattr(v, '__file__'))
    frame = sys._getframe().f_back.f_back
    file = frame.f_code.co_filename
    while file in file2module and \
            file2module[file].__name__.startswith('score.init.'):
        frame = frame.f_back
        if frame is None:
            return None
        file = frame.f_code.co_filename
    return file2module[file]


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


class InitializationError(Exception):
    """
    Base class for exceptions to raise, in case the initialization of a module
    fails.
    """

    def __init__(self, module, *args, **kwargs):
        self.module = module
        Exception.__init__(self, *args, **kwargs)


class DependencyLoop(InitializationError):
    """
    Thrown if a dependency loop was detected during a call to :func:`.init`.
    """

    def __init__(self, *args, **kwargs):
        # skip parent constructor
        Exception.__init__(self, *args, **kwargs)


class ConfigurationError(InitializationError):
    """
    The exception to raise when the initialization of a module failed due to a
    bogus configuration.
    """


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


def parse_bool(value):
    """
    Converts a string value to a boolean. This function will accept the same
    strings as the default configuration of python's :mod:`configparser` module.
    """
    if not isinstance(value, str):
        return bool(value)
    try:
        return configparser.ConfigParser.BOOLEAN_STATES[value.lower()]
    except KeyError:
        raise ConfigurationError(
            _calling_module(),
            'Value "%s" does not describe a boolean' % value)


def parse_time_interval(value):
    """
    Converts a human readable time interval string to a float in seconds.

    >>> parse_time_interval('3s')
    3.0
    >>> parse_time_interval('5 milliseconds')
    0.005
    >>> parse_time_interval('1 minute')
    60.0
    >>> parse_time_interval('2 hours')
    7200.0
    >>> parse_time_interval('365days')
    31536000.0
    """
    multiplier = {
        'ms': 0.001,
        'millisecond': 0.001,
        'milliseconds': 0.001,
        's': 1,
        'second': 1,
        'seconds': 1,
        'm': 60,
        'minute': 60,
        'minutes': 60,
        'h': 60*60,
        'hour': 60*60,
        'hours': 60*60,
        'd': 60*60*24,
        'day': 60*60*24,
        'days': 60*60*24,
    }
    config_error = ConfigurationError(
        _calling_module(),
        'Value "%s" does not describe a valid time interval' % value
    )
    try:
        matches = re.search('^\s*(\d+)\s*([a-z]+)\s*$', value.lower())
        return float(matches.group(1)) * multiplier[matches.group(2)]
    except AttributeError:
        raise config_error
    except KeyError:
        raise config_error


def parse_dotted_path(value):
    """
    Converts a dotted python path to the denoted object. The following will
    return the :func:`randint` function from the :mod:`random` module, for
    example::

        parse_dotted_path('random.randint')
    """
    if not isinstance(value, str):
        return value
    module, classname = value.rsplit('.', 1)
    return getattr(importlib.import_module(module), classname)


def parse_call(value, args=tuple(), kwargs={}):
    """
    Parses a string containing a function call or an object construction. The
    given *value* is expected to call the path to a python object (as
    interpreted by :func:`parse_dotted_path`), followed by an opening
    parenthesis, arguments and keywords separated by commas, and a closing
    parenthesis.

    This will look a lot like real python code, but the actual invocation will
    be enriched with the *args* and *kwargs* given to this function. If this
    function is invoked like the following ...

    >>> parse_call('foo.Test(3, ovr=b)', (1, 2), kwargs={'ovr': 'c', 'bar': 4})

    ... it will invoke and return the result of the following code:

    >>> foo.Test(1, 2, '3', ovr='b', bar=4)

    Note that all arguments (and keyword arguments) in the *value* string will
    be passed as strings!
    """
    if '(' not in value:
        cls = value
    else:
        args = list(args)
        kwargs = kwargs.copy()
        cls, argstr = value.rstrip(')').split('(')
        if argstr:
            for argstr in map(lambda s: s.strip(), argstr.split(',')):
                if '=' in argstr:
                    k, v = argstr.split('=')
                    kwargs[k] = v
                else:
                    args.append(argstr)
    cls = parse_dotted_path(cls)
    return cls(*args, **kwargs)


def parse_list(value):
    """
    Converts a string value to a corresponding list of strings. Substrings are
    assumed to be delimited by newline characters.
    """
    if isinstance(value, list):
        return value
    parts = value.split('\n')
    if not parts[0].strip():
        del parts[0]
    return [part.strip() for part in parts]


def parse_host_port(value, fallback=None):
    """
    Extracts a host and a port definition from given *value*. Valid values are:

    - hostname
    - hostname:port

    The return value will be a 2-tuple containing the hostname and the port.
    If the given *value* is empty, or contains no port definition, these values
    can be dropped in from a give *fallback* value, which can have the same
    format as defined for the first parameter (a `str`), or the same format as
    the return value (a `tuple`).

    The following call would return ``('example.com', 5109)``:

    >>> parse_host_port('example.com', 'localhost:5109')
    """
    if not value:
        if isinstance(fallback, str):
            fallback = parse_host_port(fallback)
        return fallback
    parts = value.split(':')
    if len(parts) == 1:
        if isinstance(fallback, str):
            fallback = parse_host_port(fallback)
        if fallback and len(fallback) > 1:
            parts.append(fallback[1])
    return (parts[0], int(parts[1]))


def extract_conf(configuration, prefix, defaults=dict()):
    """
    This function can be used to extract :term:`confdict` values with a given
    *prefix*. When called with the *prefix* ``spam.``, for example, it will
    return all values in the *confdict* that start with that string.

    If a *defaults* `dict` is present, it will be used as the base for the
    return value.

    >>> defaults = {
    ...   'eggs': 'Spam and eggs',
    ... }
    >>> conf = {
    ...   'spam.eggs': 'Eggs with Spam!',
    ...   'spam.bacon.eggs': 'Spam, bacon and eggs',
    ...   'bacon.spam': 'Bacon and Spam'
    ... }
    >>> extract_conf(conf, 'spam.', defaults)
    {'eggs': 'Eggs with Spam!', 'bacon.eggs': 'Spam, bacon and eggs'}
    """
    conf = dict(defaults.items())
    for key, value in configuration.items():
        if key.startswith(prefix):
            conf[key[len(prefix):]] = value
    return conf


def init_object(confdict, key, args=tuple(), kwargs={}):
    """
    Creates an object from a :term:`confdict`. This function either expects a
    string accepted by :func:`parse_call`, or a more verbose and flexible
    configuration. If the given value in the *confdict* contains an opening
    parenthesis, it is assumed to be in the terse format, in which case it will
    be parsed by parse_call.

    In any other case, the function assumes that the *confdict* contains a class
    name under the specified *key*, which will be parsed using
    :func:`parse_dotted_path`. The function will then extract all other keys
    from *confdict* that start with the same *key*, process them and pass the
    resulting `dict` to the class's contructor as keyword arguments. It is
    possible to provide additional arguments to the constructor as *args*.

    The aforementioned processing phase will replace all multi-line values with
    arrays using :func:`.parse_list`.

    For example, the following configuration::

        versionmanager = score.webassets.versioning.Mercurial
        versionmanager.folder = /usr/share/versionmanager
        versionmanager.repos =
            /var/www/project
            /var/www/library1
            /var/www/library2

    will invoke the constructor like this::

        Mercurial(folder="/usr/share/versionmanager", repos=[
            "/var/www/project",
            "/var/www/library1",
            "/var/www/library2",
        ])
    """
    if '(' in confdict[key]:
        return parse_call(confdict[key], args, kwargs)
    cls = parse_dotted_path(confdict[key])
    kwargs = kwargs.copy()
    for key, value in extract_conf(confdict, key + '.').items():
        if '\n' in value:
            value = parse_list(value)
        kwargs[key] = value
    return cls(*args, **kwargs)


def init_cache_folder(confdict, key, autopurge=False):
    """
    Initializes the cache folder described in the :term:`confdict` with the
    given *key*. This function will make sure that the folder exists and is
    writable and return its absolute path.

    If *autopurge* is `True`, it will further write the whole *confdict* into a
    file called :file:`__conf__` in the folder to detect changes to the
    *confdict*. If the function thus detects a confdict change during the next
    initialization, it will delete the contents of the folder, assuming that
    its contents have become obsolete.
    """
    folder = confdict[key]
    os.makedirs(folder, exist_ok=True)
    folder = os.path.realpath(folder)
    if not os.access(folder, os.R_OK | os.W_OK):
        raise ConfigurationError(_calling_module(),
                                 'Configured cache folder is not writable')
    if not autopurge:
        return folder
    confdict = dict(confdict.items())
    del confdict[key]
    confitems = list(confdict.items())
    confitems.sort()
    confstr = str(confitems)
    conffile = os.path.join(folder, '__conf__')
    try:
        oldconfstr = open(conffile, 'r').read()
    except OSError:
        pass
    else:
        if confstr != oldconfstr:
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
    open(conffile, 'w').write(confstr)
    return folder
