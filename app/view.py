from flask import request, redirect, render_template, current_app, url_for, flash, has_app_context
from flask.views import View, MethodView
import flask_admin as admin
import flask_login as login
from flask_admin.contrib import sqla
from flask_admin import helpers, expose, BaseView
from flask_security import current_user
from sqlalchemy.exc import IntegrityError
import json
import time
from datetime import datetime
from wtforms import form, fields, validators, SubmitField
from werkzeug.security import generate_password_hash, check_password_hash
import requests
#from admin_models import User
from sqlalchemy import exc
from sqlalchemy.orm.exc import *
from sqlalchemy import func

from app import db
from .admin_models import User, Role, Roles_Users
from .reverb_models import SearchItem, SearchResults
from .reverb_api import reverb_api
from config import OAUTH_TOKEN

class BaseAPI(MethodView):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    return
  def parse_request_args(self):
    return
  def json_error_response(self, error_code, error_message):
    json_error = {}
    json_error['error'] = {
      'code': error_code,
      'message': error_message
    }
    return json_error

class ItemSearchPageView(BaseView):
    def is_accessible(self):
        return login.current_user.is_authenticated

    @expose('/')
    def index(self):
        start_time = time.time()
        # Have to be logged in to access the page.

        if not login.current_user.is_authenticated:
            current_app.logger.error("IP: %s not logged in attempting to access page" % (request.remote_addr))
            return current_app.login_manager.unauthorized()

        current_app.logger.debug('dispatch_request started')
        try:
            reverb_req = reverb_api(oauth_token=OAUTH_TOKEN, logger=current_app.logger)
            json_results = reverb_req.categories()
            rendered_template = self.render('search_page.html', categories=json_results['categories'])

        except Exception as e:
            current_app.logger.exception(e)
        current_app.logger.debug('dispatch_request finished in %f seconds' % (time.time() - start_time))
        return rendered_template


class ItemSearchPage(View):
  def __init__(self):
    current_app.logger.debug('ItemSearchPage __init__')

  def dispatch_request(self):
    start_time = time.time()
    #Have to be logged in to access the page.
    if not current_user.is_authenticated:
        current_app.logger.error("IP: %s not logged in attempting to access page" % (request.remote_addr))
        return current_app.login_manager.unauthorized()

    current_app.logger.debug('dispatch_request started')
    try:
        req = requests.get("/reverb_categories")
        if req.status_code == 200:
            req
        rendered_template = render_template('search_page.html')

    except Exception as e:
      current_app.logger.exception(e)
    current_app.logger.debug('dispatch_request finished in %f seconds' % (time.time()-start_time))
    return rendered_template

class AddSearchItem(MethodView):
  def get(self):
      if user_id is None:
          # return a list of users
          pass
      else:
          # expose a single user
          pass


  def delete(self, user_id):
      pass

  def put(self, user_id):
      pass

  def post(self):
    if not current_user.is_authenticated:
        current_app.logger.error("IP: %s not logged in attempting to access page" % (request.remote_addr))
        return current_app.login_manager.unauthorized()

    #email = request.form['email']
    search_item = request.form['search_item']
    try:
        max_price = request.form['max_price']
    except ValueError as e:
        max_price = None
    try:
        min_price = float(request.form['min_price'])
    except ValueError as e:
        min_price = None
    #category = request.form['category']
    full_category = request.form['full_category']
    new_results_only = False
    if 'new_results_only' in request.form:
        new_results_only = int(request.form['new_results_only'])
    item_region = None
    if 'item_region' in request.form:
        item_region = request.form['item_region']
    row_entry_date = datetime.now()
    current_app.logger.debug('IP: %s AddSearchItem: Email: %s Search Item: %s Country Code: %s Max Price: %s Min Price: %s Category: %s'\
                             % (request.remote_addr, current_user.email, search_item, item_region, max_price, min_price, full_category))
    search_item = SearchItem(
        row_entry_date=row_entry_date.strftime("%Y-%m-%d %H:%M:%S"),
        search_item=search_item,
        item_region=item_region,
        category=full_category,
        max_price=max_price,
        min_price=min_price,
        user_id=current_user.id,
        show_new_results_only=new_results_only
    )
    try:
        db.session.add(search_item)
        db.session.commit()
        ret_code = 200
        ret_val = {
            'status': 200,
            'message': 'Search added successfully.'}
    except IntegrityError as e:
        current_app.logger.exception(e)
        ret_code = 500
        ret_val = {
            'status': 500,
            'message': 'Search already exists'}
    except Exception as e:
        current_app.logger.exception(e)
        ret_code = 500
        ret_val = {
            'status': 500,
            'message': 'Error adding search.'}
    rev_val = json.dumps(ret_val)
    return (rev_val, ret_code, {'Content-Type': 'Application-JSON'})




# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.DataRequired()])
    password = fields.PasswordField(validators=[validators.DataRequired()])
    #submit = SubmitField('Sign In')
    def validate_login(self, field):
      user = self.get_user()

      if user is None:
          raise validators.ValidationError('Invalid user')

      # we're comparing the plaintext pw with the the hash from the db
      if not check_password_hash(user.password, self.password.data):
      # to compare plain text passwords use
      # if user.password != self.password.data:
          raise validators.ValidationError('Invalid password')

    def get_user(self):
      return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.StringField(validators=[validators.DataRequired()])
    email = fields.StringField(validators=[validators.DataRequired()])
    first_name = fields.StringField()
    last_name = fields.StringField()
    password = fields.PasswordField(validators=[validators.DataRequired()])

    def validate_login(self, field):
      if db.session.query(User).filter_by(login=self.login.data).count() > 0:
        raise validators.ValidationError('Duplicate username')

class base_view(sqla.ModelView):
  """
  This view is used to update some common columns across all the tables used.
  Now it's mostly the row_entry_date and row_update_date.
  """
  def on_model_change(self, form, model, is_created):
    start_time = time.time()
    current_app.logger.debug("IP: %s User: %s on_model_change started" % (request.remote_addr, current_user.login))

    entry_time = datetime.utcnow()
    if is_created:
      model.row_entry_date = entry_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
      model.row_update_date = entry_time.strftime("%Y-%m-%d %H:%M:%S")

    sqla.ModelView.on_model_change(self, form, model, is_created)

    current_app.logger.debug("IP: %s User: %s on_model_change finished in %f seconds" % (request.remote_addr, current_user.login, time.time() - start_time))

  def is_accessible(self):
    """
    This checks to make sure the user is active and authenticated and is a superuser. Otherwise
    the view is not accessible.
    :return:
    """
    if not current_user.is_active or not current_user.is_authenticated:
      return False

    if current_user.has_role('admin'):
      return True

    return False

class AdminUserModelView(base_view):
  """
  This view handles the administrative user editing/creation of users.
  """
  form_extra_fields = {
    'password': fields.PasswordField('Password')
  }
  column_list = ('login', 'first_name', 'last_name', 'email', 'active', 'roles', 'row_entry_date', 'row_update_date')
  form_columns = ('login', 'first_name', 'last_name', 'email', 'password', 'active', 'roles')

  def on_model_change(self, form, model, is_created):
    """
    If we're creating a new user, hash the password entered, if we're updating, check if password
    has changed and then hash that.
    :param form:
    :param model:
    :param is_created:
    :return:
    """
    start_time = time.time()
    current_app.logger.debug(
      'IP: %s User: %s AdminUserModelView on_model_change started.' % (request.remote_addr, current_user.login))
    # Hash the password text if we're creating a new user.
    if is_created:
      model.password = generate_password_hash(form.password.data)
    # If this is an update, check to see if password has changed and if so hash the form password.
    else:
      hashed_pwd = generate_password_hash(form.password.data)
      if hashed_pwd != model.password:
        model.password = hashed_pwd

    current_app.logger.debug('IP: %s User: %s AdminUserModelView create_model finished in %f seconds.' % (
    request.remote_addr, current_user.login, time.time() - start_time))

class BasicUserModelView(AdminUserModelView):
  """
  Basic user view. A simple user only gets access to their data record to edit. No creating or deleting.
  """
  column_list = ('login', 'first_name', 'last_name', 'email')
  form_columns = ('login', 'first_name', 'last_name', 'email', 'password')
  can_create = False  # Don't allow a basic user ability to add a new user.
  can_delete = False  # Don't allow user to delete records.

  def get_query(self):
    # Only return the record that matches the logged in user.
    return super(AdminUserModelView, self).get_query().filter(User.login == login.current_user.login)

  def is_accessible(self):
    if current_user.is_active and current_user.is_authenticated and not current_user.has_role('admin'):
      return True
    return False

class RolesView(base_view):


  def is_accessible(self):
      if current_user.is_active and current_user.is_authenticated and current_user.has_role('admin'):
          return True
      return False

  """
  View into the user Roles table.
  """
  column_list = ['name', 'description']
  form_columns = ['name', 'description']


# Create customized model view class
class UserModelView(sqla.ModelView):
    #can_create = False
    #can_delete = False


    @property
    def _list_columns(self):
        return self.get_list_columns()

    @_list_columns.setter
    def _list_columns(self, value):
        pass

    @property
    def column_list(self):
        if current_user is not None:
            if not has_app_context() or current_user.has_role('admin'):
                return ['id', 'row_entry_date', 'row_update_date', 'last_login_date',
                        'login', 'email', 'roles', 'first_name', 'last_name', 'active']
            else:
                return ['last_login_date', 'login', 'email', 'first_name', 'last_name' ]

    @property
    def _form_columns(self):
        return self.get_form_columns()

    @_form_columns.setter
    def _form_columns(self, value):
        pass

    @property
    def form_columns(self):
        if current_user != None:
            if not has_app_context() or not current_user.has_role('admin'):
                return ['email', 'first_name', 'last_name' ]


    def is_accessible(self):
        if current_user.is_active and current_user.is_authenticated and current_user.has_role('admin'):
          return True
        return False
        '''
        if current_user.is_authenticated:
          return True
        return False
        '''
    def get_query(self):
      if current_user.is_active and current_user.is_authenticated:
          #Admin user cana see all user accounts, otherwise you just get your user info.
          if current_user.has_role('admin'):
            return self.session.query(self.model)
          else:
              return self.session.query(self.model).filter(self.model.login == current_user.login)

    def get_count_query(self):
      cnt = 0
      if current_user.is_active and current_user.is_authenticated:
          #Admin user cana see all user accounts, otherwise you just get your user info.
          if not current_user.has_role('admin'):
            cnt = self.session.query(func.count('*')).filter(self.model.login == current_user.login)
          else:
              cnt = super().get_count_query()
      return cnt



# Create customized index view class that handles login & registration
class MyAdminIndexView(admin.AdminIndexView):

    @expose('/')
    def index(self):
        current_app.logger.debug("IP: %s Admin index page" % (request.remote_addr))
        if not login.current_user.is_authenticated:
          current_app.logger.debug("IP: %s User: %s is not authenticated" % (request.remote_addr, login.current_user))
          return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        current_app.logger.debug("IP: %s Login page" % (request.remote_addr))
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)
        else:
          current_app.logger.debug("IP: %s User: %s is not authenticated" % (request.remote_addr, form.login.data))
        if login.current_user.is_authenticated:
            #Update the login time.
            try:
                login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                login.current_user.last_login_date = login_time
                db.session.commit()
            except Exception as e:
                current_app.logger.exception(e)
            return redirect(url_for('.index'))
        link = '<p>Don\'t have an account? <a href="' + url_for('.register_view') + '">Click here to register.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            try:
                user = User()

                form.populate_obj(user)
                user.row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # we hash the users password to avoid saving it as plaintext in the db,
                # remove to use plain text:
                user.password = generate_password_hash(form.password.data)

                db.session.add(user)
                db.session.commit()
                #Create the role mapping. ALl users coming through the register path are search_user.
                role = db.session.query(Role).filter(Role.name == 'search_user').one()
                role_map = Roles_Users(user_id=user.id,
                                       role_id=role.id)
                db.session.add(role_map)
                db.session.commit()

                login.login_user(user)
                return redirect(url_for('.index'))
            except Exception as e:
                current_app.logger.exception(e)

        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        current_app.logger.debug("IP: %s Logout page" % (request.remote_addr))
        login.logout_user()
        return redirect(url_for('.index'))



class SearchItemView(sqla.ModelView):
  #form_excluded_columns = ('user', 'row_entry_date', 'row_update_date')
  form_columns = ['search_item', 'category', 'item_region', 'max_price', 'min_price', 'show_new_results_only']
  can_create = False

  @property
  def _list_columns(self):
      return self.get_list_columns()
  @_list_columns.setter
  def _list_columns(self, value):
    pass
  @property
  def column_list(self):
      if login.current_user and login.current_user.is_authenticated:
          if not current_user.has_role('admin'):
              column_list = ['row_entry_date', 'last_email_date', 'search_item', 'category', 'item_region', 'max_price', 'min_price',
                             'show_new_results_only']
          else:
              column_list = ['user.login', 'row_entry_date', 'last_email_date', 'search_item', 'category', 'item_region', 'max_price', 'min_price',
                             'show_new_results_only']
          return column_list

  def is_accessible(self):
    return login.current_user.is_authenticated

  def create_model(self, form):
    #sqla.ModelView.create_model(self, form)
    try:
      model = self.model()
      form.populate_obj(model)
      model.user = login.current_user
      entry_time = datetime.utcnow()
      model.row_entry_date = entry_time.strftime("%Y-%m-%d %H:%M:%S")
      self.session.add(model)
      self._on_model_change(form, model, True)
      self.session.commit()
    except Exception as ex:
      current_app.logger.exception(ex)
      self.session.rollback()
      return False
    else:
      self.after_model_change(form, model, True)

    return model

  def delete_model(self, model):
      #Let's clean out the search results table since this search is getting deleted.
      current_app.logger.debug("IP: %s Deleting search: %s(%d)" % (request.remote_addr, model.search_item, model.id))
      search_results_deleted = -1
      try:
          recs = self.session.query(SearchResults)\
              .filter(SearchResults.search_id == model.id)\
              .delete()
          search_results_deleted = recs
          self.session.commit()
      except Exception as e:
          current_app.logger.error("Error when deleting search results for search id: %d" % (model.id))
          current_app.logger.exception(e)
          self.session.rollback()
      try:
        self.on_model_delete(model)
        self.session.flush()
        self.session.delete(model)
        self.session.commit()

      except Exception as e:
          current_app.logger.error("Error when deleting search id: %d" % (model.id))
          current_app.logger.exception(e)
          self.session.rollback()
          return False
      else:
          self.after_model_delete(model)
      current_app.logger.debug("Deleted search: %s(%d) and %d search results" % (model.search_item, model.id, search_results_deleted))
      return True
  """
  def after_model_change(self, form, model, is_created):
    return

  def on_model_change(self, form, model, is_created):
    return
  """
  def get_query(self):
    if not current_user.has_role('admin'):
        return super(SearchItemView, self).get_query().filter(SearchItem.user_id == login.current_user.id)
    else:
        return super(SearchItemView, self).get_query()

  def get_count_query(self):
      cnt = ""
      if current_user.is_active and current_user.is_authenticated:
          #Admin user cana see all user accounts, otherwise you just get your user info.
          if not current_user.has_role('admin'):
              cnt = self.session.query(func.count('*')).filter(SearchItem.user_id == login.current_user.id)
          else:
              cnt = super().get_count_query()
      return cnt

class SearchResultsView(sqla.ModelView):
    column_list = ['row_entry_date', 'row_update_date', 'search_item.search_item', 'search_item_id', 'last_price']
    def is_accessible(self):
      if current_user.is_active and current_user.is_authenticated and current_user.has_role('admin'):
          return True
      return False

class NormalizedSearchResultsView(sqla.ModelView):
    column_list = ['row_entry_date', 'row_update_date', 'search_item.search_item', 'search_item_id', 'search_site.site_name', 'last_price']
    def is_accessible(self):
      if current_user.is_active and current_user.is_authenticated and current_user.has_role('admin'):
          return True
      return False

class reverb_categories_rest(BaseAPI):
    def __init__(self):
        self._base_url = "https://api.reverb.com/api/categories"
        self._headers = {'Authorization': 'Bearer %s' % (OAUTH_TOKEN),
                   'Content-Type': 'application/hal+json',
                   'Accept': 'application/hal+json',
                   'Accept-Version': '3.0'}

    def get(self):
        try:
            req = requests.get(self._base_url, headers=headers)
        except Exception as e:
            current_app.logger.exception(e)
            results = self.json_error_response(req.status_code, req.text)
            ret_code = 404
        return req


class reverb_listings_rest(BaseAPI):
    def __init__(self):
        self._base_url = "https://api.reverb.com/api/listings/all"
        self._headers = {'Authorization': 'Bearer %s' % (OAUTH_TOKEN),
                   'Content-Type': 'application/hal+json',
                   'Accept': 'application/hal+json',
                   'Accept-Version': '3.0'}

    def get(self):
      for key in request.args:
          payload[key] = request.args[key]
      try:
          req = requests.get(self._base_url, headers=headers, params=payload)
      except Exception as e:
          current_app.logger.exception(e)
          results = self.json_error_response(req.status_code, req.text)
          ret_code = 404
      return req

class reverb_search(reverb_listings_rest):
    def get(self):
        current_app.logger.debug("IP: %s reverb_search. Params: %s" % (request.remote_addr, request.args))

        payload = {}
        for key in request.args.keys():
            payload[key] = request.args[key]
        try:
            req = requests.get(self._base_url, headers=self._headers, params=payload)
            results = req.text
            ret_code = req.status_code
        except Exception as e:
            current_app.logger.exception(e)
            results = self.json_error_response(req.status_code, req.text)
            ret_code = 404

        return (results, ret_code, {'Content-Type': 'application/json'})

