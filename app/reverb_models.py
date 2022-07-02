from app import db
from flask_security import RoleMixin,UserMixin

class Search_User(db.Model):
  __tablename__ = 'search_user'

  id = db.Column(db.Integer, primary_key=True)
  row_entry_date = db.Column(db.String(32))
  email = db.Column(db.String(255), unique=True)


class SearchItem(db.Model):
  __tablename__ = 'user_search_item'
  id = db.Column(db.Integer, primary_key=True)
  row_entry_date = db.Column(db.String(32))
  row_update_date = db.Column(db.String(32))
  last_email_date = db.Column(db.String(32))
  search_item = db.Column(db.Text)
  max_price = db.Column(db.Float)
  min_price = db.Column(db.Float)
  category = db.Column(db.String())
  show_new_results_only = db.Column(db.Boolean)

  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  user = db.relationship('User', backref='user_search_item')


  def __str__(self):
    return self.search_item



class SearchResults(db.Model):
  __tablename__ = 'search_results'
  id = db.Column(db.Integer, primary_key=True)
  row_entry_date = db.Column(db.String(32))
  row_update_date = db.Column(db.String(32))

  search_item_id = db.Column(db.Integer)

  search_id = db.Column(db.Integer, db.ForeignKey('user_search_item.id'))
  search_item = db.relationship('SearchItem', backref='search_results')
