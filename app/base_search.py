class base_search:
    def __init__(self, plugin_path, logger=None):
        self._logger = logger
        self._plugin_name = "BaseSearch"
        self._plugin_path = plugin_path
        self._listings = []

    @property
    def __name__(self):
        return self._plugin_name

    def initialize(self, **kwargs):
        return

    def search(self, user, search_rec, site_id):
        return

    def get_listings(self):
        return self._listings
