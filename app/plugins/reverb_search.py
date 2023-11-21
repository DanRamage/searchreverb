import time
import os
from base_search import base_search

# from results import listing, listings
import configparser
from reverb_api import reverb_api


class ItemSearch(base_search):
    def __init__(self, logger):
        super().__init__(logger)
        self._plugin_name = "Reverb"

    def search(self, user, search_rec, site_id):
        start_time = time.time()
        try:
            # Get the ini file.
            ini_filename = os.path.join(self._plugin_path, f"{self._plugin_name}.ini")
            config_file = configparser.RawConfigParser()
            config_file.read(ini_filename)
            oath_token = config_file.get("settings", "OAUTH_TOKEN")
        except Exception as e:
            self._logger.exception(e)
        else:
            try:
                search_obj = reverb_api(oauth_token=oath_token, logger=self._logger)

                # for search_rec in search_recs:
                query_params = {
                    "query": search_rec.search_item,
                    "price_max": search_rec.max_price,
                }
                if search_rec.min_price is not None:
                    query_params["price_min"] = search_rec.min_price
                if search_rec.item_region is not None:
                    query_params["item_region"] = search_rec.item_region

                # Split the category value apart in an attempt to better filter results.
                # On Add Item screen we create the full category hierarchy using the category and subcategory slugs.
                if search_rec.category is not None and len(search_rec.category):
                    category, product_type = search_rec.category.split("/")
                    query_params["category"] = category.strip()
                    query_params["product_type"] = product_type.strip()

                self._logger.debug(
                    "Running query for Email: %s Query params: %s"
                    % (user.email, search_rec.search_item)
                )
                get_location = True
                if user.zipcode is not None and search_rec.filter_radius is not None:
                    get_location = True

                listings = search_obj.search_listings(
                    site_id=site_id, get_location=get_location, **query_params
                )

            except Exception as e:
                self._logger.exception(e)

            self._logger.info(
                f"{self._plugin_name} finished searches in {time.time()-start_time} seconds."
            )

            return listings
