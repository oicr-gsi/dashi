import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids
from . import bcl2fastq, bamqc_gbovertime, poolqc

ids = init_ids(['url', 'page-content'])

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
        if path == '/{0}'.format(bcl2fastq.page_name):
            return bcl2fastq.layout
        elif path == '/{0}'.format(bamqc_gbovertime.page_name):
            return bamqc_gbovertime.layout
        elif path == '/{0}'.format(poolqc.page_name):
            return poolqc.layout
        else:
            return '404'
