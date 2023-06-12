from dash import html
from dash import dcc as core
from dash import dash_table
from dash.dependencies import Input, Output
import pandas

from ..utility import df_manipulation as util
from ..dash_id import init_ids

page_name = "bcl2barcode-index-qc"
title = "Bcl2Barcode Index QC"

ids = init_ids(
    [
        "error",
        "run_select",
        "bcl2fastq_url",
        "known_index_bar",
        "known_unknown_pie",
        "known_fraction",
        "unknown_index_bar",
        "known_data_table",
        "unknown_data_table",
        "tabs_data_table",
    ]
)

DATAVERSION = util.cache.versions(["bcl2barcodecaller"])
known = util.get_bcl2barcodecaller_known()
unknown = util.get_bcl2barcodecaller_unknown()
summary = util.get_bcl2barcodecaller_summary()

# In case there is a run that is all unknown barcodes
all_runs = pandas.concat([known[util.BCL_KNOWN.Run], unknown[util.BCL_UNKNOWN.Run]]).unique()
all_runs = sorted(all_runs, reverse=True)

KNOWN_DATA_TABLE_COLS = [
    {"name": "Library", "id": util.BCL_KNOWN.LibraryAlias},
    {"name": "Index", "id": util.BCL_KNOWN.Barcodes},
    {"name": "Library PF Clusters", "id": util.BCL_KNOWN.Count},
    {"name": "Lane", "id": util.BCL_KNOWN.Lane},
]

UNKNOWN_DATA_TABLE_COLS = [
    {"name": "Index", "id": util.BCL_UNKNOWN.Barcodes},
    {"name": "Count", "id": util.BCL_UNKNOWN.Count},
    {"name": "Lane", "id": util.BCL_UNKNOWN.Lane},
]


def dataversion():
    return DATAVERSION


def layout(qs):
    return html.Div(
        children=[
            core.Dropdown(
                id=ids["run_select"],
                #   Options is concatenated string versions of all_runs.
                options=[{"label": r, "value": r} for r in all_runs],
                value=all_runs[0],
                clearable=False,
            ),
            core.Graph(id=ids["known_index_bar"]),
            html.Div(
                [
                    html.Div(
                        [
                            core.Graph(id=ids["known_unknown_pie"]),
                        ],
                        style={"width": "25%", "display": "inline-block"},
                    ),
                    html.Div(
                        [core.Graph(id=ids["unknown_index_bar"])],
                        style={"width": "75%", "display": "inline-block", "float": "right"},
                    ),
                ]
            ),
            html.Br(),
            core.Tabs(id=ids['tabs_data_table'], children=[
                core.Tab(label='Known Barcodes', children=[
                    dash_table.DataTable(
                        id=ids["known_data_table"],
                        columns=KNOWN_DATA_TABLE_COLS,
                        export_format='csv',
                        export_headers='names',
                        sort_action='native',
                    )
                ]),
                core.Tab(label='Unknown Barcodes', children=[
                    dash_table.DataTable(
                        id=ids["unknown_data_table"],
                        columns=UNKNOWN_DATA_TABLE_COLS,
                        export_format='csv',
                        export_headers='names',
                        sort_action='native',
                    )
                ])
            ]),
        ],
        # The scrollbars of the Dash dropdowns overlap with the (Firefox) browser scrollbar
        style={"margin-right": "5px"}
    )


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["known_index_bar"], "figure"),
            Output(ids["unknown_index_bar"], "figure"),
            Output(ids["known_unknown_pie"], "figure"),
            Output(ids["known_data_table"], "data"),
            Output(ids["unknown_data_table"], "data")
        ],
        [
            Input(ids["run_select"], "value")
        ],
    )
    def update_layout(run_alias):
        """
        When input(run dropdown) is changed, known index bar, unknown index bar,
        piechart and textarea are updated

        Parameter:
            run_alias: user-selected run name from dropdown
        Returns:
            functions update_known_index_bar, update_unknown_index_bar,
            update_pie_chart's data value, and update_pie_chart's fraction value
        """
        known_run = known[known[util.BCL_KNOWN.Run] == run_alias]
        unknown_run = unknown[unknown[util.BCL_UNKNOWN.Run] == run_alias]

        return (
            create_known_index_bar(known_run),
            create_unknown_index_bar(unknown_run),
            create_pie_chart(run_alias),
            known_run.to_dict("records"),
            unknown_run.to_dict("records")
        )


def create_known_index_bar(run):
    """ Function to create known index bar according to user selected run
           Parameters:
               run: Dataframe filtered and cleaned by 'update_layout'
           Returns:
              data and values for the layout of stacked bar graph of sample indices
              creates bar graph "known_index_bar"
       """
    data = []
    for i, d in run.groupby([util.BCL_KNOWN.Barcodes, util.BCL_KNOWN.LibraryAlias]):
        data.append({
            "x": list(d[util.BCL_KNOWN.LibraryAlias].unique()),
            # One library can be run on multiple lanes. Sum them together.
            "y": [d[util.BCL_KNOWN.Count].sum()],
            "type": "bar",
            "name": i[0],
            "marker": {"line": {"width": 2, "color": "rgb(255,255, 255)"}},
        })
    
    return {
        "data": data,
        "layout": {
            "barmode": "stack",
            "title": "Sample Indices",
            # dtick ensures tick mark labels aren't elided
            # https://stackoverflow.com/questions/42187139/plotly-horizontal-bar-display-all-y-axis-labels
            "xaxis": {"title": "Library", "automargin": True, "dtick": 1},
            "yaxis": {"title": "Clusters"},
            "showlegend": True,
            "height": 600,
        },
    }


def create_unknown_index_bar(run):
    """ Function to create unknown index bar  according to user selected run
            Parameters:
                run: The run to calculate for
            Returns:
                data and layout values for stacked bar graph for unknown indices
                creates unknown_index_bar bar graph
              """
    run = run.sort_values(util.BCL_UNKNOWN.Count, ascending=False)
    run = run.head(30)
    data = []

    for lane, d in run.groupby(util.BCL_UNKNOWN.Lane):
        data.append({
            "x": list(d[util.BCL_UNKNOWN.Barcodes]),
            "y": list(d[util.BCL_UNKNOWN.Count]),
            "type": "bar",
            "name": lane
        })
    
    return {
        "data": data,
        "layout": {
            "barmode": "stack",
            "title": "Unknown Indices",
            "xaxis": {"title": "Index", "automargin": True},
            "yaxis": {"title": "Clusters"},
            "showlegend": True
        },
    }


def create_pie_chart(run_alias):
    known_count = summary[summary[util.BCL_SUMMARY.Run] == run_alias][util.BCL_SUMMARY.KnownClusters]
    unknown_count = summary[summary[util.BCL_SUMMARY.Run] == run_alias][util.BCL_SUMMARY.UnknownClusters]

    if len(known_count) > 0 and len(unknown_count) > 0:
        known_count = known_count.iloc[0]
        unknown_count = unknown_count.iloc[0]
    return (
        {
            "data": [
                {
                    "labels": ["Known", "Unknown"],
                    "values": [known_count, unknown_count],
                    "type": "pie",
                    "marker": {"colors": ["#349600", "#ef963b"]},
                }
            ],
            "layout": {"title": "Flow Cell Composition of Known/Unknown Indices"},
        }
    )
