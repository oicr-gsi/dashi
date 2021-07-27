from collections import namedtuple
import importlib
import sys
import traceback

import dash_html_components as html
from .utility import sidebar_utils

prefix = "application.dash_application.views."

# An array of module names as strings, one per page
# These are for the modules that Dash can graph
pagenames = [
    "bcl2barcode",
    "call_ready_ts",
    "call_ready_rna",
    "call_ready_wgs",
    "runscanner_illumina_flowcell",
    "sample_swaps",
    "single_lane_ts",
    "single_lane_rna",
    "single_lane_wgs",
    "SARS-CoV-2",
    'single_lane_cfmedip'
]

# Emulates the module members that are called in known_pages_router in case of error
ErrorPage = namedtuple('ErrorPage', 'layout title dataversion page_name init_callbacks')

# Please do not edit this array
# https://media2.giphy.com/media/DkaZuJGcwwN32/200.webp?cid=790b761109288a37049d763e1175d0e4ca6307eee3351333&rid=200.webp
pages = []


def error_div(module_name, jira_error_summary, jira_error_text):
    """
    This emulates the `layout` function from the Dashi views. It displays the error
    message and provides a link to generate a JIRA ticket

    Args:
        module_name: Which module name failed
        jira_error_summary: The summary of the JIRA ticket
        jira_error_text: The description in the JIRA ticket

    Returns: Dashi div to display

    """
    def f(_):
        return html.Div(id=module_name, children=[
            html.H3("Unexpected Error: Failed to load cache"),
            sidebar_utils.jira_button(
                "Report This Error",
                module_name + "_jira_failed_cache_button",
                {"display": "inline-block"},
                sidebar_utils.construct_jira_link_general(
                    jira_error_text, jira_error_summary
                ),
                )
        ])

    return f


# Please do not edit this loop
for name in pagenames:
    try:
        pages.append(importlib.import_module(prefix + name))
    except (IOError, OSError):
        exception = traceback.format_exc()
        jira_summary = "Error loading cache in " + name + " Dashi view"
        print(exception, file=sys.stderr)
        pages.append(ErrorPage(
            error_div(name, jira_summary, exception),
            name,
            lambda: "Unknown version",
            name,
            lambda x: None,
        ))


# TODO: Maybe move the user-defined array to another file and import it into a scarier-sounding file
