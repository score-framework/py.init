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

import warnings
import configparser
import os
import re
import importlib


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
        raise ValueError('"%s" does not describe a boolean' % value)


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
        'sec': 1,
        'second': 1,
        'seconds': 1,
        'm': 60,
        'min': 60,
        'minute': 60,
        'minutes': 60,
        'h': 60*60,
        'hour': 60*60,
        'hours': 60*60,
        'd': 60*60*24,
        'day': 60*60*24,
        'days': 60*60*24,
    }
    config_error = ValueError(
        '"%s" does not describe a valid time interval' % value)
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
    value_error = ValueError(
        '"%s" does not describe a valid dotted path' % value)
    if '.' not in value:
        raise value_error
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
    return list(filter(None, (part.strip() for part in value.split('\n'))))


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
            return parse_host_port(fallback)
    parts = value.split(':')
    if len(parts) == 1:
        if isinstance(fallback, str):
            fallback = parse_host_port(fallback)
        if fallback and len(fallback) > 1:
            parts.append(fallback[1])
    if len(parts) < 2:
        raise ValueError('Missing port definition')
    return parts[0], int(parts[1])


def parse_object(confdict, key, args=tuple(), kwargs={}):
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
    if key not in confdict:
        raise ValueError('"%s" not found in confdict' % key)
    if '(' in confdict[key]:
        return parse_call(confdict[key], args, kwargs)
    cls = parse_dotted_path(confdict[key])
    kwargs = kwargs.copy()
    for key, value in extract_conf(confdict, key + '.').items():
        if '\n' in value:
            value = parse_list(value)
        kwargs[key] = value
    return cls(*args, **kwargs)


def init_object(*args, **kwargs):
    """
    Backward-compatibility for :func:`.parse_object`.
    """
    warnings.warn('The function init_object was renamed to parse_object',
                  DeprecationWarning, stacklevel=2)
    return parse_object(*args, **kwargs)


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
    if key not in confdict:
        raise ValueError('"%s" not found in confdict' % key)
    folder = confdict[key]
    os.makedirs(folder, exist_ok=True)
    folder = os.path.realpath(folder)
    if not os.access(folder, os.R_OK | os.W_OK):
        raise ValueError(
            'Configured cache folder "%s" is not writable' % folder)
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
