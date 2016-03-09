.. module:: score.init
.. role:: faint
.. role:: confkey

**********
score.init
**********

Introduction
============

This module provides helper functions that will allow implementing our
:ref:`initialization guidelines <initialization>` conveniently. It provides an
auto-initializer for a list of score-modules and several functions supporting
the initialization process itself.


Configuration
=============

.. autofunction:: score.init.init

.. autofunction:: score.init.init_from_file

.. autofunction:: score.init.parse_config_file

.. autofunction:: score.init.init_logging_from_file

.. autoclass:: score.init.ConfiguredScore

.. autoclass:: score.init.ConfiguredModule

Exceptions
----------

.. autoclass:: score.init.InitializationError

.. autoclass:: score.init.DependencyLoop

.. autoclass:: score.init.ConfigurationError


Helper functions
================

.. autofunction:: score.init.parse_bool

.. autofunction:: score.init.parse_list

.. autofunction:: score.init.parse_host_port

.. autofunction:: score.init.parse_time_interval

.. autofunction:: score.init.parse_dotted_path

.. autofunction:: score.init.parse_call

.. autofunction:: score.init.extract_conf

.. autofunction:: score.init.parse_object

.. autofunction:: score.init.init_cache_folder

