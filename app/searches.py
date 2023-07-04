import os
import time
from datetime import datetime

import pyproj
import requests
from flask import current_app
from mako import exceptions as makoExceptions
from mako.template import Template
from shapely.geometry import Point
from shapely.ops import transform
from sqlalchemy.exc import IntegrityError

from app import db
from config import *
from config import BING_MAP_API_KEY
from smtp_utils import smtpClass

from .admin_models import User
from .gc_api import guitarcenter_api
from .reverb_api import reverb_api
from .reverb_models import NormalizedSearchResults, SearchItem, SearchSite


def reproject_func(in_proj, out_proj):
    return pyproj.Transformer.from_crs(in_proj, out_proj, always_xy=True).transform


class search_result:
    def __init__(self, search_rec):
        self._search_rec = search_rec
        self._search_site_results = {}

    def add_search_site_results(self, search_site_name, results):
        self._search_site_results[search_site_name] = results

    @property
    def search_rec(self):
        return self._search_rec

    @property
    def search_site_results(self):
        return self._search_site_results


class searches:
    def __init__(self):
        self._listings = []
        self._search_results = {}
        self._reproj_func = reproject_func("EPSG:4326", "EPSG:3857")

    def do_searches(self, send_emails):
        start_time = time.time()
        try:
            email_results = send_emails

            users = db.session.query(User).all()
            # Get all the sites we're going to search.
            search_site_recs = db.session.query(SearchSite).all()

            self._search_results = {}
            # Loop each user, querying their searches.
            for user in users:
                search_results = []
                search_recs = (
                    db.session.query(SearchItem)
                    .filter(SearchItem.user_id == user.id)
                    .all()
                )

                for search_rec in search_recs:
                    result = search_result(search_rec)

                    for site_rec in search_site_recs:
                        query_start_time = time.time()
                        current_app.logger.info(
                            "Running {site_name} queries.".format(
                                site_name=site_rec.site_name
                            )
                        )
                        if site_rec.site_name == "Guitar Center":
                            listings = self.gc_search(user, search_rec, site_rec.id)
                        elif site_rec.site_name == "Reverb":
                            listings = self.reverb_search(user, search_rec, site_rec.id)
                        current_app.logger.info(
                            "Finished {site_name} queries in {time} seconds".format(
                                site_name=site_rec.site_name,
                                time=time.time() - query_start_time,
                            )
                        )
                        # If we get any results, process them. We add new results to the DB, trim
                        # out records that are no longer listed.
                        if len(listings):
                            # If the user put in a zipcode, and the search query has a filter radius,
                            # let's iterate the listing and get rid of results not in the radius.
                            if (
                                user.zipcode is not None
                                and search_rec.filter_radius is not None
                            ):
                                filtered_listings = self.distance_filter(
                                    listings, user, search_rec.filter_radius
                                )
                                current_app.logger.debug(
                                    f"Filtered listings from: {len(listings)} to "
                                    f"{len(filtered_listings)}"
                                )
                                listings = filtered_listings

                            results_to_report = self.process_normalized_results(
                                user, search_rec, listings, site_rec
                            )
                            if len(results_to_report):
                                result.add_search_site_results(
                                    site_rec.site_name, results_to_report
                                )
                    if len(result.search_site_results):
                        search_results.append(result)
                # Save the results to an HTML file, then email them to the user.
                if len(search_results):
                    self.output_normalized_results(search_results, user, email_results)

        except Exception as e:
            current_app.logger.exception(e)
        db.session.close()

        current_app.logger.debug(
            "Finished run_searches in %f seconds" % (time.time() - start_time)
        )

    def bing_geo_query(self, api_key, **kwargs):
        url_template = f"http://dev.virtualearth.net/REST/v1/Locations?key={api_key}"
        locality = kwargs.get("locality", None)
        if locality is not None:
            url_template += f"&locality={locality}"
        region = kwargs.get("region", None)
        if region is not None:
            url_template += f"&admin_district={region}"
        zipcode = kwargs.get("zipcode", None)
        if zipcode is not None:
            url_template += f"&postalCode={zipcode}"
        try:
            point = None
            req = requests.get(url_template)
            if req.status_code == 200:
                json_req = req.json()
                if "resourceSets" in json_req:
                    if len(json_req["resourceSets"]):
                        coords = json_req["resourceSets"][0]["resources"][0]["point"][
                            "coordinates"
                        ]
                        point = Point(coords[1], coords[0])
        except Exception as e:
            raise e
        return point

    def distance_filter(self, listings, user_rec, filter_radius):
        filtered_listings = []
        # Let's check the user_rec to see if we have a lat/lon for the zip, if not,
        # let's get that and save it.
        if user_rec.latitude is None or user_rec.longitude is None:
            user_loc_point = self.bing_geo_query(
                BING_MAP_API_KEY, zipcode=user_rec.zipcode
            )
            user_rec.longitude = user_loc_point.x
            user_rec.latitude = user_loc_point.y
            try:
                db.session.commit()
            except Exception as e:
                current_app.logger.exception(e)
        else:
            user_loc_point = Point(user_rec.longitude, user_rec.latitude)
        for listing in listings:
            # Transform to 3857.
            user_point = transform(self._reproj_func, user_loc_point)
            allowable_radius = filter_radius * MILES_TO_METERS
            if listing.region is not None and listing.locality is not None:
                listing_point = self.bing_geo_query(
                    BING_MAP_API_KEY, region=listing.region, locality=listing.locality
                )
                # Transform to 3857.
                data_pt = transform(self._reproj_func, listing_point)
                item_distance = user_point.distance(data_pt)
                if item_distance <= allowable_radius:
                    current_app.logger.debug(
                        f"Listing: {listing.listing_description} Loc: {listing.locality},{listing.region} "
                        f"within radius:{allowable_radius/MILES_TO_METERS} {item_distance/MILES_TO_METERS}"
                    )
                    filtered_listings.append(listing)
                else:
                    current_app.logger.debug(
                        f"Listing: {listing.listing_description} Loc: {listing.locality},{listing.region} "
                        f"outside radius:{allowable_radius/MILES_TO_METERS} {item_distance/MILES_TO_METERS}"
                    )

        return filtered_listings

    def reverb_search(self, user, search_rec, site_id):
        try:
            search_obj = reverb_api(oauth_token=OAUTH_TOKEN, logger=current_app.logger)
            listings = []

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

            current_app.logger.debug(
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
            current_app.logger.exception(e)

        return listings

    def gc_search(self, user, search_rec, site_id):
        start_time = time.time()
        try:
            search_obj = guitarcenter_api()

            listings = []
            # for search_rec in search_recs:
            current_app.logger.debug(
                f"Running query for Email: {user.email} Item: {search_rec.search_item}"
            )

            listings = search_obj.search_used(
                search_rec.search_item,
                search_rec.min_price,
                search_rec.max_price,
                site_id,
            )
            if user.zipcode is not None:
                user.zipcode
        except Exception as e:
            current_app.logger.exception(e)
        current_app.logger.debug(
            f"gc_search finished in {time.time() - start_time} seconds."
        )
        return listings

    def process_normalized_results(self, user_rec, search_rec, listings, search_site):
        try:
            results_to_report = []

            # Figure out if we have new results, so we query the database then do some set operations.
            prev_search_results = (
                db.session.query(NormalizedSearchResults)
                .filter(NormalizedSearchResults.search_id == search_rec.id)
                .filter(NormalizedSearchResults.search_site_id == search_site.id)
                .all()
            )

            current_search_set = set()
            prev_search_set = set()
            price_change_listings = []

            for listing in listings:
                # Create a set of the current results. We'll use set operations to figure out what's new and then what's
                # no longer available.
                current_search_set.add((listing.id, listing.search_site_id))

            if len(prev_search_results):
                row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Create a set of the local cache of last search results
                for prev_search_result in prev_search_results:
                    prev_search_set.add(
                        (
                            prev_search_result.search_item_id,
                            prev_search_result.search_site_id,
                        )
                    )

                    # Let's also check to see if there are any price changes, if so we'll add them to the results.
                    try:
                        listing = next(
                            (
                                listing
                                for listing in listings
                                if prev_search_result.search_item_id == listing.id
                            ),
                            None,
                        )
                        if listing:
                            if listing.price != prev_search_result.last_price:
                                current_app.logger.debug(
                                    "%s price change detected for item: %d From: %s to %s"
                                    % (
                                        search_site.site_name,
                                        prev_search_result.search_item_id,
                                        str(prev_search_result.last_price),
                                        str(listing.price),
                                    )
                                )
                                price_change_listings.append(listing)
                                # Update the database record with the new current price.
                                try:

                                    prev_search_result.row_update_date = row_entry_date
                                    prev_search_result.last_price = float(listing.price)
                                    db.session.commit()
                                except Exception as e:
                                    db.session.rollback()
                                    current_app.logger.error(
                                        "%s(%d) error updating the search record: %d Site: %d price."
                                        % (
                                            search_site.site_name,
                                            search_site.id,
                                            search_rec.id,
                                            search_rec.search_site_id,
                                        )
                                    )
                                    current_app.logger.exception(e)

                    except Exception as e:
                        current_app.logger.exception(e)

            # Now let's figure out what's new.
            new_results = current_search_set.difference(prev_search_set)

            # IF we are sending all results, set the results_to_report to the listings.
            if not search_rec.show_new_results_only:
                results_to_report = listings
            else:
                # If we are showing only new results, populate results_to_report with the ids we just received that
                # aren't stored from a previous results query.
                results_to_report = [
                    listing
                    for listing in listings
                    if (listing.id, listing.search_site_id) in new_results
                ]
                # If we have any price changes, we want to add them to our results_to_report. We add them only when
                # we are showing new results only since they would already be included if we are sending all results.
                if price_change_listings:
                    results_to_report.extend(price_change_listings)

            # We save the new results to the database.
            if len(new_results):
                row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for new_result_id, search_site_id in new_results:
                    try:
                        current_app.logger.debug(
                            "%s new results %d for user: %s search: %s(%d)"
                            % (
                                search_site.site_name,
                                new_result_id,
                                user_rec.email,
                                search_rec.search_item,
                                search_rec.id,
                            )
                        )
                        # Find the list record based on id so we can get the price.
                        listing_rec = next(
                            listing
                            for listing in listings
                            if new_result_id == listing.id
                        )
                        new_result = NormalizedSearchResults(
                            row_entry_date=row_entry_date,
                            search_item_id=new_result_id,
                            search_id=search_rec.id,
                            last_price=float(listing_rec.price),
                            search_site_id=listing_rec.search_site_id,
                        )
                        db.session.add(new_result)
                        db.session.commit()
                    except IntegrityError as e:
                        current_app.logger.exception(e)
                        db.session.rollback()
                    except Exception as e:
                        current_app.logger.exception(e)
                        db.session.rollback()

            else:
                current_app.logger.debug(
                    "%s no new results for user: %s search: %s(%d)"
                    % (
                        search_site.site_name,
                        user_rec.email,
                        search_rec.search_item,
                        search_rec.id,
                    )
                )

            # Now figure out if old listings have been removed and clean up our table.
            deleted_search_results = prev_search_set.difference(current_search_set)
            if len(deleted_search_results):
                for deleted_results in deleted_search_results:
                    current_app.logger.debug(
                        "%s search item: %d is no longer in the current results, removing from db"
                        % (search_site.site_name, deleted_results[0])
                    )
                    try:
                        db.session.query(NormalizedSearchResults).filter(
                            NormalizedSearchResults.search_item_id == deleted_results[0]
                        ).filter(
                            NormalizedSearchResults.search_site_id == deleted_results[1]
                        ).delete()
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        current_app.logger.exception(e)

        except Exception as e:
            current_app.logger.exception(e)

        return results_to_report

    def output_normalized_results(self, search_results, user, email_results):
        run_time = datetime.now()
        file_attach_list = []
        for result in search_results:
            try:
                template_path = os.path.join(
                    current_app.root_path, EMAIL_TEMPLATE_NORMALIZED
                )
                email_template = Template(filename=template_path)
                template_output = email_template.render(
                    user=user.email,
                    search_rec=result.search_rec,
                    search_results=result.search_site_results,
                    search_execute_time=run_time.strftime("%Y-%m-%d %H:%M"),
                )
            except Exception:
                current_app.logger.exception(
                    makoExceptions.text_error_template().render()
                )
            else:
                try:
                    filename = "%d_%d_results_%s" % (
                        user.id,
                        result.search_rec.id,
                        run_time.strftime("%Y-%m-%d_%H_%M"),
                    )
                    out_file = os.path.join(
                        current_app.root_path,
                        f"{RESULTS_TEMP_DIRECTORY}",
                        f"{filename}.html",
                    )
                    with open(out_file, "w") as file_obj:
                        current_app.logger.debug("Saving results file: %s" % (out_file))
                        file_obj.write(template_output)
                        file_attach_list.append(out_file)
                except Exception as e:
                    current_app.logger.exception(e)
        if email_results and len(file_attach_list):
            try:
                current_app.logger.debug("Emailing user: %s" % (user.email))
                email_obj = smtpClass(
                    host=EMAIL_HOST,
                    user=EMAIL_USER,
                    password=EMAIL_PWD,
                    port=EMAIL_PORT,
                    use_tls=EMAIL_USE_TLS,
                )
                email_obj.from_addr("%s@%s" % (EMAIL_USER, EMAIL_HOST))
                email_obj.rcpt_to([user.email])
                # email_obj.message(template_output)
                for file_to_attach in file_attach_list:
                    email_obj.attach(file_to_attach)
                email_obj.message("See attachment for results.")
                email_obj.subject("Reverb Search Results")
                email_obj.send(content_type="html", charset="UTF-8")

            except Exception as e:
                current_app.logger.exception(e)
            else:
                # If we succeeded in sending the email, let's update the last_email_date.
                try:
                    for result in search_results:
                        result.search_rec.last_email_date = run_time.strftime(
                            "%Y-%m-%dT%H:%M:%S"
                        )
                        db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(
                        "Error attempting to update the last_email_date for search item: %d"
                        % (result.search_rec.id)
                    )
                    current_app.logger.exception(e)

        return
