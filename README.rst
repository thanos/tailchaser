========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|  |requires|
        | |codecov|
    * - package
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/tailchaser/badge/?style=flat
    :target: https://readthedocs.org/projects/tailchaser
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/thanos/tailchaser.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/thanos/tailchaser

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/thanos/tailchaser?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/thanos/tailchaser

.. |requires| image:: https://requires.io/github/thanos/tailchaser/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/thanos/tailchaser/requirements/?branch=master

.. |codecov| image:: https://codecov.io/github/thanos/tailchaser/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/thanos/tailchaser

.. |version| image:: https://img.shields.io/pypi/v/tailchaser.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/tailchaser

.. |downloads| image:: https://img.shields.io/pypi/dm/tailchaser.svg?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/tailchaser

.. |wheel| image:: https://img.shields.io/pypi/wheel/tailchaser.svg?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/tailchaser

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/tailchaser.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/tailchaser

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/tailchaser.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/tailchaser


.. end-badges

the ultimate tailer

* Free software: BSD license

Installation
============

::

    pip install tailchaser

Documentation
=============

https://tailchaser.readthedocs.org/

Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox
