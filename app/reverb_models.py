from app import db


class Search_User(db.Model):
    __tablename__ = "search_user"

    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    email = db.Column(db.String(255), unique=True)
    zipcode = db.Column(db.String(10), unique=True)
    city = db.Column(db.String(255))
    state = db.Column(db.String(255))


class SearchItem(db.Model):
    __tablename__ = "user_search_item"
    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))
    last_email_date = db.Column(db.String(32))
    search_item = db.Column(db.Text)
    max_price = db.Column(db.Float)
    min_price = db.Column(db.Float)
    item_region = db.Column(db.String(3))
    item_state = db.Column(db.String())
    category = db.Column(db.String())
    show_new_results_only = db.Column(db.Boolean)
    filter_radius = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref="user_search_item")

    def __str__(self):
        return self.search_item


class SearchResults(db.Model):
    __tablename__ = "search_results"
    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))

    search_item_id = db.Column(db.Integer)
    last_price = db.Column(db.Float)

    search_id = db.Column(db.Integer, db.ForeignKey("user_search_item.id"))
    search_item = db.relationship("SearchItem", backref="search_results")


class SearchSite(db.Model):
    __tablename__ = "search_site"
    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))

    site_name = db.Column(db.String(64))


class NormalizedSearchResults(db.Model):
    __tablename__ = "normalized_search_results"
    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))

    search_item_id = db.Column(db.Integer)
    last_price = db.Column(db.Float)

    search_site_id = db.Column(db.Integer, db.ForeignKey("search_site.id"))
    search_site = db.relationship("SearchSite", backref="normalized_search_results")
    search_id = db.Column(db.Integer, db.ForeignKey("user_search_item.id"))
    search_item = db.relationship("SearchItem", backref="normalized_search_results")
