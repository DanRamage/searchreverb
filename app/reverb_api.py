import requests
import logging.config

import time
from datetime import datetime

class reverb_base:
  def __init__(self, url, oauth_token):
    self._base_url = url
    self._oauth_token = oauth_token
    self._logger = logging.getLogger()
  def get(self, url, **kwargs):
    payload = {}
    for key in kwargs:
      payload[key] = kwargs[key]

    headers = {'Authorization': 'Bearer %s' % (self._oauth_token),
               'Content-Type': 'application/hal+json',
               'Accept': 'application/hal+json',
               'Accept-Version': '3.0'}
    self._logger.debug("Request params: %s" % (payload))
    req = requests.get(url, headers=headers, params=payload, timeout=15)
    return req

class reverb_api(reverb_base):
  def __init__(self, oauth_token, url="https://api.reverb.com/api"):
    super().__init__(url, oauth_token)
    self.item_results = []
    self.run_time = datetime.utcnow()


  def search_listings(self, **kwargs):
    start_search = time.time()
    listings = []
    try:
      url = "%s/%s" % (self._base_url, "listings/all")
      results = self.get(url=url, **kwargs)
      if results.status_code == 200:
        results = results.json()
        #json_results.append(results)
        listings.extend(results['listings'])
        if 'next' in results['_links']:
          next_url = results['_links']['next']['href']
          paginate = True
          while paginate:
              next_req = self.get(url=next_url)
              if next_req.status_code == 200:
                next_results = next_req.json()
                #json_results.append(next_results)
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
