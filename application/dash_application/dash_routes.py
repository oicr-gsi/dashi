from dash import Dash
from dash.dependencies import Input, Output
import dash_html_components as html


# Add Dash to provided Flask server
def add_dash(server):
    dash_app = Dash(__name__, server=server) 

    from . import pages
    for page in pages.pages:
        page.init_callbacks(dash_app)

    from . import dash_multipage_index
    dash_app.layout = dash_multipage_index.layout

    #Return the server object from Dash to overwrite Flask server object
    return dash_app.server