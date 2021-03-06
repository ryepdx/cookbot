#!/usr/bin/env python

import os
import re
import urlparse

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import HtmlXPathSelector

from cookbot.items import AllrecipesRecipe, Ingredient


class AllrecipesSpider(CrawlSpider):
    name = 'allrecipes'
    allowed_domains = ['allrecipes.com']
    download_delay = 1

    start_urls = [
        # International Recipes
        'http://allrecipes.com/Recipes/World-Cuisine/African/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Asian/Chinese/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Asian/Japanese/Main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Asian/Korean/Main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Asian/Indian/Main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Asian/Thai/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/European/Eastern-European/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/European/French/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/European/German/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/European/Greek/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/European/Italian/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Middle-Eastern/main.aspx',
        'http://allrecipes.com/Recipes/World-Cuisine/Latin-American/Mexican/main.aspx',
        'http://allrecipes.com/Recipes/USA-Regional-and-Ethnic/Cajun-and-Creole/main.aspx',
        'http://allrecipes.com/Recipes/USA-Regional-and-Ethnic/Southern-Recipes/Southern-Cooking-by-State/main.aspx',

         # American Recipes
        'http://allrecipes.com/Recipes/Main-Dish/Main.aspx',
        'http://allrecipes.com/Recipes/Meat-and-Poultry/Main.aspx',
        'http://allrecipes.com/Recipes/Fruits-and-Vegetables/Main.aspx',
        'http://allrecipes.com/Recipes/Seafood/Main.aspx',
        'http://allrecipes.com/Recipes/Pasta/Main.aspx',

        # By Meal Part
        'http://allrecipes.com/Recipes/appetizers-and-snacks/main.aspx',
        'http://allrecipes.com/Recipes/drinks/main.aspx',
        'http://allrecipes.com/Recipes/breakfast-and-brunch/main.aspx',
        'http://allrecipes.com/Recipes/main-dish/salads/main.aspx',
        'http://allrecipes.com/Recipes/soups-stews-and-chili/main.aspx',
        'http://allrecipes.com/Recipes/main-dish/main.aspx',
        'http://allrecipes.com/Recipes/side-dish/main.aspx',
        'http://allrecipes.com/Recipes/bread/main.aspx',
        'http://allrecipes.com/Recipes/desserts/main.aspx',
    ]

    rules = (
        # Follow pagination
        Rule(SgmlLinkExtractor(allow=(r'Recipes/.+/[M|m]ain.aspx\?Page=\d+',)), follow=True),

        # Extract recipes
        Rule(SgmlLinkExtractor(allow=(r'Recipe/.+/Detail.aspx',)), callback='parse_recipe')
    )

    def parse_recipe(self, response):
        hxs = HtmlXPathSelector(response)
        recipe = AllrecipesRecipe()

        # name
        recipe['name'] = hxs.select("//h1[@id='itemTitle']/text()")[0].extract().strip()

        # category
        referer = response.request.headers.get('Referer')
        category = os.path.dirname(urlparse.urlsplit(referer).path)
        recipe['category'] = category if not category.startswith('/Recipes/') \
                                      else category[len('/Recipes/'):]

        # author
        try:
            recipe['author'] = int(
                hxs.select("//span[@id='lblSubmitter']/a/@href").re('(\d+)')[0]
            )
        except:
            pass

        # description
        recipe['description'] = '\n'.join(hxs.select("//span[@id='lblDescription']/text()")
                                             .extract())

        # rating
        try:
            recipe['rating'] = float(
                hxs.select("//meta[@itemprop='ratingValue']/@content").extract()[0]
            )
        except:
            pass

        # ingredients
        ingredients = []
        ingredient_nodes = hxs.select("//li[@id='liIngredient']")
        for ingredient_node in ingredient_nodes:
            try:
                name = ingredient_node.select("label/p/span[@id='lblIngName']/text()") \
                                      .extract()[0]
                quantity = ingredient_node.select("label/p/span[@id='lblIngAmount']/text()") \
                                      .extract()[0]
            except:
                continue

            ingredient = Ingredient()
            ingredient['name'] = name
            ingredient['quantity'] = quantity
            ingredients.append(ingredient)
        recipe['ingredients'] = ingredients

        # instructions
        recipe['instructions'] = hxs.select(
            "//div[@class='directions']/div/ol/li/span/text()"
        ).extract()

        # nutrients
        recipe['nutrients'] = {}
        try:
            recipe['nutrients']['calories'] = int(
                hxs.select("//span[@id='litCalories']/text()").extract()[0]
            )
        except:
            pass

        def parse_nutrient(name):
            return hxs.select(
                "//span[@itemprop='{}Content']/following-sibling::*/text()".format(name)
            ).extract()[0].replace(' ', '').strip()

        for nutrient_type in ('fat', 'cholesterol', 'fiber', 'sodium',
                              'carbohydrate', 'protein'):
            try:
                value = parse_nutrient(nutrient_type)
                if value:
                    recipe['nutrients'][nutrient_type] = value
            except:
                pass

        return recipe
