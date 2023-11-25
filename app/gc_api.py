import logging.config
from re import sub
from decimal import Decimal
import requests

# from bs4 import BeautifulSoup
from flask import current_app
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from .results import listing, listings


class gc_listing(listing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        type = kwargs.get("response_type", "html")
        if type == "html":
            self.parse_html(**kwargs)
        elif type == "json":
            self.parse_json(**kwargs)

    def parse_json(self, **kwargs):
        product = kwargs.get("product", None)
        site_id = kwargs.get("site_id")
        self._search_site_id = site_id

        if "displayName" in product:
            self._listing_description = product["displayName"]
        if "productId" in product:
            prod_id = product["productId"]
            self._id = int(prod_id.replace("site", ""))
        if "price" in product:
            price = product["price"]
            try:
                self._price = float(Decimal(sub(r"[^\d.]", "", price)))
            except (ValueError, Exception) as e:
                raise e
        if "usedCondition" in product:
            self._condition = product["usedCondition"]
        if "linkUrl" in product:
            self._link = f"https://www.guitarcenter.com/{product['linkUrl']}"
        if "storeName" in product:
            store_location = product["storeName"]
            self._locality, self._region = store_location.split(",")
            self._locality = self._locality.strip()
            self._region = self._region.strip()

    def parse_html(self, **kwargs):
        logger = kwargs.get("logger", None)
        product = kwargs.get("product", None)
        site_id = kwargs.get("site_id")
        if product:
            try:
                self._search_site_id = site_id
                self._locality = self._region = None
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
        parse_type = kwargs.get("type", None)
        if parse_type == "json":
            self.parse_json(**kwargs)
        else:
            self.parse_html(**kwargs)

    def parse_json(self, **kwargs):
        json_response = kwargs["json"]
        site_id = kwargs.get("site_id", -1)
        if "products" in json_response:
            products = json_response["products"]
            for product in products:
                try:
                    listing = gc_listing(
                        product=product,
                        site_id=site_id,
                        logger=current_app.logger,
                        response_type="json",
                    )
                    self._listings.append(listing)
                except Exception as e:
                    current_app.logger.exception(e)

        return

    def parse_html(self, **kwargs):
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
                            product=product,
                            site_id=site_id,
                            logger=current_app.logger,
                            response_type="html",
                        )
                        self._listings.append(listing)
                    except Exception as e:
                        current_app.logger.exception(e)
                if len(self._listings):
                    self._listings.sort(key=lambda item: item.price)


logger = logging.getLogger()


class guitarcenter_api:
    def __init__(self, **kwargs):
        self._base_used_url = "https://www.guitarcenter.com/rest/model/ngp/rest/actor/SearchActor/RedesignSearch"
        # self._base_used_url = "https://www.guitarcenter.com/Used"
        self._base_applied_filter_url = (
            "https://www.guitarcenter.com/ajax/storeLocation/findInStoreList.jsp"
        )
        self._firefox_binary = "/Applications/Firefox.app/Contents/MacOS/firefox"
        self._geckodriver_binary = "/usr/local/bin/geckodriver"

        self._driver = None
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
        listings = []
        # GC changed their search to now use an API that returns JSON.
        """
        #Latest params:
        ?N=1076
        &Ns=cD
        &Ntt=soldano%20slo%2030
        &Nao=0
        &price=300-2700
        &pageName=used-page
        &recsPerPage=24
        &postalCode=
        &profileCountryCode=US
        &profileCurrencyCode=USD
        &SPA=true
        """
        try:
            url_template = (
                f"{self._base_used_url}?N=1076&Ns=cD&Ntt={search_term}&Nao=0"
                f"&price={min_value}-{max_value}&pageName=used-page"
                f"&recsPerPage=50&postalCode=&profileCountryCode=US&profileCurrencyCode=USD"
                f"SPA=true"
            )
            current_app.logger.debug(f"gc url: {url_template}")
            req = requests.get(url_template)
            if req.status_code == 200:
                listings = gc_listings()
                listings.parse(json=req.json(), site_id=site_id, type="json")
                current_app.logger.debug(
                    "Query has: {rec_cnt} results.".format(rec_cnt=len(listings))
                )
            else:
                current_app.logger.error(
                    f"GC search_used failed. Status Code: {req.status_code}"
                )
        except Exception as e:
            current_app.logger.exception(e)
        """
        self.initialize()
        listings = []
        if self._driver:
            try:
                url_template = (f"{self._base_used_url}?N=1076&Ns=cD&Ntt={search_term}&Nao=0"
                                f"&price={min_value}-{max_value}&pageName=used-page"
                                f"&recsPerPage=50&postalCode=&profileCountryCode=US&profileCurrencyCode=USD"
                                f"SPA=true")
                current_app.logger.debug(f"gc url: {url_template}")
                req = requests.get(url_template)

                self._driver.get(url_template)
                soup = BeautifulSoup(self._driver.page_source, "html.parser")
                listings = gc_listings()
                listings.parse(soup=soup, site_id=site_id, type="json")
                current_app.logger.debug(
                    "Query has: {rec_cnt} results.".format(rec_cnt=len(listings))
                )
            except Exception as e:
                current_app.logger.exception(e)
            self._driver.quit()
            self._driver = None
        """
        return listings


def main():
    gc_api = guitarcenter_api()
    gc_api.search_used("belle epoch deluxe", 100, 500)
    return


if __name__ == "__main__":
    main()
