from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http.request import Request
import sqlite3 

import re

# Used to find gas mileage from a string that can look like:
#	23 City / 25 Hwy
#	23 (Est) City / 25 (Est) Hwy
#	23 (2011) City / 25 (2011) Hwy
#	or just be NA
mpg_regex = re.compile(r'\s(?P<city>\d+).*City\s/\s(?P<hwy>\d+).*Hwy')

class car_db_interface:
	def __init__(self):
		self.db = sqlite3.connect('car_data.db')

		# create a table to hold the data
		table_create_string = "create table if not exists car_data" +\
			"(make, model, mpg_city default 'NA', mpg_hwy default 'NA', cost)"
		index_create_string = "create index if not exists car_data_index on car_data" +\
			"(model, cost)"
		self.db.execute(table_create_string)
		self.db.execute(index_create_string)

	def __del__(self):
		# commit any changes and close the database
		self.db.commit()
		self.db.close()

	def add_cars(self, make, model, mpg_city, mpg_hwy, cost_list):
		for m in range(len(model)):
			insert_string = "insert into car_data (make, model, mpg_city, mpg_hwy, cost) " +\
				"values (?, ?, ?, ?, ?)"
			self.db.execute(insert_string, (make, model[m], mpg_city[m], mpg_hwy[m], cost_list[m]))

class UsnewsSpider(BaseSpider):
	name = "usnews"
	allowed_domains = ["rankingsandreviews.com"]
	start_urls = ["http://usnews.rankingsandreviews.com/cars-trucks"]
	base_url = "http://usnews.rankingsandreviews.com"

	def __init__(self):
		# connect to database
		self.car_db = car_db_interface()


	def parse(self, response):
		hxs = HtmlXPathSelector(response)
		man_name = hxs.select('//div[@id="brand-browser"]//ul//li//a/text()').extract()
		man_link = hxs.select('//div[@id="brand-browser"]//ul//li//a/@href').extract()

		for i in range(len(man_name)):
			yield Request(url = self.base_url + man_link[i], callback=self.parse_manufacturer)


	def parse_manufacturer(self, response):
		hxs = HtmlXPathSelector(response)

		# The make of the car can be found in the title:
		# 	"Browse MAKE - ..."
		make = hxs.select('//title/text()').re(r'Browse\s([\w\s\d]+)\s-')[0]

		# Models are found under the "car-listing" DIV in the heading H3
		models = hxs.select('//div[@class="car-listing"]//div//h3/a/text()').extract()

		# The MPG string is under that same "car-listing" DIV within a un-ordered list
		# following the string "MPG:". This string will be further refined later
		mpg_str = hxs.select('//div[@class="car-listing"]//div//ul//li/text()').re(r'MPG:([\s\w\(\)/]+)')

		# Cost info, like MPG, is in an un-ordered list under "car-listing". It can either have
		# the format of Avg Paid: $XX,XXX - $XX,XXX OR MSRP: $XX,XXX - $XX,XXX
		# The MSRP format is not a link, so it exists as text under the list element, whereas
		# the Avg Price format is within an <a> element
		cost_html = hxs.select('//div[@class="car-listing"]//div/ul//li').extract()
		cost_list = re.findall(r'Avg\. Paid:\s.+>(.+)</a|MSRP: (.+)<',"".join(cost_html))

		mpg_city = []
		mpg_hwy = []
		cost_str_list = []
		
		for m in range(len(models)):
			# Use the REGEX compiled above to find the gas mileage
			mpg_res = mpg_regex.search(mpg_str[m])

			if not mpg_res:
				# If it couldn't be translated, use NA
				mpg_city.append('NA')
				mpg_hwy.append('NA')
			else:
				# Otherwise, append the values associated with the named groups
				mpg_city.append(mpg_res.group('city'))
				mpg_hwy.append(mpg_res.group('hwy'))

			if not cost_list[m][0]:
				# Only MSRP available
				cost_str_list.append(cost_list[m][1] + "(MSRP)")
			else:
				# Use average paid
				cost_str_list.append(cost_list[m][0])
			
		# Send these cars to the database
		self.car_db.add_cars(make, models, mpg_city, mpg_hwy, cost_str_list)
			