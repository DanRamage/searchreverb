import requests
import logging.config

import time
from datetime import datetime
from urllib.parse import urlparse, urlencode

class reverb_base:
  def __init__(self, url, oauth_token, logger):
    self._base_url = url
    self._oauth_token = oauth_token
    self._logger = logger
  def get(self, url, **kwargs):
    payload = {}
    for key in kwargs:
      payload[key] = kwargs[key]

    headers = {'Authorization': 'Bearer %s' % (self._oauth_token),
               'Content-Type': 'application/hal+json',
               'Accept': 'application/hal+json',
               'Accept-Version': '3.0'}
    self._logger.debug("URL: %s Request params: %s" % (url, payload))
    try:
      req = requests.get(url, headers=headers, params=payload, timeout=15)
    except Exception as e:
      self._logger.exception(e)
    return req

class reverb_api(reverb_base):
  def __init__(self, oauth_token, logger, results_limit=100, url="https://api.reverb.com/api"):
    super().__init__(url, oauth_token, logger)
    self.item_results = []
    self.run_time = datetime.utcnow()
    #This is the number of results we will limit ourselves to.
    self._results_limit = results_limit


  def search_listings(self, **kwargs):
    start_search = time.time()
    listings = []
    try:
      url = "%s/%s" % (self._base_url, "listings/all")
      results = self.get(url=url, **kwargs)
      if results.status_code == 200:
        stop_at_page = None
        results = results.json()
        total_pages = results['total']
        if total_pages > self._results_limit:
          self._logger.warning("Query has: %d results, our limit is: %d" % (total_pages, self._results_limit))
        else:
          self._logger.warning("Query has: %d results." % (total_pages))

        listings.extend(results['listings'])
        if 'next' in results['_links']:
          current_page = 1
          next_url = results['_links']['next']['href']
          self._logger.debug("Next url: %s" % (next_url))
          # We want to limit our queries, so let's not return anymore than N results.
          url_parts = urlparse(next_url)
          query_parts = dict(param.split('=') for param in url_parts.query.split('&'))
          #Based on the results returned per query and the current page, we will limit our results.
          stop_at_page = int(self._results_limit / int(query_parts['per_page']))

          paginate = True
          while paginate:
              if (stop_at_page and current_page >= stop_at_page) or (current_page == total_pages):
                paginate = False
              current_page += 1
              next_req = self.get(url=next_url)
              if next_req.status_code == 200:
                next_results = next_req.json()
                listings.extend(next_results['listings'])
                if 'next' in next_results['_links']:
                  next_url = next_results['_links']['next']['href']
                else:
                  paginate = False

    except Exception as e:
      self._logger.exception(e)
    self._logger.debug("search finished in %f seconds" % (time.time() - start_search))
    return listings

  def categories(self):
    start_search = time.time()
    json_results = None
    try:
      url = "%s/%s" % (self._base_url, "categories")
      results = self.get(url=url, **{})
      json_results = results.json()
    except Exception as e:
      self._logger.exception(e)
    self._logger.debug("search finished in %f seconds" % (time.time() - start_search))
    return json_results
