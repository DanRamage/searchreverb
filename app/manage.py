"""
To use the command line interface you have to:
Load the python venv(source /path/to/python/venv/bin/activate
export FLASK_APP=<fullpathto>/manage.py
"""
import sys
sys.path.append('../commonfiles/python')
import os
import os
import click
from flask import Flask, current_app, redirect, url_for, request
import logging.config
from logging.handlers import RotatingFileHandler
from logging import Formatter
import time
from app import db
from config import *
from datetime import datetime
from shapely.wkb import loads as wkb_loads
import json
import requests
from shapely.geometry import Point, Polygon, box
from werkzeug.security import generate_password_hash, check_password_hash
from mako.template import Template
from mako import exceptions as makoExceptions
from sqlalchemy.exc import IntegrityError

from smtp_utils import smtpClass
from .reverb_models import SearchItem, SearchResults
from .admin_models import Role, User, Roles_Users
from .reverb_api import reverb_api
app = Flask(__name__)
db.app = app
db.init_app(app)
# Create in-memory database
app.config['DATABASE_FILE'] = DATABASE_FILE
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_ECHO'] = SQLALCHEMY_ECHO

def init_logging(app):
  app.logger.setLevel(logging.DEBUG)
  file_handler = RotatingFileHandler(filename = LOGFILE)
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(Formatter('%(asctime)s,%(levelname)s,%(module)s,%(funcName)s,%(lineno)d,%(message)s'))
  app.logger.addHandler(file_handler)

  app.logger.debug("Logging initialized")

  return

@app.cli.command('database_maintenance')
@click.option('--params', nargs=0)
def database_maintenance(params):
  start_time = time.time()
  init_logging(app)
  current_app.logger.debug("database_maintenance started.")
  try:
    db.session.execute("VACUUM;")
    db.session.close()
  except Exception as e:
    current_app.logger.exception(e)
  #Now let's cleanup the temp directory.
  results_tmp_dir = os.path.join(app.root_path, RESULTS_TEMP_DIRECTORY)

  current_app.logger.debug("Cleaning up files older than: %d seconds" % (RESULTS_TEMP_AGE_OUT))
  for tmp_file in os.listdir(results_tmp_dir):
    try:
      tmp_file_path = os.path.join(results_tmp_dir, tmp_file)
      if os.stat(tmp_file_path).st_mtime < start_time - RESULTS_TEMP_AGE_OUT:
        if os.path.isfile(tmp_file_path):
          current_app.logger.debug("File: %s is older than cutoff, deleting." % (tmp_file_path))
          os.remove(tmp_file_path)
    except Exception as e:
      current_app.logger.error("Error when testing file: %s for deletion." % (tmp_file_path))
      current_app.logger.exception(e)
  current_app.logger.debug("database_maintenance completed in %f seconds." % (time.time()-start_time))
  return


@app.cli.command('create_roles')
@click.option('--params', nargs=2)
def create_roles(params):
  start_time = time.time()
  init_logging(app)
  roles = params[0].split(',')
  role_descriptions = params[1].split(',')
  row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  for ndx,role in enumerate(roles):
    try:
      current_app.logger.debug("Adding role: %s desc: %s" % (role, role_descriptions[ndx]))
      new_role = Role(row_entry_date=row_entry_date,
                       name=role,
                       description=role_descriptions[ndx])
      db.session.add(new_role)
      db.session.commit()
    except Exception as e:
      current_app.logger.exception(e)
  db.session.close()

  return


@app.cli.command('add_user')
@click.option('--params', nargs=4)
def add_user(params):
  start_time = time.time()
  init_logging(app)
  login = params[0]
  email_addr = params[1]
  password = params[2]
  roles_to_add = params[3].split(',')
  current_app.logger.debug("add_user started")
  try:
    test_user = User(login=login,
                     email=email_addr,
                     password=generate_password_hash(password))
    db.session.add(test_user)
    db.session.commit()
    #Create role map
    roles = db.session.query(Role).all()
    for role in roles:
      if role.name in roles_to_add:
        role_map = Roles_Users(user_id=test_user.id,
                           role_id=role.id)
        db.session.add(role_map)
    db.session.commit()


  except Exception as e:
    current_app.logger.exception(e)

  current_app.logger.debug("add_user finished in %f seconds" % (time.time()-start_time))

def process_results(user_rec, search_rec, listings):
  try:
    results_to_report = []
    #Figure out if we have new results, so we query the database then do some set operations.
    prev_search_results = db.session.query(SearchResults)\
                .filter(SearchResults.search_id == search_rec.id)\
                .all()

    current_search_set = set()
    prev_search_set = set()
    price_change_listings = []

    for listing in listings:
      # Create a set of the current results. We'll use set operations to figure out what's new and then what's
      # no longer available.
      current_search_set.add(listing['id'])

    if len(prev_search_results):
      row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      #Create a set of the local cache of last search results
      for prev_search_result in prev_search_results:
        prev_search_set.add(prev_search_result.search_item_id)

        # Let's also check to see if there are any price changes, if so we'll add them to the results.
        try:
          listing = next((listing for listing in listings if prev_search_result.search_item_id == listing['id']), None)
          if listing:
            if float(listing['price']['amount']) != prev_search_result.last_price:
              current_app.logger.debug("Price change detected for item: %d From: %s to %s" %
                                       (prev_search_result.search_item_id, str(prev_search_result.last_price),
                                        str(listing['price']['amount'])))
              price_change_listings.append(listing)
              # Update the database record with the new current price.
              try:

                prev_search_result.row_update_date = row_entry_date
                prev_search_result.last_price = float(listing['price']['amount'])
                db.session.commit()
              except Exception as e:
                db.session.rollback()
                current_app.logger.error("Error updating the search record: %d price." % (search_rec.id))
                current_app.logger.exception(e)

          '''
          for listing in listings:
            if listing['id'] == search_result.search_item_id:
              if float(listing['price']['amount']) != search_result.last_price:
                current_app.logger.debug("Price change detected for item: %d From: %s to %s" %
                                         (search_result.search_item_id,str(search_result.last_price),str(listing['price']['amount'])))
                price_change_listings.append(listing)
                #Update the database record with the new current price.

                try:
                  search_rec.last_price = float(listing['price']['amount'])
                  db.session.commit()
                except Exception as e:
                  db.session.rollback()
                  current_app.logger.error("Error updating the search record: %d price." % (search_rec.id))
                  current_app.logger.exception(e)
              break
            '''
        except Exception as e:
          current_app.logger.exception(e)

    #Now let's figure out what's new.
    new_results = current_search_set.difference(prev_search_set)

    #IF we are sending all results, set the results_to_report to the listings.
    if not search_rec.show_new_results_only:
      results_to_report = listings
    else:
      #If we are showing only new results, populate results_to_report with the ids we just received that
      #aren't stored from a previous results query.
      results_to_report = ([listing for listing in listings if listing['id'] in new_results])
      # If we have any price changes, we want to add them to our results_to_report. We add them only when
      # we are showing new results only since they would already be included if we are sending all results.
      if (price_change_listings):
        results_to_report.extend(price_change_listings)

    #We save the new results to the database.
    if len(new_results):
      row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      for new_result_id in new_results:
        try:
          current_app.logger.debug("New results %d for user: %s search: %s(%d)" % \
                                   (new_result_id, user_rec.email, search_rec.search_item, search_rec.id))
          #Find the list record based on id so we can get the price.
          listing_rec = next(listing for listing in listings if new_result_id == listing['id'])
          new_result = SearchResults(row_entry_date=row_entry_date,
                                     search_item_id=new_result_id,
                                     search_id=search_rec.id,
                                     last_price=float(listing_rec['price']['amount'])
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
      current_app.logger.debug("No new results for user: %s search: %s(%d)" %\
                               (user_rec.email, search_rec.search_item, search_rec.id))

    #Now figure out if old listings have been removed and clean up our table.
    deleted_search_results = prev_search_set.difference(current_search_set)
    if len(deleted_search_results):
      for deleted_results in deleted_search_results:
        current_app.logger.debug("Search item: %d is no longer in the current results, removing from db" % \
          (deleted_results))
        try:
          db.session.query(SearchResults)\
              .filter(SearchResults.search_item_id == deleted_results)\
              .delete()
          db.session.commit()
        except Exception as e:
          db.session.rollback()
          current_app.logger.exception(e)

  except Exception as e:
    current_app.logger.exception(e)

  return results_to_report

@app.cli.command('run_searches')
@click.option('--params', nargs=1)
def run_searches(params):
  #base_url = "http://127.0.0.1:5000/search"
  start_time = time.time()
  try:
    email_results = int(params)
    init_logging(app)

    users = db.session.query(User).all()
    search_obj = reverb_api(oauth_token=OAUTH_TOKEN, logger=current_app.logger)

    for user in users:
      search_recs = db.session.query(SearchItem)\
        .filter(SearchItem.user_id == user.id)\
        .all()
      search_results = []
      for search_rec in search_recs:
        query_params = { 'query': search_rec.search_item,
                          'price_max': search_rec.max_price,
                      }
        if search_rec.min_price is not None:
          query_params['price_min'] = search_rec.min_price
        if search_rec.item_region is not None:
          query_params['item_region'] = search_rec.item_region

        #Split the category value apart in an attempt to better filter results.
        #On Add Item screen we create the full category hierarchy using the category and subcategory slugs.
        if search_rec.category is not None and len(search_rec.category):
          category, product_type = search_rec.category.split('/')
          query_params['category'] = category.strip()
          query_params['product_type'] = product_type.strip()

        current_app.logger.debug("Running query for Email: %s Query params: %s" % (user.email, query_params))
        listings = search_obj.search_listings(**query_params)
        #Sort
        sorted_listings = sorted(listings, key=lambda item: float(item['price']['amount']))
        current_app.logger.debug("Sorted list of: %d results" % (len(sorted_listings)))

        if len(sorted_listings):
          results_to_report = process_results(user, search_rec, sorted_listings)
          #I may at some point have all the search results put into one file, so for now
          #pass the results_to_report as a list.
          if len(results_to_report):
            search_results.append((search_rec, results_to_report))
          #if len(results_to_report):
          #  output_results(current_app, [results_to_report], user, search_rec, email_results)
      if len(search_results):
        output_results(current_app, search_results, user, email_results)
  except Exception as e:
    current_app.logger.exception(e)

  db.session.close()

  current_app.logger.debug("Finished run_searches in %f seconds" % (time.time()-start_time))

  return

def output_results(app, search_results, user, email_results):
#def output_results(app, results, user, search_rec, email_results):
    run_time = datetime.now()
    file_attach_list = []
    for search_rec, results in search_results:
      try:
        template_path = os.path.join(app.root_path, EMAIL_TEMPLATE)
        email_template = Template(filename=template_path)
        template_output = email_template.render(user=user.email,
                                                search_rec=search_rec,
                                                search_results=[results],
                                                search_execute_time=run_time.strftime('%Y-%m-%d %H:%M'))
      except:
        app.logger.exception(makoExceptions.text_error_template().render())
      else:
        try:
          filename = "%d_%d_results_%s" % (user.id, search_rec.id, run_time.strftime('%Y-%m-%d_%H_%M'))
          out_file = os.path.join(app.root_path, "%s/%s.html" % (RESULTS_TEMP_DIRECTORY, filename))
          with open(out_file, "w") as file_obj:
            app.logger.debug("Saving results file: %s" % (out_file))
            file_obj.write(template_output)
            file_attach_list.append(out_file)
        except Exception as e:
          current_app.logger.exception(e)
    if email_results and len(file_attach_list):
        try:
          app.logger.debug("Emailing user: %s" % (user.email))
          email_obj = smtpClass(host=EMAIL_HOST,
                                user=EMAIL_USER,
                                password=EMAIL_PWD,
                                port=EMAIL_PORT,
                                use_tls=EMAIL_USE_TLS)
          email_obj.from_addr("%s@%s" % (EMAIL_USER, EMAIL_HOST))
          email_obj.rcpt_to([user.email])
          #email_obj.message(template_output)
          for file_to_attach in file_attach_list:
            email_obj.attach(file_to_attach)
          email_obj.message("See attachment for results.")
          email_obj.subject("Reverb Search Results")
          email_obj.send(content_type="html", charset="UTF-8")

        except Exception as e:
          app.logger.exception(e)
        else:
          #If we succeeded in sending the email, let's update the last_email_date.
          try:
            search_rec.last_email_date = run_time.strftime('%Y-%m-%dT%H:%M:%S')
            db.session.commit()
          except Exception as e:
            db.session.rollback()
            current_app.logger.error("Error attempting to update the last_email_date for search item: %d" % (search_rec.id))
            current_app.logger.exception(e)

    return
