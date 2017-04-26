# vim: set fileencoding=UTF-8
# Copyright © 2015-2017 STRG.AT GmbH, Vienna, Austria
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


from .exceptions import (
    InitializationError, ConfigurationError, DependencyLoop)

from .dependency import DependencySolver

from .initializer import (
    init, init_from_file, init_logging_from_file,
    ConfiguredModule, ConfiguredScore)

from .config import (
    parse_bool, parse_datetime, parse_time_interval, parse_dotted_path,
    parse_call, parse_list, parse_host_port, parse_object, parse_json,
    init_object, init_cache_folder, extract_conf, parse_config_file)

from .autoimport import import_from_submodules

__version__ = '0.5.2'

__all__ = (
    'init', 'init_from_file', 'init_logging_from_file', 'InitializationError',
    'ConfigurationError', 'DependencySolver', 'DependencyLoop',
    'ConfiguredModule', 'ConfiguredScore', 'parse_bool', 'parse_datetime',
    'parse_time_interval', 'parse_dotted_path', 'parse_call', 'parse_list',
    'parse_host_port', 'parse_object', 'parse_json', 'init_object',
    'init_cache_folder', 'extract_conf', 'parse_config_file',
    'import_from_submodules')
