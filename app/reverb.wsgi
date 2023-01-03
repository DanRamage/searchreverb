# flake8: noqa
import os
import sys

sys.path.insert(0, "/var/www/reverb")

activate_this = os.path.join("/usr/local/virtualenv/python_flask/bin/activate_this.py")
execfile(activate_this, dict(__file__=activate_this))

# from wq_rest_interface import app as application
from main import app as application
