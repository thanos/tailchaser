=====
Usage
=====

To use tailchaser in a project::


    #
	# Example 1
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

