from flask import current_app as app
from flask import render_template
import random
from version import __version__ as version
import os
import json
import datetime
import time

## Use flask's server-side rendering to create a page from templates/index.html
## The @app.route decoration tells flask to return this content for both http://<root> and http://<root>/index
## Looks at the project_status.json and run_status.json files in the root of the qc-etl output
## to build tables for the home page. Assumes they'll be there and in the correct format.
@app.route('/')
@app.route('/index')
def index():
    qc_etl_location = os.getenv("GSI_QC_ETL_ROOT_DIRECTORY")
    three_weeks_ago_ts = (datetime.datetime.today() - datetime.timedelta(days=21)).timestamp() * 1000
    latest_runs = []
    with open(qc_etl_location + '/run_status.json', 'r') as run_status_file:
        run_json = json.load(run_status_file)
        for run in run_json:
            if run["run_completed"] > three_weeks_ago_ts:
                latest_runs.append(run)
    
    return render_template('index.html',
    teststr=three_weeks_ago_ts,
    version=version,
    runs=latest_runs)
