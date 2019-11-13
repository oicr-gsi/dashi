from dash import Dash
from dash.dependencies import Input, Output
import dash_html_components as html

## Adds Dash to provided Flask server
def add_dash(server):
    ## Create Dash instance using Flask object as server
    dash_app = Dash(__name__, server=server) 

    ## Load callbacks into memory
    from . import pages
    for page in pages.pages:
        page.init_callbacks(dash_app)

    ## Set your initial Dash page's layout to this variable 
    from .views import index_page
    dash_app.layout = index_page.layout

    ## Return the server object from Dash to overwrite Flask server object
    return dash_app.server
