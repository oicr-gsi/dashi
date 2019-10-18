import dash
import dash_core_components as core
import dash_html_components as html
from .dash_id import init_ids
from dash.dependencies import Input, Output
from flask_caching import Cache
from . import dash_multipage_1, dash_multipage_2, dash_multipage_3

page_name = 'multipage'

ids = init_ids(['url', 
    'page-content'])

layout = html.Div([
    core.Location(id=ids['url'], refresh=False),
    html.Div(id=ids['page-content'])
])

index_page = html.Div([
    core.Link('Go to Page 1', href='/dash/{0}'.format(dash_multipage_1.page_name)),
    html.Br(),
    core.Link('Go to Page 2', href='/dash/{0}'.format(dash_multipage_2.page_name)),
    html.Br(),
    core.Link('Go to Page 3', href='/dash/{0}'.format(dash_multipage_3.page_name)),
    html.Br(),
    html.A('Back to Flask', href='/..')
])


def init_callbacks(dash_app):
    dash_app.config.suppress_callback_exceptions = True

    @dash_app.callback(Output(ids['page-content'], 'children'),
            [Input(ids['url'], 'pathname')])
    @dash_app.server.cache.memoize(timeout=60)
    def display_page(pathname):
        if pathname == '/dash/{0}'.format(dash_multipage_1.page_name):
            return dash_multipage_1.layout
        elif pathname == '/dash/{0}'.format(dash_multipage_2.page_name):
            return dash_multipage_2.layout
        elif pathname == '/dash/{0}'.format(dash_multipage_3.page_name):
            return dash_multipage_3.layout
        else:
            return index_page

    @dash_app.callback(Output(dash_multipage_2.ids['page-content'], 'children'),
            [Input(dash_multipage_2.ids['radios'], 'value')])
    @dash_app.server.cache.memoize(timeout=60)
    def page_2_radios(value):
        return 'You have selected "{0}"'.format(value)
