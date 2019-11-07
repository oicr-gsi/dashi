import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids

##############################################
### Add file name to the list in pages.py  ###
### once you're done!					   ###
##############################################

## Please refer to the Dash documentation for information
## on Layouts and Callbacks

## Please add all layout element IDs to this array of String
## Then, use ids['name_of_element'] instead 'name_of_element' in the id 
## field of your layout elements
ids = init_ids([])

## Dash layout object
layout = html.Div(children='Placeholder') 

## Please define all callbacks inside this procedure
def init_callbacks(dash_app):
    @app.callback(
        Output(),
        [Input()])
    def placeholder_callback(value):
        return
