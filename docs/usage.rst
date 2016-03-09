=====
Usage
=====


To use tailchaser in a project::


    #
    # Example 1 - Tail to Elastic
    #

    import requests

    import tailchaser

    class TailToElastic(tailchaser.producers.Tailer):
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

    class TailToKafka(tailchaser.producers.Tailer):
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
            self.kafka_producer.send(self.TOPIC, record)

     






