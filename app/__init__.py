import os
from flask import Flask, send_from_directory, current_app, url_for
from flask_sqlalchemy import SQLAlchemy
import flask_admin as flask_admin
from flask_admin import helpers as admin_helpers
import flask_login as flask_login
from werkzeug.security import generate_password_hash,check_password_hash
from flask_security import Security, SQLAlchemyUserDatastore
from config import *
import logging.config
from logging.handlers import RotatingFileHandler
from logging import Formatter

#app = Flask(__name__)

db = SQLAlchemy()
def create_app(config_file):
  from .admin_models import User,Role

  app = Flask(__name__)

  #db = SQLAlchemy()

  install_secret_key(app)

  #from app import db
  db.app = app
  db.init_app(app)
  user_datastore = SQLAlchemyUserDatastore(db, User, Role)
  security = Security(app, user_datastore)
  login_manager = flask_login.LoginManager()

  # Create in-memory database
  app.config['DATABASE_FILE'] = DATABASE_FILE
  app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
  app.config['SQLALCHEMY_ECHO'] = SQLALCHEMY_ECHO

  init_logging(app)
  admin = build_flask_admin(app, login_manager)
  build_url_rules(app)

  # Create user loader function
  @login_manager.user_loader
  def load_user(user_id):
    return db.session.query(User).get(user_id)

  # define a context processor for merging flask-admin's template context into the
  # flask-security views.
  @security.context_processor
  def security_context_processor():
    return dict(
      admin_base_template=admin.base_template,
      admin_view=admin.index_view,
      h=admin_helpers,
      get_url=url_for
    )

  return app

def build_flask_admin(app, login_manager):

  from .view import MyAdminIndexView, \
    UserModelView, \
    SearchItemView,\
    ItemSearchPageView, \
    AdminUserModelView, \
    BasicUserModelView,\
    RolesView

  from .admin_models import User, Role
  from .reverb_models import SearchItem

  login_manager.init_app(app)
  # Create admin
  admin = flask_admin.Admin(app,
                            'Reverb API Search Price',
                            index_view=MyAdminIndexView(url='/reverb'),
                            base_template='my_master.html',
                            template_mode='bootstrap4',
                            )
  #admin = flask_admin.Admin(app, 'Reverb API Search Price', template_mode='bootstrap3')

  # Add view
  #admin.add_view(AdminUserModelView(User, db.session, endpoint="admin_user_view"))
  #admin.add_view(BasicUserModelView(User, db.session, endpoint="basic_user_view"))
  #admin.add_view(RolesView(Role, db.session))

  admin.add_view(UserModelView(User, db.session))
  admin.add_view(SearchItemView(SearchItem, db.session,name='Current Search Items'))
  admin.add_view(ItemSearchPageView(name='Add Reverb Search Item', endpoint='reverbitemsearch'))
  return admin

def build_url_rules(app):
  from .view import ItemSearchPage, AddSearchItem, reverb_search, reverb_categories_rest

  #Page rules
  app.add_url_rule('/searchpage', view_func=ItemSearchPage.as_view('searchpage'))
  app.add_url_rule('/submit', view_func=AddSearchItem.as_view('submit'), methods=['POST'])
  app.add_url_rule('/search', view_func=reverb_search.as_view('search'), methods=['GET'])
  app.add_url_rule('/reverb_categories', view_func=reverb_categories_rest.as_view('reverb_categories'), methods=['GET'])



  @app.errorhandler(500)
  def internal_error(exception):
      current_app.logger.exception(exception)
      #return render_template('500.html'), 500


  return

def init_logging(app):
  app.logger.setLevel(logging.DEBUG)
  file_handler = RotatingFileHandler(filename = LOGFILE)
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(Formatter('%(asctime)s,%(levelname)s,%(module)s,%(funcName)s,%(lineno)d,%(message)s'))
  app.logger.addHandler(file_handler)

  app.logger.debug("Logging initialized")

  return

def install_secret_key(app):
  """Configure the SECRET_KEY from a file
  in the instance directory.

  If the file does not exist, print instructions
  to create it from a shell with a random key,
  then exit.

  """
  if not FLASK_DEBUG:
    app.config['SECRET_KEY'] = os.urandom(24)
  else:
    app.config['SECRET_KEY'] = SECRET_KEY

'''
login_manager = flask_login.LoginManager()

app = Flask(__name__)

db = SQLAlchemy()

install_secret_key(app)

db.app = app
db.init_app(app)
from .admin_models import User, Role
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Create in-memory database
app.config['DATABASE_FILE'] = DATABASE_FILE
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_ECHO'] = SQLALCHEMY_ECHO

init_logging(app)
admin = build_flask_admin(app)
build_url_rules(app)
'''
#app = create_app(None)
