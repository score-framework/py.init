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

import configparser
import os
import re
import warnings
from ..exceptions import ConfigurationError
from .helpers import parse_list
import logging
from glob import glob


log = logging.getLogger(__name__)


def parse(file, *, recurse=True):
    """
    Reads a configuration file and returns a :class:`configparser.ConfigParser`.

    The main feature of this function is the support for "adjustment files",
    i.e. files that do not actually define all values, but define deviations
    from another file. The function will collect the set of all values by
    recursing into the files defined in the initial file. This whole feature can
    be disabled, though, by passing a falsey value as the *recurse* argument, in
    which case the function just behaves like a configparser with
    :class:`configparser.ExtendedInterpolation`.

    If the *recurse* value is left at its default, the parsing process is at
    follows:

    - The file is parsed using the :class:`configparser.ExtendedInterpolation`.
    - If there is no section ``score.init``, or that section does not have a key
      ``based_on``, the parsed configuration is returned as-is. At this point
      the function was just used to parse the given file as a stand-alone file.
    - If a base file, as described earlier, was configured, that file is parsed
      first. The current file is regarded as an "adjustment file", which mangles
      the configuration provided in the base file.
    - The function now iterates on all key/value pairs of the adjustment file
      and updates the base configuration in the following manner:

      - If the adjustment value is "<delete>", the value in the original
        configuration is removed. If this leaves the section in the original
        file empty, the section is removed as well.

      - If the adjustment value starts with the string "<diff>", it is
        considered to contain a value in pseudo-diff format operating on the
        base value. The accepted format for this mode is explained later.

      - If the adjustment value is of the form "<replace:regex:replacement>",
        the regular expression given as *regex* is applied on the base value and
        the *first occurrence* is replaced with the value given as
        *replacement*. If one wants to replace *all* occurrences, it is possible
        to do so providing the flag "g" as last parameter:
        "<replace:regex:replacement:g>".

        The colons used in the example can be replaced with any
        other character, so the same rule could have been written as
        "<replace/regex/replacement>".

        It is further possible to chain multiple replace actions.

      - Otherwise the value is considered to be the replacement for the value in
        the base configuration.

    - The updated configuration is the return value of the function.

    Example with the following base file called "app.conf"::

        [score.init]
        modules =
            score.ctx
            score.db
            score.es

        [score.db]
        base = fuf.db.base.Storable
        sqlalchemy.url = sqlite:///${here}/database.sqlite3
        destroyable = true

    The next file is intended to adjust the above configuration to the
    local environment::

        [score.init]
        based_on = app.conf
        modules = <diff>
            -score.es

        [score.db]
        sqlalchemy.url =
            <replace:database:app>
            <replace:\.sqlite3$:.db>
        destroyable = <delete>

    The resulting configuration will behave as if the input file looked like
    this::

        [score.init]
        based_on = app.conf
        modules =
            score.ctx
            score.db

        [score.db]
        base = fuf.db.base.Storable
        sqlalchemy.url = sqlite:///${here}/app.db

    The custom diff format of this function works without line numbers and just
    consists of removals (lines with a leading dash), additions (leading plus
    sign) and anchors (leading space or no character at all).

    The only issue with this format that has no line numbers is the question
    where to insert the additions. The solution to this problem is: right after
    the last anchor, or, if there was no anchor, at the beginning of the string.

    Also note that all removals also act as anchors for this purpose.

    Here are some examples demonstrating the above::

        |foo     |+baz      |baz
        |bar  +  |      =>  |foo
                            |bar

        |foo     | bar      |foo
        |bar  +  |+baz  =>  |bar
                            |baz

        |foo     | foo      |foo
        |bar  +  |+baz  =>  |baz
                            |bar

        |foo     |-bar      |foo
        |bar  +  |+baz  =>  |baz

    """
    return _parse(file, [], recurse)


def _parse(file, visited, recurse=True):
    """
    Helper function for :func:`parse`, needed for hiding the *visited*
    parameter in the public API. The purpose of that parameter is to prevent
    loops in the include directives.
    """
    log.debug('%sparsing %s', '  ' * len(visited), file)
    settings = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation())
    settings['DEFAULT']['here'] = os.path.dirname(file)
    if not settings['DEFAULT']['here']:
        settings['DEFAULT']['here'] = '.'
    with open(file) as fp:
        settings.read_file(fp)
    if not recurse:
        return settings
    try:
        includes = settings['score.init']['include']
    except KeyError:
        includes = ''
    files = []
    visited.append(os.path.abspath(file))
    settings = _parse_bases(file, visited, settings, files)
    settings = _parse_includes(file, visited, settings, files, includes)
    visited.pop()
    if 'score.init' not in settings:
        settings['score.init'] = {}
    try:
        settings['score.init']['_files'] = \
            settings['score.init']['_files'] + '\n' + '\n'.join(files)
    except KeyError:
        settings['score.init']['_files'] = '\n'.join(files)
    return settings


def _parse_bases(file, visited, settings, files):
    """
    Handles the ``score.init/based_on`` key in the parsed *settings* of given
    configuration *file*. Will add all encountered bases to the list of *files*
    encountered while handling the the current file. Will also raise a
    :class:`.ConfigurationError` if it encounters a file that has already been
    *visited*.
    """
    try:
        bases_string = settings['score.init']['based_on']
    except KeyError:
        return settings
    adjustments = settings
    bases = []
    files.append(os.path.abspath(file))
    for base in parse_list(bases_string):
        if not os.path.isabs(base):
            base = os.path.join(settings['DEFAULT']['here'], base)
            base = os.path.abspath(base)
        if base in visited:
            import score.init
            raise ConfigurationError(
                score.init,
                'Configuration file loop:\n - ' + '\n - '.join(visited))
        files.append(base)
        bases.append(_parse(base, visited))
    settings = _merge_settings(*bases)
    _apply_adjustments(file, settings, adjustments)
    return settings


def _parse_includes(file, visited, settings, files, includes):
    """
    Handles the ``score.init/include`` key in the parsed *settings* of given
    configuration *file*. Will add all encountered bases to the list of *files*
    encountered while handling the the current file. Will also raise a
    :class:`.ConfigurationError` if one of the includes has a ``based_on``
    configuration.
    *visited*.
    """
    if not includes:
        return settings
    for include_declaration in parse_list(includes):
        for include_file in glob(include_declaration):
            include = _parse(include_file, visited, recurse=False)
            try:
                if include['score.init']['based_on']:
                    import score.init
                    raise ConfigurationError(
                        score.init,
                        'An included file cannot be `based_on` other files')
            except KeyError:
                pass
            _apply_adjustments(file, settings, include)
            files.append(include_file)
    return settings


def _merge_settings(*settings):
    """
    Returns a new :class:`configparser.ConfigParser` that contains all sections
    and keys in given list of configuration *settings*. Keys in later settings
    will overwrite those in earlier settings.
    """
    result = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation())
    for other in settings:
        for section in other:
            if section == 'DEFAULT':
                continue
            if section not in result:
                result[section] = {}
            for key in other[section]:
                value = other[section][key]
                if key in other['DEFAULT'] and other['DEFAULT'][key] == value:
                    continue
                result[section][key] = value
    return result


_replace_regex = re.compile(
    r"""
        <replace
            (?P<separator>.)        # arbitrary separator
            (?P<regex>.*?)          # the regular expression
            \1                      # separator backref
            (?P<replacement>.*?)    # replacement value
            (?:                     # optional flags group
                \1                      # separator backref
                (?P<flags>.*)           # flags (currently only "g",
            )?                          #        but we match anything)
            >
        \s*     # match any whitespace *after* the match to be able to continue
                # matching right afterwards without needing to trim first
    """, re.VERBOSE)


def _apply_adjustments(file, settings, adjustments):
    """
    Helper function for :func:`parse`, which applies all adjusting settings
    changes as described in that function's documentation.
    """
    for section in adjustments:
        if section == 'DEFAULT':
            continue
        for key in adjustments[section]:
            try:
                value = adjustments[section][key]
                try:
                    if adjustments['DEFAULT'][key] == value:
                        continue
                except KeyError:
                    pass
            except configparser.InterpolationSyntaxError:
                # Handle "broken" interpolation in regular expressions due to
                # end-of-string anchor (i.e. dollar sign) by bypassing
                # interpolation altogether (using the *raw* kwarg). Example
                # scenario where this is useful (not the dollar sign):
                #   <replace:\.sqlite3$:.db>
                value = adjustments[section].get(key, raw=True)
                if not _replace_regex.match(value):
                    raise
            except configparser.InterpolationMissingOptionError:
                value = adjustments[section].get(key, raw=True)
            _apply_adjustment(file, settings, section, key, value)


def _apply_adjustment(file, settings, section, key, value):
    """
    Helper function for :func:`_apply_adjustments`, which applies a single
    adjusting setting changes as described in the documentation to
    :func:`parse`.
    """
    if value.strip() == '<delete>':
        try:
            del settings[section][key]
        except KeyError:
            warnings.warn(
                'Requested delete-adjustment target %s/%s does '
                'not exist in original file %s' % (section, key, file))
    elif value.strip().startswith('<diff>'):
        try:
            original = settings[section][key]
        except KeyError as e:
            import score.init
            raise ConfigurationError(
                score.init,
                'Original value of diff-adjustment to %s/%s not found in %s' %
                (section, key, file)
            ) from e
        settings[section][key] = _apply_diff(section, key, original, value)
    elif _replace_regex.match(value.strip()):
        try:
            original = settings[section][key]
        except KeyError as e:
            import score.init
            raise ConfigurationError(
                score.init,
                'Original value of replace-adjustment to %s/%s '
                'not found in %s' % (section, key, file)
            ) from e
        settings[section][key] = _apply_replace(section, key, original, value)
    else:
        if section not in settings:
            settings[section] = {}
        settings[section][key] = value


def _apply_diff(section, key, original, diff):
    """
    Applies a *diff* value as described in :func:`.parse` to given *original*
    value.
    """
    from score.init import parse_list
    lines = parse_list(original)
    diff_lines = map(lambda x: x.strip(),
                     parse_list(re.sub(r'^\s*<diff>\s*', '', diff)))
    anchor = 0
    for line in diff_lines:
        if line[0] not in '-+':
            try:
                anchor = lines.index(line) + 1
            except ValueError as e:
                import score.init
                raise ConfigurationError(
                    score.init,
                    'Error parsing diff in %s/%s: line does not exist in base'
                    'file:\n %s' % (section, key, line)
                ) from e
        elif line[0] == '-':
            try:
                anchor = lines.index(line[1:])
            except ValueError as e:
                import score.init
                raise ConfigurationError(
                    score.init,
                    'Error parsing diff in %s/%s: line does not exist in base'
                    'file:\n %s' % (section, key, line)
                ) from e
            del lines[anchor]
        elif line[0] == '+':
            lines.insert(anchor, line[1:])
        else:
            assert False, 'Should never be here'
    return '\n'.join(lines)


def _apply_replace(section, key, original, definition):
    """
    Applies a *replace* operation as described in :func:`.parse` to given
    *original* value.
    """
    replaced = original
    start = 0
    definition = definition.strip()
    while original[start:]:
        match = _replace_regex.match(definition, start)
        if not match:
            import score.init
            raise ConfigurationError(
                score.init,
                'Adjustment value for %s/%s contains invalid replacements' %
                (section, key)
            )
        start += len(match.group(0))
        regex = re.compile(match.group('regex'))
        replacement = match.group('replacement')
        flags = match.group('flags') or ''
        count = 1
        if 'g' in flags:
            count = 0
        tmp = re.sub(regex, replacement, replaced, count)
        if tmp == replaced:
            warnings.warn('Provided regex "%s" did not match anything '
                          'in %s/%s' % (regex, section, key))
        replaced = tmp
    return replaced
