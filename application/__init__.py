from flask import Flask
from flask_caching import Cache
from prometheus_flask_exporter import PrometheusMetrics
import pandas
import sys
import numpy


## Set up Flask application, attach extensions, and load configuration
def create_app(debug=False):
    # pandas debug options
    pandas.set_option('display.max_rows', None)
    pandas.set_option('display.max_columns', None)
    numpy.set_printoptions(threshold=sys.maxsize)

    # Construct new Flask core
    app = Flask(__name__,
            instance_relative_config=False)

    # Enable cache
    app.cache = Cache(app, config={'CACHE_TYPE': 'simple'})

    # Enable metrics
    app.metrics = PrometheusMetrics(app)

    # Use Configuration object
    app.config.from_object('config.Config')

    with app.app_context():
        # Import Flask routes
        from . import routes

        #Import Dash application
        from .dash_application import dash_routes
        app = dash_routes.add_dash(app, debug)

        return app
