import dash_core_components as core 
import dash_html_components as html 
from dash.dependencies import Input, Output
from .dash_id import init_ids
from flask_caching import Cache

page_name = 'page-2'

ids = init_ids(['page-content', 'radios'])

layout = html.Div([
    html.H1('Page 2'),
    core.RadioItems(
        id=ids['radios'],
        options=[{'label': i, 'value': i} for i in ['Orange', 'Blue', 'Red']],
        value='Orange'
    ),
    html.Div(id=ids['page-content']),
    html.Br(),
    core.Link('Go to Page 1', href='/dash/page-1'),
    html.Br(),
    core.Link('Go back to home', href='/dash/multipage')
])

def init_callbacks(dash_app):
    return