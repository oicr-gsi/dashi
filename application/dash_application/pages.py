import importlib
import os
import sys
import traceback
from collections import namedtuple

from dash import html

from .utility import sidebar_utils

# Get the installed pages
all_reports = []
_report_sources = os.getenv("REPORT_SOURCES")
for source in _report_sources.split(","):
    sys.path.append(source)
    for (dirpath, _, filenames) in os.walk(source):
        for filename in filenames:
            if filename.endswith(".py"):
                module = importlib.import_module(os.path.join(dirpath, filename))
                all_reports.append(getattr(module, "page_name").replace("-", "_"))

_enabled_env = os.getenv("ENABLED_REPORTS")
if _enabled_env:
    _requested = [n.strip() for n in _enabled_env.split(",") if n.strip()]
    for _name in _requested:
        if _name not in all_reports:
            print("Unknown report name in ENABLED_REPORTS: " + _name, file=sys.stderr)
    pagenames = [n for n in _requested if n in all_reports]
else:
    pagenames = all_reports

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
