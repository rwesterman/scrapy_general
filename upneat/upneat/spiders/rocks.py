# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
import logging
# import pandas as pd

class RocksSpider(scrapy.Spider):
    name = 'rocks'
    start_urls = ['http://www.upneat.rocks/recipe/sources/pdt/',
                  "http://www.upneat.rocks/recipe/sources/the-craft-of-the-cocktail",
                  "http://www.upneat.rocks/recipe/sources/death-co"]

    def __init__(self):
        super().__init__()

        self.log = logging.getLogger("__name__")
        # allowed_domains = ['www.upneat.rocks/recipe/sources/pdt']
        self.link_extractor = LinkExtractor(restrict_xpaths='/html/body/div/div[@class="row"]/ul')
        self.links = []
        self.pdt_drinks = {}

    def parse(self, response):
        self.links = self.link_extractor.extract_links(response)
        # self.log.debug(self.links)
        for link in self.links:
            # Get URL from Link object
            url = link.url
            # follow the drink URL and extract the recipe
            yield response.follow(url, self.parse_recipe)

        # print(self.pdt_drinks)

    def parse_recipe(self, response):
        # Todo: Integrate this with adding the recipe to database in real time
        # Gather the drink name and strip the newline characters
        drink_name = response.xpath('//div[@class="container-fluid"]/div/div/h3/text()'
                                    ).extract_first().strip('\n')

        # Since this will be a csv, need to remove any commas from drink names
        if "," in drink_name:
            no_commas = drink_name.split(",")
            drink_name = "".join(no_commas)

        # source = response.xpath('//div[@class="container-fluid"]/div/div/h3/p/a/text()').extract_first()
        source = response.xpath('//a[@style="font-style:italic"]/text()').extract_first()
        # get list of ingredients from recipe page
        ingredients = response.xpath('//div[@class="container-fluid"]/div/div/ul/li/text()').extract()

        self._append_to_file(drink_name, source, ingredients)



        return

    def _append_to_file(self, drink_name, source, ingredients):

        with open("upneat_recipes.csv", 'a') as f:
            f.write("{}, {}, {}\n".format(drink_name, source, ", ".join(ingredients)))