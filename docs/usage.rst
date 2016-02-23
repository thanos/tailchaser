=====
Usage
=====

To use tailchaser in a project::


  #
	# Example 1
	#
	
	import tailchaser
	
	class TailToElastic(tailchaser.Tailer):
		def handoff(self, file_tailed, checkpoint, record):
			""" Expect a record like:
			
			20160204 10:28:15,525 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/lme-market.properties]
			20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-database.properties]
			20160204 10:28:15,541 INFO PropertiesLoaderSupport - Loading properties file from URL [file:C:/WaterWorks/Broken/BSE//config/default-hibernate.properties]
			20160204 10:28:15,588 INFO MLog - MLog clients using log4j logging.
			20160204 10:28:15,729 INFO C3P0Registry - Initializing c3p0-0.9.1.2 [built 21-May-2007 15:04:56; debug? true; trace: 10]
			20160204 10:28:15,775 INFO AbstractApplicationContext$BeanPostProcessorChecker - Bean 'defaultDataSourceTarget' is not eligible for getting processed by all BeanPostProcessors (for example: not eligible for auto-proxying)
			20160204 10:28:15,791 INFO AbstractApplicationContext$BeanPostProcessorChecker - Bean 'defaultDataSource' is not eligible for getting processed by all BeanPostProcessors (for example: not eligible for auto-proxying)
			"""
			date, time, level, source, _, message = record.split(5)
		
			requests.json("http://someelacticserver.com:9200/myindex/log", json={
											'timestamp': '{}T{}'.format(date, time)
											'level': level,
											'source': source,
											'message': message
									})
																		
