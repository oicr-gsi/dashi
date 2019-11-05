import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids
from . import pages

page_name = None

ids = init_ids(['url', 'page-content'])

layout = html.Div([
    core.Location(id=ids['url'], refresh=False),
    html.Div(id=ids['page-content'])
]) 


def init_callbacks(dash_app):
    dash_app.config.suppress_callback_exceptions = True

    # TODO: You can hang dashi and potentially DoS it by going to <dashi-url>/None
    @dash_app.callback(
        Output(ids['page-content'], 'children'),
        [Input(ids['url'], 'pathname')])
    def url_handler(path):
        for page in pages.pages:
            if path == '/{0}'.format(page.page_name):
                return page.layout
        return '404'
