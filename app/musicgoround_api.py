import logging.config
from re import sub
from decimal import Decimal

from bs4 import BeautifulSoup
from flask import current_app
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from .results import listing, listings


class musicgoround_listing(listing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger = kwargs.get("logger", None)
        logger
        product = kwargs.get("product", None)
        site_id = kwargs.get("site_id")
        site_id
        base_url = kwargs.get("base_url", "https://www.musicgoround.com")

        if product:
            try:
                # There doesn't seem to be a unique product id. It looks like their SKU/ID is
                # part of the link to the product, so we'll pick that out and hash and use it.
                card_image = product.find("a").get("href")
                link_tag = card_image
                self._link = f"{base_url}{link_tag}"

                href_parts = card_image.split("/")
                # The part we want is something like: '41115-S000097780' we split on the '-' and use the
                # S000097780 part for the hash since that seems to be the sku.
                try:
                    # /product/40112-S000166469/used-marshall-vintage-lead-12-model-5005-guitar-combo-amplifier
                    # We hope the product is always in the path and that the SKU is the next element.
                    product_id = None
                    product_ndx = href_parts.index("product")
                    if len(href_parts) >= product_ndx + 1:
                        product_id = href_parts[product_ndx + 1]
                except Exception:
                    product_id = None
                if product_id is not None:
                    # The product id now has "site" prepended, we assign it and then strip "site" out of it.
                    id, sku = product_id.split("-")
                    self._id = hash(sku)
                    # self._id = int(product.find("var", class_="hidden displayId").text)
                    card_body = product.find("div", class_="card-body")
                    if card_body:
                        self._listing_description = str(
                            card_body.find("h3").text
                        ).strip()
                    price = card_body.find("p", class_="card-text--price").text.strip()
                    try:
                        self._price = float(Decimal(sub(r"[^\d.]", "", price)))
                    except (ValueError, Exception) as e:
                        raise e
                    # Condition and city, state div.
                    """
                    <div class="card-text--meta mt-auto text-white-50">
                        <small>Used</small>
                        <!---->
                        <span class="px-2">|</span>
                        <small>Aurora, CO</small><
                    /div>
                    """
                    condition_location_tag = card_body.find(
                        "div", class_="card-text--meta"
                    ).findAll("small")
                    # The first <small> is the condition, the next is the location.
                    for ndx, tag in enumerate(condition_location_tag):
                        if ndx == 0:
                            # There's no real condition text on the card, just Used and New.
                            self._condition = tag.text.strip()
                        elif ndx == 1:
                            self._locality, self._region = tag.text.split(",")
                            self._locality = self._locality.strip()
                            self._region = self._region.strip()

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


class musicgoround_listings(listings):
    def parse(self, **kwargs):
        soup = kwargs.get("soup", None)
        site_id = kwargs.get("site_id", -1)
        if soup:
            listing_container = soup.find("div", {"class": "product-list-grid"})
            if listing_container:
                product_cards = listing_container.findAll("product-product-card")
                for product in product_cards:
                    try:
                        listing = musicgoround_listing(
                            product=product, site_id=site_id, logger=current_app.logger
                        )
                        self._listings.append(listing)
                    except Exception as e:
                        current_app.logger.exception(e)
                if len(self._listings):
                    self._listings.sort(key=lambda item: item.price)


logger = logging.getLogger()


class musicgoround_api:
    def __init__(self, **kwargs):
        self._base_used_url = "https://www.musicgoround.com/products"

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
                # self._driver.get(self._base_used_url)
            except Exception as e:
                current_app.logger.exception(e)

    def search_used(
        self, search_term, min_value, max_value, site_id, filter_options=None
    ):
        self.initialize()
        listings = []
        if self._driver:
            try:
                # Parameters for the search term
                # search = search term
                # maxPrice=Max Price
                # minPrice = Minimum Price
                min_value_str = ""
                if min_value:
                    min_value_str = f"&minPrice={min_value}"
                max_value_str = ""
                if max_value:
                    max_value_str = f"&maxPrice={max_value}"
                url_template = f"{self._base_used_url}?search={search_term}{min_value_str}{max_value_str}"
                current_app.logger.debug(f"mgr url: {url_template}")
                self._driver.get(url_template)
                # We need to wait until
                element = None
                try:
                    element = WebDriverWait(self._driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "product-list"))
                    )
                    element
                except (TimeoutError, Exception) as e:
                    current_app.logger.error(
                        f"{url_template}: Page element never found."
                    )
                    current_app.logger.exception(e)
                finally:
                    soup = BeautifulSoup(self._driver.page_source, "html.parser")
                    listings = musicgoround_listings()
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
    mgr_api = musicgoround_api()
    mgr_api.search_used("belle epoch deluxe", 100, 500)
    return


if __name__ == "__main__":
    main()
