import os
from flask import Flask
from flask_migrate import Migrate
from flask_security import RoleMixin, UserMixin
from flask_sqlalchemy import SQLAlchemy


DATABASE_FILE = "reverb_search_db.sqlite"
SQLALCHEMY_DATABASE_URI = "sqlite:///" + DATABASE_FILE
SQLALCHEMY_ECHO = False


app = Flask(__name__)

app.config["DATABASE_FILE"] = os.path.join(app.root_path, DATABASE_FILE)
SQLALCHEMY_DATABASE_URI = "sqlite:///" + app.config["DATABASE_FILE"]
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_ECHO"] = SQLALCHEMY_ECHO

"""
# Create in-memory database
app.config["DATABASE_FILE"] = DATABASE_FILE
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_ECHO"] = SQLALCHEMY_ECHO
"""
db = SQLAlchemy(app)

migrate = Migrate(app, db, render_as_batch=True)


class Search_User(db.Model):
    __tablename__ = "search_user"

    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    email = db.Column(db.String(255), unique=True)
    zipcode = db.Column(db.String(10))
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
    item_region = db.Column(db.String())
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
    user = db.relationship("SearchItem", backref="search_results")


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
    search_id = db.Column(db.Integer, db.ForeignKey("user_search_item.id"))
    search_item = db.relationship("SearchItem", backref="normalized_search_results")


class Roles_Users(db.Model):
    __tablename__ = "roles_users"
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"), primary_key=True)
    role_id = db.Column(db.Integer(), db.ForeignKey("role.id"), primary_key=True)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


# Create user model.
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    row_entry_date = db.Column(db.String(32))
    row_update_date = db.Column(db.String(32))
    last_login_date = db.Column(db.String(32))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))

    zipcode = db.Column(db.String(10))
    city = db.Column(db.String(255))
    state = db.Column(db.String(255))

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    active = db.Column(db.Boolean())
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.Text)
    roles = db.relationship(
        Role,
        secondary="roles_users",
        primaryjoin=(Roles_Users.user_id == id),
        backref="user",
    )
    fs_uniquifier = db.Column(db.String(255), unique=True, nullable=False)
