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

The ultimate rotation and windows friendly log tailer plus a lot more...

- backfills rotated files
- handles gz and bz2 files
- handles multi line records
- doesn't break windows rotating log handlers
- easy to extend
- Free software: BSD license
- other than six pure Python stdlib.

Installation
============ 

::
    
    pip install tailchaser
    
Thsi will install the tailchaser library in your site-packages and it will also add the script tailchase to your Scripts directory. 


Usage
===== 
   
::

    $ tailchase /where/my/logs/*.log

    $ tailchase -h
    
    usage: tailchase [-h] [--only-backfill] [--dont-backfill]
                   [--clear-checkpoint] [--read-period READ_PERIOD]
                   [--read-pause READ_PAUSE] [--reading-from {unix,win}]
                   [--temp-dir TEMP_DIR]
                   [--logging {DEBUG,INFO,WARN,ERROR,CRITICAL}]
                   file-pattern


    positional arguments:
      file-pattern          The file pattern to tail, such as /var/log/access.*

    optional arguments:
      -h, --help            show this help message and exit
      --only-backfill       dont't tail, default: False
      --dont-backfill       basically only tail, default: False
      --clear-checkpoint    start form the begining, default: False
      --read-period READ_PERIOD
                        how long you read before you pause. If zero you don't
                        pause, default: 1
      --read-pause READ_PAUSE
                        how long you pause between reads, default: 0
      --reading-from PLATFORM
                        sets how long you read and then pause can be one of {unix,win}, default: win
      --temp-dir TEMP_DIR   on back fill files are copied to a temp directory.Use
                        this to set this directory, default: None
      --logging LEVEL
                        logging level it can be one of  DEBUG,INFO,WARN,ERROR,CRITICAL, default: ERROR



In its simplest form
--------------------

In its simplest form tailchase works like a combination of cat and tail -f except it will start with the oldest rotated file. So if you were to have ::

    /var/log/opendirectoryd.log
    /var/log/opendirectoryd.log.0
    /var/log/opendirectoryd.log.1
    /var/log/opendirectoryd.log.2
    /var/log/opendirectoryd.log.3
    /var/log/opendirectoryd.log.4

it would first output  the text of /var/log/opendirectoryd.log.4, then /var/log/opendirectoryd.log.3, etc. until it reached the newest file then when it  has reached the end of /var/log/opendirectoryd.log revert to a "tail -f" behaviour.

So if you were to do ::
    
    tailchase 'tests/logs/opendirectoryd.*'
    
"*note: In bash you need to quote the wildcard otherwise it will be expanded into the scripts argv array.*"

you would get something like ::

    2015-12-24 15:39:56.733754 EST - AID: 0x0000000000000000 - Registered node with name '/Contacts'
    2015-12-24 15:39:56.733933 EST - AID: 0x0000000000000000 - Registered node with name '/LDAPv3' as hidden
    2015-12-24 15:39:56.736154 EST - AID: 0x0000000000000000 - Registered node with name '/Local' as hidden
    2015-12-24 15:39:56.736868 EST - AID: 0x0000000000000000 - Registered node with name '/NIS' as hidden
    2015-12-24 15:39:56.737134 EST - AID: 0x0000000000000000 - Discovered configuration for node name '/Search' at path '       2015-12-24 15:39:56.737151 EST - AID: 0x0000000000000000 - Registered node with name '/Search'
    2015-12-24 15:39:56.738794 EST - AID: 0x0000000000000000 - Loaded bundle at path '/System/Library/OpenDirectory/Modules     2015-12-24 15:39:56.740509 EST - AID: 0x0000000000000000 - Loaded bundle at path '/System/Library/OpenDirectory/Modules/


Coding with tailchaser
======================


Using the tailchaser library in a project is probably best done by example.


Example 1 - Tailchase to a REST service.
----------------------------------------

::

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
            result = requests.json("http://someelacticserver.com:9200/myindex/log", json={
                            'timestamp': '{}T{}'.format(date, time)
                            'level': level,
                            'source': source,
                            'message': message
                            })
            return result.status_code == requests.codes.ok


Example 2 - Tailchase to  Kafka
-------------------------------

::
    
    #
    # Example 2 - Tail to Kafka - shows how to add your own arguments and then send messages to kafka.
    #

    from kafka import KafkaProducer
    rom tailchaser.tailer import Tailer
    
    
    class TailToKafka(Tailer):
        def add_arguments(cls, parser=None):
            parser = super(TailToKafka, cls).add_arguments(parser)

        HOSTS = 'localhost:1234'
        TOPIC = b'log'
        def startup(self):
            self.kafka_producer = KafkaProducer(bootstrap_servers=self.HOSTS,value_serializer=msgpack.dumps)


        def handoff(self, file_tailed, checkpoint, record):
            """ Expect a record like:

            20160204 10:28:15,525 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/lme-market.properties]
            20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-database.properties]
            20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-hibernate.properties]
            """
            self.kafka_producer.send(self.TOPIC, record).get(timeout=10)
            return True
             


Example 3 - Saving and Loading last Offset from Zookeeper 
---------------------------------------------------------

::

    #
    # Example 3 - Saving and Loading last Offset from Zookeeper 
    #
    import platform
    import pickle
    import six
    from kazoo.client import KazooClient
    from tailchaser.tailer import Tailer

    class TailToElastic(Tailer):
        def start(self):
            self.zk = KazooClient(hosts=self.config.zookeeper_host)
            self.zk.start()
            
            
        def stop():
            self.zk.stop()
            
        def load_checkpoint(self):
            zk_path = self.config.checkpoint_filename
            try:
                checkpoint = pickle.loads(self.zk.get(zk_path))
                log.debug('loaded: %s %s', zk_path, checkpoint)
                return checkpoint
            except (IOError, EOFError):
                log.debug('failed to load: %s', zk_path)
                return self.INIT_CHECKPOINT

        def save_checkpoint(self, checkpoint):
            log.debug('dumping %s %s', self.config.checkpoint_filename, checkpoint)
            return self.zk.set(self.config.checkpoint_filename, six.b(pickle.dumps(checkpoint)))


        @staticmethod
        def make_checkpoint_filename(source_pattern, path=None):
            zk_path =  '/'.join(['tailchase', platform.node(), slugify(source_pattern)]
            self.zk.ensure_path(zk_path)
            return zk_path


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

