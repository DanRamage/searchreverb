import optparse

from app import create_app

# from config import *


app = create_app(None)

if __name__ == "__main__":
    parser = optparse.OptionParser()

    parser.add_option("-u", "--User", dest="user", help="User to add", default=None)
    parser.add_option(
        "-p",
        "--Password",
        dest="password",
        help="Stations file to import.",
        default=None,
    )
    (options, args) = parser.parse_args()

    if options.user is not None:
        if options.password is not None:
            print("Must provide password")
            # build_init_db(options.user, options.password, True)
        else:
            print("Must provide password")
    else:
        # install_secret_key(app, SECRET_KEY_FILE)

        app.run(debug=True)
        app.logger.debug("App started")
