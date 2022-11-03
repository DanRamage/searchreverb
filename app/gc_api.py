from bs4 import BeautifulSoup
from flask import current_app
import logging.config
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from .results import listing, listings

class gc_listing(listing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        product = kwargs.get('product', None)
        site_id = kwargs.get('site_id')
        if product:
            try:
                self._search_site_id = site_id
                self._id = int(product.find('var', class_="hidden displayId").text)
                self._listing_description = str(product.find('div', class_="productTitle").text).strip()
                self._price = float(product.find('div', class_='priceContainer mainPrice').findChildren('span', class_="productPrice")[0].contents[-1])
                self._condition = str(product.find('div', class_='productCondition').text)
                link_tag = product.find('div', class_="product").find('div', class_="thumb").find('a', class_="quickView").attrs['href']
                self._link = "{main_url}{href}".format(main_url="https://www.guitarcenter.com", href=link_tag)
            except Exception as e:
                raise e

class gc_listings(listings):
    def parse(self, **kwargs):
        soup = kwargs.get('soup', None)
        site_id = kwargs.get('site_id', -1)
        if soup:
            product_container = soup.find("div", {"id": "resultsContent"})
            if product_container:
                product_list = product_container.find("ol")
                products = product_list.findChildren('li')
                for product in products:
                    try:
                        listing = gc_listing(product=product, site_id=site_id)
                        self._listings.append(listing)
                    except Exception as e:
                        current_app.logger.exception(e)
                if len(self._listings):
                    self._listings.sort(key=lambda item: item.price)



logger = logging.getLogger()
class guitarcenter_api:
    def __init__(self, **kwargs):
        self._base_used_url = "https://www.guitarcenter.com/Used"
        self._base_applied_filter_url = "https://www.guitarcenter.com/ajax/storeLocation/findInStoreList.jsp"
        self._firefox_binary = "/Applications/Firefox.app/Contents/MacOS/firefox"
        self._geckodriver_binary = "/usr/local/bin/geckodriver"

        self._driver = None
        self._min_prices = {}
        self._max_prices = {}
        return

    def initialize(self):
        if self._driver is None:
            try:
                #The GC search provides a select for min and max prices, however they are fixed. Not only
                #are they fixed, they don't send the actual value back, they use the drop list id. We need
                #to do an initial query to get those values.
                params = {
                    'Ntt': 'test',
                    'Ns': 'r'
                }
                headOption = webdriver.FirefoxOptions()
                headOption.headless = True
                self._driver = webdriver.Firefox(executable_path=self._geckodriver_binary, options=headOption)
                self._driver.get(self._base_used_url)
                soup = BeautifulSoup(self._driver.page_source, 'html.parser')
                #Find the element with the name minPrice_used.
                min_ele = soup.find(attrs={"name": "minPrice_used"})
                price_children = min_ele.findChildren("option")
                for price in price_children:
                    try:
                        text = int(price.text.replace('$', ''))
                        value = int(price['value'])
                        self._min_prices[text] = value
                    except ValueError:
                        pass
                    min_ele = soup.find(attrs={"name": "max-priceRange"})
                    price_children = min_ele.findChildren("option")
                    for price in price_children:
                        try:
                            text = int(price.text.replace('$', ''))
                            value = int(price['value'])
                            self._max_prices[text] = value
                        except ValueError:
                            pass

            except Exception as e:
                current_app.logger.exception(e)

    '''
    The guitar center search does not pass the actual monetary values, it uses the value attribute of the items
    in the <select> drop down. This function takes the min/max values from the search and gets the appropriate
    IDs to use in the GET.
    '''
    def get_price_ids(self, min_value, max_value):
        price_ids = []
        #No min value, we'll set it to 0.
        if min_value is None:
            min_value = 0
        #No max value, let's set it really high.
        if max_value is None:
            max_value = 1000000
        for price in self._min_prices:
            if price >= min_value and price < max_value:
                price_ids.append(str(self._min_prices[price]))
        return price_ids


    def search_used(self, search_term, min_value, max_value, site_id, filter_options=None):
        self.initialize()
        listings = []
        if self._driver:
            try:
                #Parameters for the search term
                #Ntt = search term
                #Ns = ?
                #N = The price Ids
                #Build price IDs
                price_ids = self.get_price_ids(min_value, max_value)
                url_template = "{url}?Ntt={search_term}&Ns=r&N={price_ids}".format(
                  url=self._base_used_url,
                  search_term=search_term,
                  price_ids="+".join(price_ids)
                )
                self._driver.get(url_template)
                soup = BeautifulSoup(self._driver.page_source, 'html.parser')
                listings = gc_listings()
                listings.parse(soup=soup, site_id=site_id)
                current_app.logger.debug("Query has: {rec_cnt} results.".format(rec_cnt=len(listings)))
            except Exception as e:
                current_app.logger.exception(e)
            self._driver.quit()
            self._driver = None

        return(listings)

def main():
    gc_api = guitarcenter_api()
    gc_api.search_used('belle epoch deluxe', 100, 500)
    return

if __name__ == "__main__":
    main()