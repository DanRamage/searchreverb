import logging.config
from re import sub
from decimal import Decimal

from bs4 import BeautifulSoup
from flask import current_app
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from .results import listing, listings


class gc_listing(listing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger = kwargs.get("logger", None)
        product = kwargs.get("product", None)
        site_id = kwargs.get("site_id")
        if product:
            try:
                self._search_site_id = site_id
                self._locality, self._region = None
                self._country_code = "US"

                product_id = product.find("div", attrs={"data-product-sku-id": True})
                if product_id is not None:
                    # The product id now has "site" prepended, we assign it and then strip "site" out of it.
                    self._id = product_id.attrs["data-product-sku-id"]
                    if "site" in self._id:
                        self._id = int(self._id.replace("site", ""))
                    # self._id = int(product.find("var", class_="hidden displayId").text)
                    self._listing_description = str(
                        product.find("a", class_="product-name").text
                    ).strip()
                    price = (
                        product.find("div", class_="price")
                        .findChildren("span", class_="sale-price")[0]
                        .contents[-1]
                    )
                    try:
                        self._price = float(Decimal(sub(r"[^\d.]", "", price)))
                    except (ValueError, Exception) as e:
                        raise e
                    link_tag = product.find("a", class_="product-name").attrs["href"]
                    # There is no ID or Class that identifies the Condition element.
                    # The only thing I see to use is the gc-font-light class, so since
                    # it is used multiple times in <p> elements, we loop and see if
                    # we find the "Condition" text.
                    condition_search = product.findAll("p", class_="gc-font-light")
                    for item in condition_search:
                        if "Condition" in item.text:
                            self._condition = str(item.text.replace("Condition: ", ""))
                            break
                    self._link = f"https://www.guitarcenter.com/{link_tag}"

                    # Try and get the city/state.
                    try:
                        store_location = str(
                            product.find("span", class_="store-name-text").text
                        )
                        self._locality, self._region = store_location.split(",")
                        self._locality = self._locality.strip()
                        self._region = self._region.strip()
                    except Exception as e:
                        logger.exception(e)

                else:
                    raise Exception("No product found.")
            except Exception as e:
                raise e
            """
            try:
                if product is not None:
                    # Try and get the city/state.
                    store_location = str(
                        product.find("span", class_="store-name-text").text
                    )
                    self._locality, self._region = store_location.split(",")
                    self._locality = self._locality.strip()
                    self._region = self._region.strip()
                    self._country_code = "US"
            except Exception as e:
                e
            """


class gc_listings(listings):
    def parse(self, **kwargs):
        soup = kwargs.get("soup", None)
        site_id = kwargs.get("site_id", -1)
        if soup:
            listing_container = soup.find("div", {"class": "listing-container"})
            if listing_container:
                product_grid = listing_container.find("div", {"class": "product-grid"})
                products = product_grid.findChildren("section")
                for product in products:
                    try:
                        listing = gc_listing(
                            product=product, site_id=site_id, logger=current_app.logger
                        )
                        self._listings.append(listing)
                    except Exception as e:
                        current_app.logger.exception(e)
                if len(self._listings):
                    self._listings.sort(key=lambda item: item.price)


logger = logging.getLogger()


class guitarcenter_api:
    def __init__(self, **kwargs):
        self._base_used_url = "https://www.guitarcenter.com/Used"
        self._base_applied_filter_url = (
            "https://www.guitarcenter.com/ajax/storeLocation/findInStoreList.jsp"
        )
        self._firefox_binary = "/Applications/Firefox.app/Contents/MacOS/firefox"
        self._geckodriver_binary = "/usr/local/bin/geckodriver"

        self._driver = None
        self._min_prices = {}
        self._max_prices = {}
        return

    def initialize(self):
        if self._driver is None:
            try:
                # The GC search provides a select for min and max prices, however they are fixed. Not only
                # are they fixed, they don't send the actual value back, they use the drop list id. We need
                # to do an initial query to get those values.
                options = Options()
                options.add_argument("--headless")
                firefox_service = Service(self._geckodriver_binary)
                self._driver = webdriver.Firefox(
                    options=options, service=firefox_service
                )
                # headOption = webdriver.FirefoxOptions()
                # headOption.headless = True
                # self._driver = webdriver.Firefox(
                #    executable_path=self._geckodriver_binary, options=headOption
                # )
                self._driver.get(self._base_used_url)
                # soup = BeautifulSoup(self._driver.page_source, "html.parser")
                # GC search page no longer uses these categories of prices. Now it appears
                # to be a Min-Max parameter passed in the POST command.
                """
                price_children = min_ele.findChildren("option")
                for price in price_children:
                    try:
                        text = int(price.text.replace("$", ""))
                        value = int(price["value"])
                        self._min_prices[text] = value
                    except ValueError:
                        pass
                    min_ele = soup.find(attrs={"name": "max-priceRange"})
                    price_children = min_ele.findChildren("option")
                    for price in price_children:
                        try:
                            text = int(price.text.replace("$", ""))
                            value = int(price["value"])
                            self._max_prices[text] = value
                        except ValueError:
                            pass
                """
            except Exception as e:
                current_app.logger.exception(e)

    """
    The guitar center search does not pass the actual monetary values, it uses the value attribute of the items
    in the <select> drop down. This function takes the min/max values from the search and gets the appropriate
    IDs to use in the GET.
    """
    """
    def get_price_ids(self, min_value, max_value):
        price_ids = []
        # No min value, we'll set it to 0.
        if min_value is None:
            min_value = 0
        # No max value, let's set it really high.
        if max_value is None:
            max_value = 1000000
        for price in self._min_prices:
            if price >= min_value and price < max_value:
                price_ids.append(str(self._min_prices[price]))
        return price_ids
    """

    def search_used(
        self, search_term, min_value, max_value, site_id, filter_options=None
    ):
        self.initialize()
        listings = []
        if self._driver:
            try:
                # Parameters for the search term
                # Ntt = search term
                # Ns = ?
                # price=Min-Max
                # Build price IDs
                # price_ids = self.get_price_ids(min_value, max_value)
                url_template = f"{self._base_used_url}?Ntt={search_term}&Ns=r&price={min_value}-{max_value}"
                self._driver.get(url_template)
                soup = BeautifulSoup(self._driver.page_source, "html.parser")
                listings = gc_listings()
                listings.parse(soup=soup, site_id=site_id)
                current_app.logger.debug(
                    "Query has: {rec_cnt} results.".format(rec_cnt=len(listings))
                )
            except Exception as e:
                current_app.logger.exception(e)
            self._driver.quit()
            self._driver = None

        return listings


def main():
    gc_api = guitarcenter_api()
    gc_api.search_used("belle epoch deluxe", 100, 500)
    return


if __name__ == "__main__":
    main()
