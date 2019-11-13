import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids
from . import pages


"""
This file acts as a router which serves all the pages the Dash app knows about.
"""
page_name = None

ids = init_ids(['url', 'page-content'])

# Default layout element (wraps the page layout elements which are returned by the router)
layout = html.Div([
    core.Location(id=ids['url'], refresh=False),
    html.Div(id=ids['page-content'])
])


def init_callbacks(dash_app):
    dash_app.config.suppress_callback_exceptions = True

    @dash_app.callback(
        Output(ids['page-content'], 'children'),
        [Input(ids['url'], 'pathname')])
    def url_handler(path):
        if path == '/None':
            return '404'
        for page in pages.pages:
            if path == '/{0}'.format(page.page_name):
                return page.layout
        return '404'
