chimera_fli plugin
==================

A chimera_ plugin for `Finger Lakes Instrumentation`_ cameras and filter wheels.

Usage
-----

Install chimera_ on your computer, and then, this package. Edit the configuration like the example below. The type of
the ``camera`` instrument section should be ``FLI``.

Installation
------------

This package depends on python-FLI_ package. We strongly suggest to use `our fork`_ of it, which is the one we use on
our tests.

::

    pip install -U git+https://github.com/astroufsc/python-FLI.git
    pip install -U git+https://github.com/astroufsc/chimera_template.git


Configuration Example
---------------------

``chimera.config`` for a FLI camera with a filter wheel with a set of 5 SLOAN filters.

::

    camera:
      name: fli
      type: FLI
      filters: u g r i z

Tested Hardware
---------------

This plugin was tested on these hardware:

*  FLI ProLine PL4720 camera with FLI CenterLine CL-1-20 Filter Wheel


Contact
-------

For more information, contact us on chimera's discussion list:
https://groups.google.com/forum/#!forum/chimera-discuss

Bug reports and patches are welcome and can be sent over our GitHub page:
https://github.com/astroufsc/chimera_fli/

.. _Finger Lakes Instrumentation: http://www.flicamera.com/
.. _chimera: https://github.com/astroufsc/chimera
.. _python-FLI: https://github.com/cversek/python-FLI
.. _our fork: https://github.com/astroufsc/python-FLI