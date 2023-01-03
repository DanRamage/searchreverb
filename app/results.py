class listing:
    def __init__(self, **kwargs):
        self._id = None
        self._listing_description = None
        self._price = None
        self._link = None
        self._condition = None
        self._search_site_id = None
        self._currency = ""

    @property
    def id(self):
        return self._id

    @property
    def listing_description(self):
        return self._listing_description

    @property
    def price(self):
        return self._price

    @property
    def link(self):
        return self._link

    @property
    def condition(self):
        return self._condition

    @property
    def search_site_id(self):
        return self._search_site_id

    @property
    def currency(self):
        return self._currency


class listings:
    def __init__(self):
        self._listings = []

    def parse(self, **kwargs):
        return

    def __iter__(self):
        return iter(self._listings)

    def __len__(self):
        return len(self._listings)
