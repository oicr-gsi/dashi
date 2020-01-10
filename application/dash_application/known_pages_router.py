from collections import namedtuple
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output

from .dash_id import init_ids
from . import pages
from ..routes import version


"""
This file acts as a router which serves all the pages the Dash app knows about.
"""
page_name = None
default_title = ""

# Build dict of known pages info
pages_info = {}
PageInfo = namedtuple('PageInfo', 'layout title')
for p in pages.pages:
    pages_info[p.page_name] = PageInfo(p.layout, p.title)

def navbar(current):
    def menu_item(label, link):
        return dbc.DropdownMenuItem(label,
                                    href=link,
                                    external_link=True,
                                    disabled=current == label,
                                    style={"fontSize": "12pt"})
    return dbc.NavbarSimple(
        id="navbar",
        children=[
            dbc.DropdownMenu(
                children=[
                    menu_item("Pre-Exome", "preqc-exome"),
                    menu_item("Pre-WGS", "preqc-wgs"),
                    menu_item("Pre-RNA", "preqc-rna")
                ],
                nav=True,
                in_navbar=True,
                style={"fontSize": "12pt"},
                label="Modules",
            ),
        ],
        brand=current,
        brand_style={"fontSize": "14pt"},
        color="light",
        dark=False,
        sticky="top",
    )


# Default layout element (wraps the page layout elements which are returned by the router)
layout = html.Div([
    core.Location(id='url', refresh=False),
    navbar(default_title),
    core.Loading(id='page-content'),
    html.Footer(id='footer', children=[html.Hr(), "Dash version {0}".format(version)])
])


def init_callbacks(dash_app):
    dash_app.config.suppress_callback_exceptions = True

    @dash_app.callback(
        Output('navbar', 'brand'),
        [Input('url', 'pathname')]
    )
    def nav_handler(path):
        if path == '/None':
            return default_title
        requested = path[1:]  # drop the leading slash
        if requested in pages_info.keys():
            page = pages_info[requested]
            return page.title if page.title else default_title
        return default_title

    @dash_app.callback(
        Output('page-content', 'children'),
        [
            Input('url', 'pathname'),
            Input('url', 'search')
        ])
    def content_handler(path, qs):
        if path == '/None':
            return '404'
        requested = path[1:] # drop the leading slash
        if requested in pages_info.keys():
            page = pages_info[requested]
            return page.layout(qs)
        return '404'
