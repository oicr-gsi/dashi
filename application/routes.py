from flask import current_app as app
from flask import render_template
import random
from version import __version__ as version
import os
import json

run_headers = ["last_updated", "page", "run", "run_completed", "completed", "processing"]
## Use flask's server-side rendering to create a page from templates/index.html
## The @app.route decoration tells flask to return this content for both http://<root> and http://<root>/index
## Looks at the project_status.json and run_status.json files in the root of the qc-etl output
## to build tables for the home page. Assumes they'll be there and in the correct format.
@app.route('/')
@app.route('/index')
def index():
    qc_etl_location = os.getenv("GSI_QC_ETL_ROOT_DIRECTORY")
    with open(qc_etl_location + '/run_status.json', 'r') as run_status_file:
        run_json = json.load(run_status_file)

    return render_template('index.html',
    version=version,
    elements=run_headers)
