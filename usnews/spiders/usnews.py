from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http.request import Request

import re

mpg_regex = re.compile(r'\s(?P<city>\d+).*City\s/\s(?P<hwy>\d+).*Hwy')
cost_regex = re.compile(r'Avg\. Paid:\s.+\>(.+)/<|MSRP:\s(.+)\<')

class UsnewsSpider(BaseSpider):
	name = "usnews"
	allowed_domains = ["rankingsandreviews.com"]
	start_urls = ["http://usnews.rankingsandreviews.com/cars-trucks"]
	base_url = "http://usnews.rankingsandreviews.com"

	def __init__(self):
		self.file = open('dump.txt','w+')

	def __del__(self):
		self.file.close()

	def parse(self, response):
		hxs = HtmlXPathSelector(response)
		man_name = hxs.select('//div[@id="brand-browser"]//ul//li//a/text()').extract()
		man_link = hxs.select('//div[@id="brand-browser"]//ul//li//a/@href').extract()

		for i in range(len(man_name)):
			yield Request(url = self.base_url + man_link[i], callback=self.parse_manufacturer)


	def parse_manufacturer(self, response):
		hxs = HtmlXPathSelector(response)
		models = hxs.select('//div[@class="car-listing"]//div//h3/a/text()').extract()
		mpg_str = hxs.select('//div[@class="car-listing"]//div//ul//li/text()').re(r'MPG:([\s\w\(\)/]+)')

		cost_html = hxs.select('//div[@class="car-listing"]//div/ul//li').extract()

		cost_list = re.findall(r'Avg\. Paid:\s.+>(.+)</a|MSRP: (.+)<',"".join(cost_html))

		mpg_city = []
		mpg_hwy = []
		
		for m in range(len(models)):
			mpg_res = mpg_regex.search(mpg_str[m])

			if not mpg_res:
				mpg_city.append('NA')
				mpg_hwy.append('NA')
			else:
				mpg_city.append(mpg_res.group('city'))
				mpg_hwy.append(mpg_res.group('hwy'))

			if not cost_list[m][0]:
				# Only MSRP available
				cost_str = cost_list[m][1] + "(MSRP)"
			else:
				# Use average paid
				cost_str = cost_list[m][0]

			self.file.write(models[m] + ": " + mpg_city[m] + " city / " \
				+ mpg_hwy[m] + " hwy, " \
				+ cost_str + '\n')



