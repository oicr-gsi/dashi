from flask import current_app as app
from flask import render_template, abort
from version import __version__ as version
import os
import json
import datetime
from application.dash_application.pages import pages
import gsiqcetl.api

# Dashi doesn't support displaying status data from multiple pages
# Only the first source is being displayed
qc_etl_location = os.getenv("GSI_QC_ETL_ROOT_DIRECTORY")
qc_etl_location = qc_etl_location.split(":")[0]

# {pagename: Full Text Page Title}
page_info = {}
for module in pages:
    page_info[module.page_name] = module.title

## Use flask's server-side rendering to create a page from templates/index.html
## The @app.route decoration tells flask to return this content for both http://<root> and http://<root>/index
## Looks at the project_status.json and run_status.json files in the root of the qc-etl output
## to build tables for the home page. Assumes they'll be there and in the correct format.
## Python uses timestamps in seconds. The project/run files have timestamps in milliseconds
## hence the multiplying and dividing by 1000
@app.route('/')
@app.route('/index')
def index():
    three_weeks_ago_ts = (datetime.datetime.today() - datetime.timedelta(days=21)).timestamp()

    latest_runs = []
    with open(qc_etl_location + '/grouped_run_status.json', 'r') as run_status_file:
        run_json = json.load(run_status_file)
        for run in run_json:
            if run["run_completed"] > three_weeks_ago_ts*1000: 
                # Convert timestamps to string for display
                run["run_completed"] = str_timestamp(run["run_completed"]/1000)

                latest_runs.append(run)
    latest_runs = sorted(latest_runs, key=lambda k: k["run_completed"], reverse=True)

    with open(qc_etl_location + '/grouped_project_status.json', 'r') as project_status_file:
        project_json = json.load(project_status_file)
    project_json = sorted(project_json, key=lambda k: k["project"])

    return render_template('index.html',
    version=version,
    runs=latest_runs,
    projects=project_json,
    page_info=page_info)


@app.route('/runs')
def run_list():
    all_runs = []
    with open(qc_etl_location + '/grouped_run_status.json', 'r') as run_status_file:
        run_json = json.load(run_status_file)
        for run in run_json:
            # Convert timestamps to string for display
            run["run_completed"] = str_timestamp(run["run_completed"]/1000)

            all_runs.append(run)
    all_runs = sorted(all_runs, key=lambda k: k["run_completed"], reverse=True)

    return render_template('runs.html',
    version=version,
    runs=all_runs,
    page_info=page_info)


@app.route('/status')
def status_page():
    qcetlapi = gsiqcetl.api.QCETLCache(qc_etl_location)
    errors = {c.name: "Missing error file" for c in gsiqcetl.api.formats}
    lastinputdate = {c.name: "Cache not enabled" for c in gsiqcetl.api.formats}
    shesmu_input = {c.name: "" for c in gsiqcetl.api.formats}

    for cache in gsiqcetl.api.formats:
        error_path = qcetlapi.path_failed_input(cache)
        if os.path.exists(error_path):
            with open(error_path, "r") as f:
                j = json.load(f)
                if len(j) > 0:
                    errors[cache.name] = json.dumps(j, indent=2)
                else:
                    errors[cache.name] = "Ok"
        cache_path = qcetlapi.path_latest_input(cache)
        if os.path.exists(cache_path):
            lastinputdate[cache.name] = datetime.datetime.fromtimestamp(
                os.stat(cache_path).st_mtime)
            shesmu_input[cache.name] = "Link"

    return render_template(
        'status.html',
        version=version,
        page_info=page_info,
        shesmu_input=shesmu_input,
        errors=errors,
        lastinputdate=lastinputdate,
    )

@app.route('/shesmu_input/<cache_name>')
def shesmu_input(cache_name):
    qcetlapi = gsiqcetl.api.QCETLCache(qc_etl_location)

    for cache in gsiqcetl.api.formats:
        if cache.name == cache_name:
            shesmu_path = qcetlapi.path_latest_input(cache)
            if not os.path.exists(shesmu_path):
                abort(404)
            with open(shesmu_path, "r") as f:
                shesmu_data = f.read()
            response = app.response_class(
                response=shesmu_data,
                status=200,
                mimetype='application/json'
            )
            return response

    abort(404)

def str_timestamp(ts):
    # To decode: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    DATE_FORMAT = "%Y-%m-%d"

    return datetime.datetime.fromtimestamp(ts).strftime(DATE_FORMAT)



