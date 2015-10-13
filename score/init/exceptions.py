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
