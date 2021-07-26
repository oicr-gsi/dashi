import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import plot_builder
from ..utility import log_utils
from ..utility import table_builder

import logging

logger = logging.getLogger(__name__)

""" Set up elements needed for page """
page_name = "illumina_flowcell"
title = "Run Scanner Illumina Flow Cell"

ids = init_ids([
    # Buttons
    "jira-issue-with-runs-button",
    "general-jira-issue-button",
    "update-button-top",
    "update-button-bottom",

    # Graphs
    "graphs",

    # Side bar
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "highlight-run",
    "instruments-list",

    # All buttons
    "all-instruments",
    
    # Tables
    "data-table",
])

COL = util.RUNSCANNER_FLOWCELL_COL
INSTRUMENT_COL = util.INSTRUMENTS_COL

DF = util.get_runscanner_flowcell()
DF = DF.drop(columns=COL.Platform)  # Conflicts with column added by `df_with_run_info`
DF = DF.fillna(value={COL.WorkflowType: "Unspecified"})
DF = DF[DF[COL.MISOHealthType] == "Completed"]
DF = util.df_with_run_info(DF, COL.Run)

ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(DF)
ALL_WORKFLOW_TYPES = util.unique_set(DF, COL.WorkflowType)

shape_colour = plot_builder.ColourShapeRunscanner(
    ILLUMINA_INSTRUMENT_MODELS,
    ALL_WORKFLOW_TYPES,
)

INITIAL = {
    "instruments": [],
    "first_sort": COL.StartDate,
    "second_sort": INSTRUMENT_COL.ModelName,
    "colour_by": INSTRUMENT_COL.ModelName,
    "shape_by": COL.WorkflowType,
    "shownames_val": None,
}

# Add shape col to WG dataframe
DF = plot_builder.add_graphable_cols(DF, INITIAL, shape_colour.items_for_df())

SORT_BY = [
    {"label": "Instruments", "value": INSTRUMENT_COL.ModelName},
    {"label": "Start Date", "value": COL.StartDate},
]

collapsing_functions = {}


def dataversion():
    return util.cache.versions(["runscannerillumina"])


def generate_q30(df, graph_params):
    return plot_builder.Subplot(
        "Percentage Above Q30",
        df,
        None,
        lambda d: d[COL.PercentAboveQ30],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        lambda d: d[COL.Run],
        None,
        "markers",
        None,
        None,
        False
    )


GRAPHS = [
    generate_q30
]


# Layout elements
def layout(_query_string):
    df = plot_builder.reshape_runscanner_df(
        DF,
        INITIAL["instruments"],
        INITIAL["first_sort"],
        INITIAL["second_sort"],
        INITIAL["colour_by"],
        INITIAL["shape_by"],
        shape_colour.items_for_df(),
        INITIAL["shownames_val"],
    )

    all_runs = util.unique_set(df, COL.Run, True)

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("Open an issue",
                                          ids['general-jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title)),
            ]),
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
                    html.Button(
                        "Update", id=ids['update-button-top'], className="update-button"
                    ),

                    html.Br(),
                    html.Br(),

                    sidebar_utils.select_instruments(
                        ids["all-instruments"],
                        ids["instruments-list"],
                        ILLUMINA_INSTRUMENT_MODELS
                    ),

                    sidebar_utils.hr(),

                    sidebar_utils.select_first_sort(
                        ids['first-sort'],
                        INITIAL["first_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_second_sort(
                        ids["second-sort"],
                        INITIAL["second_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_colour_by(
                        ids['colour-by'],
                        shape_colour.dropdown(),
                        INITIAL["colour_by"]
                    ),

                    sidebar_utils.select_shape_by(
                        ids['shape-by'],
                        shape_colour.dropdown(),
                        INITIAL["shape_by"]
                    ),

                    sidebar_utils.highlight_run(
                        ids['highlight-run'], all_runs
                    ),

                    html.Br(),
                    html.Button(
                        "Update",
                        id=ids['update-button-bottom'],
                        className="update-button"
                    ),
                ]),

                # Graphs + Tables tabs
                html.Div(className="seven columns", children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(label="Graphs", children=[
                            plot_builder.create_graph_element_with_subplots(
                                ids["graphs"], df, INITIAL, GRAPHS
                            ),
                        ]),
                        # Tables tab
                        core.Tab(label="Tables", children=[
                            table_builder.build_table(
                                ids["data-table"],
                                df.columns,
                                df
                            )
                        ])
                    ])
                ])
            ]),
        ]),
    ])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["graphs"], "figure"),
            Output(ids["highlight-run"], "options"),
            Output(ids["data-table"], "data"),
        ],
        [
            Input(ids["update-button-top"], "n_clicks"),
            Input(ids["update-button-bottom"], "n_clicks")
        ],
        [
            State(ids["instruments-list"], "value"),
            State(ids["first-sort"], "value"),
            State(ids["second-sort"], "value"),
            State(ids["colour-by"], "value"),
            State(ids["shape-by"], "value"),
            State(ids["highlight-run"], "value"),
        ]
    )
    def update_pressed(
            click,
            click2,
            instruments,
            first_sort,
            second_sort,
            colour_by,
            shape_by,
            highlighted_runs,
    ):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = plot_builder.reshape_runscanner_df(
            DF,
            instruments,
            first_sort,
            second_sort,
            colour_by,
            shape_by,
            shape_colour.items_for_df(),
            highlighted_runs,
        )

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": None,
        }

        highlightable_runs = util.unique_set(df, COL.Run, True)

        return (
            plot_builder.generate_subplot_from_func(df, graph_params, GRAPHS),
            [{'label': x, 'value': x} for x in highlightable_runs],
            df.to_dict("records"),
        )

    @dash_app.callback(
        Output(ids['instruments-list'], 'value'),
        [Input(ids['all-instruments'], 'n_clicks')]
    )
    def all_instruments_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ILLUMINA_INSTRUMENT_MODELS]
