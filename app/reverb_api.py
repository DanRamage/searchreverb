import logging
import time
from datetime import datetime
from urllib.parse import urlparse

import requests

from .results import listing, listings


class reverb_listing(listing):
    def __init__(self, **kwargs):
        try:
            reverb_rec = kwargs["reverb_rec"]
            site_id = kwargs["site_id"]
            self._id = int(reverb_rec["id"])
            self._price = float(reverb_rec["price"]["amount"])
            self._listing_description = reverb_rec["title"]
            self._condition = reverb_rec["condition"]["display_name"]
            self._link = reverb_rec["_links"]["web"]["href"]
            self._currency = reverb_rec["price"]["currency"]
            self._region = ""
            self._locality = ""
            self._country_code = ""
            self._search_site_id = site_id
            self._local_pickup_only = False

        except Exception as e:
            raise e


class reverb_listings(listings):
    def parse(self, **kwargs):
        logger = logging.getLogger()
        listings = kwargs.get("listings", None)
        site_id = kwargs.get("site_id", -1)
        get_location = kwargs.get("get_location", False)
        if listings:
            for rec in listings:
                try:
                    reverb_rec = reverb_listing(site_id=site_id, reverb_rec=rec)
                    # If we are limiting the results based on a search radius, we'll need
                    # to query the link in the result to get the actual item listing so we can then
                    # get the city,state,country info.
                    if get_location:
                        try:
                            listing_url = rec["_links"]["self"]["href"]
                            site_listing = requests.get(listing_url)
                            if site_listing.status_code == 200:
                                json_listing = site_listing.json()
                                reverb_rec.region = json_listing["location"]["region"]
                                reverb_rec.locality = json_listing["location"][
                                    "locality"
                                ]
                                reverb_rec.country_code = json_listing["location"][
                                    "country_code"
                                ]
                                reverb_rec.local_pickup_only = json_listing[
                                    "local_pickup_only"
                                ]
                            else:
                                logger.error(
                                    f"Error querying the item listing: {listing_url}"
                                )
                        except Exception as e:
                            logger.exception(e)
                    self._listings.append(reverb_rec)
                except Exception:
                    pass

            self._listings.sort(key=lambda item: item.price)


class reverb_base:
    def __init__(self, url, oauth_token, logger):
        self._base_url = url
        self._oauth_token = oauth_token
        self._logger = logger

    def get(self, url, **kwargs):
        payload = {}
        for key in kwargs:
            payload[key] = kwargs[key]

        headers = {
            "Authorization": "Bearer %s" % (self._oauth_token),
            "Content-Type": "application/hal+json",
            "Accept": "application/hal+json",
            "Accept-Version": "3.0",
        }
        self._logger.debug("URL: %s Request params: %s" % (url, payload))
        try:
            req = requests.get(url, headers=headers, params=payload, timeout=15)
        except Exception as e:
            self._logger.exception(e)
        return req


class reverb_api(reverb_base):
    def __init__(
        self, oauth_token, logger, results_limit=100, url="https://api.reverb.com/api"
    ):
        super().__init__(url, oauth_token, logger)
        self.item_results = []
        self.run_time = datetime.utcnow()
        # This is the number of results we will limit ourselves to.
        self._results_limit = results_limit

    def search_listings(self, site_id, get_location, **kwargs):
        start_search = time.time()
        listings = []
        try:
            url = "%s/%s" % (self._base_url, "listings/all")
            results = self.get(url=url, **kwargs)
            if results.status_code == 200:
                stop_at_page = None
                results = results.json()
                total_listings = results["total"]
                total_pages = results["total_pages"]
                if total_listings > self._results_limit:
                    self._logger.warning(
                        "Query has: %d results, our limit is: %d"
                        % (total_listings, self._results_limit)
                    )
                else:
                    self._logger.debug("Query has: %d results." % (total_listings))

                listings.extend(results["listings"])
                if "next" in results["_links"]:
                    current_page = 1
                    next_url = results["_links"]["next"]["href"]
                    self._logger.debug("Next url: %s" % (next_url))
                    # We want to limit our queries, so let's not return anymore than N results.
                    url_parts = urlparse(next_url)
                    query_parts = dict(
                        param.split("=") for param in url_parts.query.split("&")
                    )
                    # Based on the results returned per query and the current page, we will limit our results.
                    stop_at_page = int(
                        self._results_limit / int(query_parts["per_page"])
                    )

                    paginate = True
                    while paginate:
                        # Make sure we just don't endlessly query, so we check to see if we've hit our limit on
                        # total number of listings to return, or we've hit the total_pages from the initial result.
                        if (stop_at_page and current_page >= stop_at_page) or (
                            current_page == total_pages
                        ):
                            paginate = False
                        current_page += 1
                        next_req = self.get(url=next_url)
                        if next_req.status_code == 200:
                            next_results = next_req.json()
                            listings.extend(next_results["listings"])
                            if "next" in next_results["_links"]:
                                next_url = next_results["_links"]["next"]["href"]
                            else:
                                paginate = False

        except Exception as e:
            self._logger.exception(e)
        self._logger.debug(
            "search finished in %f seconds" % (time.time() - start_search)
        )

        normalized_listings = reverb_listings()
        normalized_listings.parse(
            listings=listings, site_id=site_id, get_location=get_location
        )

        return normalized_listings

    def categories(self):
        start_search = time.time()
        json_results = None
        try:
            url = "%s/%s" % (self._base_url, "categories")
            results = self.get(url=url, **{})
            json_results = results.json()
        except Exception as e:
            self._logger.exception(e)
        self._logger.debug(
            "search finished in %f seconds" % (time.time() - start_search)
        )
        return json_results
