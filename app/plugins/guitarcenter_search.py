import logging
import time
from re import sub
from decimal import Decimal
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from base_search import base_search
from results import listing, listings


class gc_listing(listing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        product = kwargs.get("product", None)
        site_id = kwargs.get("site_id")
        if product:
            try:
                self._search_site_id = site_id
                product_id = product.find("div", attrs={"data-product-sku-id": True})
                if product_id is not None:
                    # The product id now has "site" prepended, we assign it and then strip "site" out of it.
                    self._id = product_id.attrs["data-product-sku-id"]
                    if "site" in self._id:
                        self._id = int(self._id.replace("site", ""))
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
                else:
                    raise Exception("No product found.")
            except Exception as e:
                raise e
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


class gc_listings(listings):
    def __init__(self, logger):
        super().__init__()
        self._logger = logger

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
                        listing = gc_listing(product=product, site_id=site_id)
                        self._listings.append(listing)
                    except Exception as e:
                        self._logger.exception(e)
                if len(self._listings):
                    self._listings.sort(key=lambda item: item.price)


class guitarcenter_api:
    def __init__(self, **kwargs):
        self._logger = kwargs.get("logger", None)
        if self._logger is None:
            self._logger = logging.getLogger()
        self._base_used_url = kwargs.get(
            "base_url", "https://www.guitarcenter.com/Used"
        )
        self._firefox_binary = kwargs.get(
            "firefox_binary", "/Applications/Firefox.app/Contents/MacOS/firefox"
        )
        self._geckodriver_binary = kwargs.get(
            "geckodriver_binary", "/usr/local/bin/geckodriver"
        )

        self._driver = None
        self._min_prices = {}
        self._max_prices = {}

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
                self._driver.get(self._base_used_url)
            except Exception as e:
                self._logger.exception(e)

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
                listings = gc_listings(self._logger)
                listings.parse(soup=soup, site_id=site_id)
                self._logger.debug(
                    "Query has: {rec_cnt} results.".format(rec_cnt=len(listings))
                )
            except Exception as e:
                self._logger.exception(e)
            self._driver.quit()
            self._driver = None

        return listings


class ItemSearch(base_search):
    def __init__(self, logger):
        super().__init__(logger)
        self._plugin_name = "Guitar Center"

    def search(self, user, search_rec, site_id):
        start_time = time.time()
        try:
            search_obj = guitarcenter_api()

            self._logger.debug(
                f"Running query for Email: {user.email} Item: {search_rec.search_item}"
            )

            self._listings = search_obj.search_used(
                search_rec.search_item,
                search_rec.min_price,
                search_rec.max_price,
                site_id,
            )
            if user.zipcode is not None:
                user.zipcode
        except Exception as e:
            self._logger.exception(e)
        self._logger.debug(f"gc_search finished in {time.time() - start_time} seconds.")
        return
