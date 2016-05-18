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


import pkgutil
import importlib
import inspect


def import_from_submodules():
    """
    This function must be called from a *package* initializer, i.e. the
    ``__init__.py`` file of a package folder. It will import everything defined
    in all sub-modules and sub-packages of the calling package.

    Example scenario::

        foo/
            __init__.py
            bar/
                __init__.py
                sub_bar.py
            baz.py

    If this function is called in ``foo/__init__.py``, the python package
    *foo* will contain everything, that was exported by the package
    *foo.bar* or the module *foo.baz*.

    The imports are performed as if one would have imported ``*`` from each
    sub-package. Calling this function inside ``foo/__init__.py`` is equivalent
    to writing the following two lines:

    .. code-block:: python

        from .bar import *
        from .baz import *
    """
    globals_ = inspect.currentframe().f_back.f_globals
    packages = pkgutil.walk_packages(
        path=globals_['__path__'], prefix=globals_['__name__'] + '.')
    for importer, modname, ispkg in packages:
        mod = importlib.import_module(modname)
        if hasattr(mod, '__all__'):
            all_ = mod.__all__
        else:
            all_ = (name for name in dir(mod) if name[0] != '_')
        for name in all_:
            globals_[name] = getattr(mod, name)
