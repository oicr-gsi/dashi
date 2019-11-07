import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids

page_name = 'preexome'

ids = init_ids([])

## Dash layout object
layout = html.Div(className='body',
    children=[
        html.Div(className='sidebar'),
        html.Div(className='graphs'),
        html.Div(className='terminal-output'),
        html.Div(className='data-table'),
    ]) 

## Please define all callbacks inside this procedure
def init_callbacks(dash_app):
    # @dash_app.callback(
    #     Output(),
    #     [Input()])
    # def placeholder_callback(value):
        return
