import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids

#TODO: gsiqcetl imports?

ids = init_ids([
    'error',
    'run_select',
    'bcl2fastq_url',
    'known_index_bar',
    'known_unknown_pie',
    'known_fraction',
    'unknown_index_bar'
])

layout = html.Div(
    children=[
        # This element doesn't work correctly in a multi-app context. Left in code for further work
        # ToDO
        # https://jira.oicr.on.ca/browse/GR-776 and https://jira.oicr.on.ca/browse/GR-777
        core.Location(id=ids['bcl2fastq_url'], refresh=False),
        core.ConfirmDialog(
            id=ids['error'],
            message=(
                'You have input an incorrect run. Click either "Ok" or '
                '"Cancel" to return to the most recent run.'
            ),
        ),
        core.Dropdown(
            id=ids['run_select'],
            #   Options is concantenated string versions of all_runs.
            options=[{"label": r, "value": r} for r in all_runs],
            value=all_runs[0],
            clearable=False,
        ),
        core.Graph(id=ids['known_index_bar']),
        html.Div(
            [
                html.Div(
                    [
                        core.Graph(id=ids['known_unknown_pie']),
                        core.Textarea(
                            id=ids['known_fraction'],
                            style={"width": "100%"},
                            readOnly=True,
                            # This is the textbox at the bottom, hover over to see title
                            title=(
                                "Assumptions are made about which indexes are known "
                                "or unknown. This is due to multiple bcl2fastq analyses "
                                "being used on one run. This number should be 100%."
                            ),
                        ),
                    ],
                    style={"width": "25%", "display": "inline-block"},
                ),
                html.Div(
                    [core.Graph(id=ids['unknown_index_bar'])],
                    style={
                        "width": "75%",
                        "display": "inline-block",
                        "float": "right",
                    },
                ),
            ]
        ),
    ]
)


def init_callbacks(dash_app):

