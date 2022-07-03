FLASK_DEBUG = False
PYCHARM_DEBUG=False
BUILD_DB=False

# Create dummy secrey key so we can use sessions
SECRET_KEY = ''
SECRET_KEY_FILE = 'secret_key'

# Create in-memory database
DATABASE_FILE = ''

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + DATABASE_FILE
SQLALCHEMY_ECHO = False

if PYCHARM_DEBUG:
  LOGFILE=''
else:
  LOGFILE=''


if PYCHARM_DEBUG:
  CRON_LOGCONF=''
else:
  CRON_LOGCONF=''


OAUTH_TOKEN=''

EMAIL_TEMPLATE='output_templates/email_report.mako'
EMAIL_HOST=''
EMAIL_USER=''
EMAIL_PWD=''
EMAIL_PORT=465
EMAIL_USE_TLS=True

RESULTS_TEMP_DIRECTORY="results_temp/"
#This is in seconds.
RESULTS_TEMP_AGE_OUT = 14400


