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
    
=====
Usage
=====


To use tailchaser in a project::


    #
    # Example 1 - Tail to Elastic
    #

    import requests

    import tailchaser

    class TailToElastic(tailchaser.Tailer):
        def handoff(self, file_tailed, checkpoint, record):
            """ Expect a record like:

            20160204 10:28:15,525 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/lme-market.properties]
            20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-database.properties]
            20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-hibernate.properties]
            """

            date, time, level, source, _, message = record.split(5)
            requests.json("http://someelacticserver.com:9200/myindex/log", json={
                            'timestamp': '{}T{}'.format(date, time)
                            'level': level,
                            'source': source,
                            'message': message
                            })




    #
    # Example 2 - Tail to Kafka - shows how to add your own arguments and then send messahes to kafka.
    #


    import msgpack
    import tailchaser
    from kafka import KafkaProducer

    class TailToKafka(tailchaser.Tailer):
        def add_arguments(cls, parser=None):
            parser = super(TailToKafka, cls).add_arguments(parser)

        HOSTS = 'localhost:1234'
        TOPIC = 'log'
        def startup(self):
            self.kafka_producer = KafkaProducer(bootstrap_servers=self.HOSTS,value_serializer=msgpack.dumps)
            

        def handoff(self, file_tailed, checkpoint, record):
            """ Expect a record like:

            20160204 10:28:15,525 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/lme-market.properties]
            20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-database.properties]
            20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-hibernate.properties]
            """
            self.kafka_producer.send(self.TOPIC, message)


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
