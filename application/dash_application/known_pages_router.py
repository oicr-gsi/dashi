from collections import namedtuple
import random
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
PageInfo = namedtuple('PageInfo', 'layout title dataversion')
for p in pages.pages:
    pages_info[p.page_name] = PageInfo(p.layout, p.title, p.dataversion)

positivity = [
    "Thank you for looking at the QC data.",
    "Your hard work is appreciated.",
    "You put the quality in quality control.",
    "We're all in this together.",
    ":)",
    '“Quality is never an accident; it is always the result of high intention, sincere effort, intelligent direction and skillful execution; it represents the wise choice of many alternatives.” - William A. Foster',
    '“Quality is not act.  It is a habit.” - Aristotle',
    '“Quality means doing it right when no one is looking.” - Henry Ford',
    '“Quality begins on the inside; then works its way out.” - Bob Moawad',
    '“Success is the sum of small efforts, repeated day-in and day-out.” - Robert Collier',
]

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
            # Simple Navbar only lets you add content to the right side. This CSS forces the button out of the div 
            html.A(html.Button("Home", style={"position": "absolute", "left": "0", "margin-left": "15px", "margin-top": "4px"}), href="/"),
            dbc.DropdownMenu(
                children=[menu_item(v.title, k) for k, v in pages_info.items()],
                nav=True,
                in_navbar=True,
                style={"fontSize": "12pt"},
                label="Reports",
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
    core.Loading(id='page-content', type='dot'),
    html.Footer(id='footer', children=[
        html.Hr(), 
        "Dashi version {0} | Data version ".format(version), 
        html.Span(id='data-version'),
        html.Br(),
        random.choice(positivity)])
])


def init_callbacks(dash_app):
    dash_app.config.suppress_callback_exceptions = True

    @dash_app.callback(
        Output('navbar', 'brand'),
        [Input('url', 'pathname')]
    )
    def nav_handler(path):
        """Get the requested page"""
        if path == '/None' or path is None:
            return default_title
        requested = path[1:]  # drop the leading slash
        if requested in pages_info.keys():
            page = pages_info[requested]
            return page.title if page.title else default_title
        return default_title

    @dash_app.callback(
        [
            Output('page-content', 'children'),
            Output('data-version', 'children'),
        ],
        [
            Input('url', 'pathname'),
            Input('url', 'search')
        ])
    def content_handler(path, qs):
        """Get the requested page content and fill in the ETL
        data version info at the bottom of the page"""
        if path == '/None' or path is None:
            return '404', None
        requested = path[1:] # drop the leading slash
        if requested in pages_info.keys():
            page = pages_info[requested]
            return [page.layout(qs), page.dataversion()]
        return '404', None
