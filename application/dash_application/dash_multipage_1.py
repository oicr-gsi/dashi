import dash_core_components as core 
import dash_html_components as html 
from dash.dependencies import Input, Output
from .dash_id import init_ids
from flask_caching import Cache

page_name = 'page-1'

ids = init_ids(['page-content', 'dropdown'])

layout = html.Div([
    html.H1('Page 1'),
    core.Dropdown(
        id=ids['dropdown'],
        options=[{'label': i, 'value': i} for i in ['LA', 'NYC', 'MTL']],
        value='LA'
    ),
    html.Div(id=ids['page-content']),
    html.Br(),
    core.Link('Go to Page 2', href='/dash/page-2'),
    html.Br(),
    core.Link('Go back to home', href='/dash/multipage'),
])

def init_callbacks(dash_app):
    @dash_app.callback(Output(ids['page-content'], 'children'),
        [Input(ids['dropdown'], 'value')])
    @dash_app.server.cache.memoize(timeout=60)
    def page_1_dropdown(value):
        return 'You have selected "{0}"'.format(value)