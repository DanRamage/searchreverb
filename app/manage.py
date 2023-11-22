"""
To use the command line interface you have to:
Load the python venv(source /path/to/python/venv/bin/activate
export FLASK_APP=<fullpathto>/manage.py
"""
import logging.config
import os
import sys
import time
from datetime import datetime
from logging import Formatter
from logging.handlers import RotatingFileHandler

import click
from flask import Flask, current_app

# from mako import exceptions as makoExceptions
# from mako.template import Template
# from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import db
from config import *

# from smtp_utils import smtpClass

from .admin_models import Role, Roles_Users, User

# from .gc_api import guitarcenter_api
# from .reverb_api import reverb_api
from .reverb_models import (
    # NormalizedSearchResults,
    # SearchItem,
    # SearchResults,
    SearchSite,
)
from .searches import searches

sys.path.append("../commonfiles/python")

app = Flask(__name__)
db.app = app

# Create in-memory database
app.config["DATABASE_FILE"] = os.path.join(app.root_path, DATABASE_FILE)
SQLALCHEMY_DATABASE_URI = "sqlite:///" + app.config["DATABASE_FILE"]
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_ECHO"] = SQLALCHEMY_ECHO

db.init_app(app)


def init_logging(app):
    app.logger.setLevel(logging.DEBUG)
    file_handler = RotatingFileHandler(filename=LOGFILE)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        Formatter(
            "%(asctime)s,%(levelname)s,%(module)s,%(funcName)s,%(lineno)d,%(message)s"
        )
    )
    app.logger.addHandler(file_handler)

    app.logger.debug("Logging initialized")

    return


@app.cli.command("database_maintenance")
@click.option("--params", nargs=0)
def database_maintenance(params):
    start_time = time.time()
    init_logging(app)
    current_app.logger.debug("database_maintenance started.")
    try:
        db.session.execute("VACUUM;")
        db.session.close()
    except Exception as e:
        current_app.logger.exception(e)
    # Now let's cleanup the temp directory.
    results_tmp_dir = os.path.join(app.root_path, RESULTS_TEMP_DIRECTORY)

    current_app.logger.debug(
        "Cleaning up files older than: %d seconds" % (RESULTS_TEMP_AGE_OUT)
    )
    for tmp_file in os.listdir(results_tmp_dir):
        try:
            tmp_file_path = os.path.join(results_tmp_dir, tmp_file)
            if os.stat(tmp_file_path).st_mtime < start_time - RESULTS_TEMP_AGE_OUT:
                if os.path.isfile(tmp_file_path):
                    current_app.logger.debug(
                        "File: %s is older than cutoff, deleting." % (tmp_file_path)
                    )
                    os.remove(tmp_file_path)
        except Exception as e:
            current_app.logger.error(
                "Error when testing file: %s for deletion." % (tmp_file_path)
            )
            current_app.logger.exception(e)
    current_app.logger.debug(
        "database_maintenance completed in %f seconds." % (time.time() - start_time)
    )
    return


@app.cli.command("create_roles")
@click.option("--params", nargs=2)
def create_roles(params):
    start_time = time.time()
    init_logging(app)
    roles = params[0].split(",")
    role_descriptions = params[1].split(",")
    row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ndx, role in enumerate(roles):
        try:
            current_app.logger.debug(
                f"Adding role: {role} desc: {role_descriptions[ndx]}"
            )
            new_role = Role(
                row_entry_date=row_entry_date,
                name=role,
                description=role_descriptions[ndx],
            )
            db.session.add(new_role)
            db.session.commit()
        except Exception as e:
            current_app.logger.exception(e)

    db.session.close()
    current_app.logger.debug(
        f"create_roles finised in {time.time() - start_time} seconds."
    )
    return


@app.cli.command("add_user")
@click.option("--params", nargs=4)
def add_user(params):
    start_time = time.time()
    init_logging(app)
    login = params[0]
    email_addr = params[1]
    password = params[2]
    roles_to_add = params[3].split(",")
    current_app.logger.debug("add_user started")
    try:
        test_user = User(
            login=login, email=email_addr, password=generate_password_hash(password)
        )
        db.session.add(test_user)
        db.session.commit()
        # Create role map
        roles = db.session.query(Role).all()
        for role in roles:
            if role.name in roles_to_add:
                role_map = Roles_Users(user_id=test_user.id, role_id=role.id)
                db.session.add(role_map)
        db.session.commit()

    except Exception as e:
        current_app.logger.exception(e)

    current_app.logger.debug(
        "add_user finished in %f seconds" % (time.time() - start_time)
    )


@app.cli.command("add_search_sites")
@click.option("--params", nargs=1)
def add_search_sites(params):
    start_time = time.time()
    init_logging(app)
    search_sites = params.split(",")
    current_app.logger.debug("add_search_sites started")
    try:
        row_entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for site in search_sites:
            search_site = SearchSite(row_entry_date=row_entry_date, site_name=site)
            db.session.add(search_site)
            db.session.commit()

    except Exception as e:
        current_app.logger.exception(e)

    current_app.logger.debug(
        "add_search_sites finished in %f seconds" % (time.time() - start_time)
    )


@app.cli.command("update_fs_uniquifiers")
@click.option("--params", nargs=1)
def update_fs_uniquifiers(params):
    # update existing rows with unique fs_uniquifier
    import uuid

    users = db.session.query(User).filter(User.fs_uniquifier is None).all()
    for user in users:
        user.fs_uniquifier = uuid.uuid4().hex
    db.session.commit()
    # for row in conn.execute(sa.select([user_table.c.id])):
    #    conn.execute(user_table.update().values(fs_uniquifier=uuid.uuid4().hex).where(user_table.c.id == row['id']))

    # finally - set nullable to false
    # op.alter_column('user', 'fs_uniquifier', nullable=False)

    # for MySQL the previous line has to be replaced with...
    # op.alter_column('user', 'fs_uniquifier', existing_type=sa.String(length=64),
    # nullable=False)    current_app.logger.debug(
    return


@app.cli.command("run_searches")
@click.option("--params", nargs=1)
def run_searches(params):
    start_time = time.time()
    try:
        email_results = int(params)
        init_logging(app)

        search_obj = searches()
        search_obj.do_searches(email_results)
    except Exception as e:
        current_app.logger.exception(e)
    current_app.logger.debug(
        f"run_searches completed in {time.time() - start_time} seconds."
    )
    return
