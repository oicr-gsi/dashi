from collections import namedtuple
import json
import logging
import os
import random
import dash_bootstrap_components as dbc
from dash import html
from dash import dcc as core
from dash.dependencies import Input, Output

from . import pages
from ..routes import version


logger = logging.getLogger(__name__)

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


def load_user_messages(json_path=os.getenv("DISPLAY_USER_MESSAGE")):
    """
    Loads the user messages. Raises an exception in the following cases:
    * Cannot parse JSON file
    * If message is not a string
    * If the view of the message does not exist
    * If multiple messages exist for a single view
    """
    if json_path is None:
        return {}

    if not os.path.isfile(json_path):
        logger.warning("User message JSON file does not exist")
        return {}

    def json_parse(pairs):
        parsed = {}

        for k, v in pairs:
            if not isinstance(v, str):
                raise TypeError("User messages must be a string: {}".format(v))

            if k not in pages_info:
                raise KeyError("Unknown page name: {}".format(k))

            if k in parsed:
                raise KeyError("Multiple messages for the same page: {}".format(k))
            else:
                parsed[k] = v

        return parsed

    with open(json_path, "r") as f:
        return json.load(f, object_pairs_hook=json_parse)


# Messages to the displayed to users in specific views
# Key is the page name and the value is the message to be displayed
# If page name does not exist or value is `None` message won't be displayed
user_message = load_user_messages()


# Default layout element (wraps the page layout elements which are returned by the router)
layout = html.Div([
    core.Location(id='url', refresh=False),
    navbar(default_title),
    dbc.Alert(
        id="user_message",
        is_open=False,
        color="danger",
        style={"margin-left": "15px", "margin-right": "15px"},
    ),
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

    @dash_app.callback(
        [
            Output('user_message', 'children'),
            Output('user_message', 'is_open'),
        ],
        [
            Input('url', 'pathname'),
        ])
    def display_user_message(path):
        """
        If there is a user message associated with the loaded page, display it.
        """
        if path is None:
            return "", False

        requested = path[1:] # drop the leading slash
        message = user_message.get(requested, None)
        if message is None:
            return "", False
        else:
            return message, True
