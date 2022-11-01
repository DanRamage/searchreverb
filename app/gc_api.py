from bs4 import BeautifulSoup
import requests
import logging.config
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

class gc_listing:
    def __init__(self, product):
        self._id = None
        self._price = None
        self._link = None
        try:
            self._id = product.find('var', class_="hidden productId").text
            self._price = float(product.find('div', class_='priceContainer mainPrice').findChildren('span', class_="productPrice")[0].contents[-1])
            link_tag = product.find('div', class_="product").find('div', class_="thumb").find('a', class_="quickView").attrs['href']
            self._link = "{main_url}{href}".format(main_url="https://www.guitarcenter.com", href=link_tag)
        except Exception as e:
            self._id = None
            self._price = None
class gc_listings:
    def __init__(self, soup):
        self._listings = []
        product_container = soup.find("div", {"id": "resultsContent"})
        if product_container:
            product_list = product_container.find("ol")
            products = product_list.findChildren('li')
            for product in products:
                listing = gc_listing(product)
                self._listings.append(listing)


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

                #else:
                #    logger.error("Unable to GET the url: {url} Code: {code}".format(url=self._base_used_url,
                #                                                                    code=req.status_code))
            except Exception as e:
                logger.exception(e)
    '''
    The guitar center search does pass the actual monetary values, it uses the value attribute of the items
    in the <select> drop down.
    '''
    def get_price_ids(self, min_value, max_value):
        price_ids = []
        for price in self._min_prices:
            if price >= min_value and price < max_value:
                price_ids.append(str(self._min_prices[price]))
        return price_ids


    def search_used(self, search_term, min_value, max_value, filter_options=None):
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
                listings = gc_listings(soup)
            except Exception as e:
                logger.exception(e)
        return(listings)

def main():
    gc_api = guitarcenter_api()
    gc_api.search_used('belle epoch deluxe', 100, 500)
    return

if __name__ == "__main__":
    main()