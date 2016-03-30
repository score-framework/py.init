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
