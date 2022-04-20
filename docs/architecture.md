# Dashi Architecture
**Dashi** is a QC Reporting system. It pulls data from gsi-qc-etl, filters, and displays it in an interactive series of graphs grouped into reports. The graphs are powered by [Dash](https://dash.plot.ly/), however we use Dash in a relatively non-standard way in order to exact more control over the display. We use Dash as an attachment to a [Flask](https://flask.palletsprojects.com/en/1.1.x/) instance rather than using the Flask instance embedded in Dash, which allows for serving plain HTML pages through Flask for a performance boost.

## Directory Structure

The following is a top to bottom explanation of the files in the Dashi project.

+ /dashi
    + .env : holds environment variables
    + requirements.txt : holds dependencies information, for use with pip on installation
    + config.py : holds python library configuration
    + version.py : holds version information. Used for populating page + footers.
    + wsgi.py : Entry point for WSGI webserver. Loads environment variables, logger, creates & runs Flask application.
    + /application : contains Flask application
        + `__init__.py` : initializes Flask application with caching, metrics, loads routes and attaches Dash application.
        + routes.py: Flask URL handling for plain HTML pages. Allows for passing variables to be injected into HTML
        + /templates : holds HTML pages with special Flask variable syntax
        + /dash_application : contains Dash application
            + /assets/style.css : Dashi stylesheet
            + /plots : legacy graph utilities, not in current use
            + dash_id.py : attaches UUIDs to widget names to get around Dash's requirement that widget IDs be globally unique. Used in every view
            + dash_routes.py : was named to mimic Flask's 'routes.py' but role has since changed. Initializes Dash instance, loads known_page_router's layout skeleton as initial layout, loads pages and their callbacks into memory, returns the Flask instance with Dash attached
            + pages.py : contains developer-maintained list of views by name, imports them programmatically (loading them into memory & triggering their initial data processing), stores imported modules as array
            + known_pages_router.py : builds a dictionary of pages from pages.py plus some information, provides default layout skeleton, callbacks to handle navigation & URL queries
            + /views
                + One file per page in Dashi. Each view contains an array of IDs generated with dash_id, a layout() function to return the page layout, and init_callbacks() which contains all the callbacks for supporting interactivity on the page.
            + /utility
                + df_manipulation.py : common data processing tasks
                + log_utils.py : common logging tasks
                + plot_builder.py : handles our common plotly scatter plot drawing tasks, including cutoff lines, highlighting items, and shaping & colouring items by criteria.
                + sidebar_utils.py : utils for adding widgets to the sidebar, also for parsing URLs and bugfixing callbacks
                + table_builder.py : handles common data table tasks

## Startup Execution
On startup, Dashi prepares to serve pages upon request by loading all page content into memory. Once startup has completed, Dashi is able to respond to events, including responding URL changes, through Dash's callbacks system.

![Startup Execution diagram](./resources/Dashi%20Startup%20Execution.svg)

## URL Handling
Plain HTML pages have their URLs handled by Flask's routes.py, which uses a straight-forward function annotation to map requested URLs to HTML files.

Dash does not have such functionality, and is designed with the expectation that Dash applications will be single-page. We must therefore 'fake' URL handling in Dash using the Location widget in the *dash_core_components* module. This widget watches for URL changes so that callbacks may act on them.

```python
# Default layout element (wraps the page layout elements which are returned by the router)
layout = html.Div([
    core.Location(id='url', refresh=False),
    navbar(default_title),
    dbc.Alert(
        id="user_message",
        is_open=False,
        color="danger",
        style={"margin-left": "15px", "margin-right": "15px"},
    ),
    core.Loading(id='page-content', type='dot'),
    html.Footer(id='footer', children=[
        html.Hr(), 
        "Dashi version {0} | Data version ".format(version), 
        html.Span(id='data-version'),
        html.Br(),
        random.choice(positivity)])
])
```
Source: [known_pages_router.py](../application/dash_application/known_pages_router.py)

Technically, Dashi only displays one page layout, which is the layout skeleton held in [known_pages_router.py](../application/dash_application/known_pages_router.py). The navigation-related callbacks in that module update the skeleton to include information and page content from the other views, based on changes detected in the URL by the Location widget (id 'url'). The widget we update to display page content is the Loading widget with the id 'page-content'. To display content, we output page content to 'page-content's 'children' attribute.

```python
@dash_app.callback(
    Output('navbar', 'brand'),
    [Input('url', 'pathname')]
)
def nav_handler(path):
```
Source: [known_pages_router.py](../application/dash_application/known_pages_router.py)

*nav_handler()* watches for changes to the 'pathname' attribute of the widget with id 'url' (the Location widget). The value that nav_handler() returns is used to replace the current value for the 'brand' attribute of the navbar.

```python
@dash_app.callback(
    [
        Output('page-content', 'children'),
        Output('data-version', 'children'),
    ],
    [
        Input('url', 'pathname'),
        Input('url', 'search')
    ])
def content_handler(path, qs):
    """Get the requested page content and fill in the ETL
    data version info at the bottom of the page"""
    if path == '/None' or path is None:
        return '404', None
    requested = path[1:] # drop the leading slash
    if requested in pages_info.keys():
        page = pages_info[requested]
        return [page.layout(qs), page.dataversion()]
    return '404', None
```
Source: [known_pages_router.py](../application/dash_application/known_pages_router.py)

Dash uses parallel event handling for its callbacks. *content_handler()* also watches for changes to the 'pathname' attribute (as well as the 'search' attribute) of the Location widget, so both callbacks are fired at the same time. This function calls the requested page's *layout()* function to get the content (passing in the search query so the display can be affected by it) and returns it so Dash will output it to 'page-content's 'children' attribute; this displays the page content on screen.

```python
def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # initial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]

    df = reshape_single_lane_df(bamqc, initial["runs"], initial["instruments"], initial["projects"], initial["references"], initial["kits"], initial["library_designs"], initial["start_date"], initial["end_date"], initial["first_sort"], initial["second_sort"], initial["colour_by"], initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className='body', children=[
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

For example, the *layout()* function in [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py) passes the received query from 'search' to *parse_query()* (shown below) then uses the values from the query to change what the page will display before returning the page layout.

```python
def parse_query(query) -> Dict[str, Any]:
    query_dict = parse_query_string(query[1:])  # slice off the leading question mark
    queries = {
        "req_start": None,
        "req_end": None,
        "req_runs": [],
        "req_projects": []
    }
    if "last" in query_dict:
        queries["req_start"], queries["req_end"] = get_requested_run_date_range(query_dict["last"][0])
    if "run" in query_dict:
        queries["req_runs"] = query_dict["run"]
    if "project" in query_dict:
        queries["req_projects"] = query_dict["project"]
    return queries
```
Source: [sidebar_utils.py](../application/dash_application/utility/sidebar_utils.py)

