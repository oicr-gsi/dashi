from dash import dcc as core
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table
import pinery
import logging

from ..dash_id import init_ids
from ..utility import df_manipulation, sidebar_utils
from ..utility.df_manipulation import CROSSCHECKFINGERPRINT_CALLER_COL as COL

logger = logging.getLogger(__name__)

PINERY_COL = pinery.column.SampleProvenanceColumn
RUN_COLS = pinery.column.RunsColumn

page_name = "sample_swaps"
title = "Sample Swaps"

ids = init_ids([
    # Buttons
    'update-button-top',

    # Sidebar
    "all-projects",
    "checkbox_show_swaps",
    "projects-list",

    # Main Table
    "table",
])

special_cols = {
    "latest_run": "LATEST_RUN",
    "miso": "miso",
    "miso_match": "miso_match",
}

swap = df_manipulation.get_crosscheckfingerprint_caller()
swap.sort_values([COL.LibraryName, COL.SwapCall, COL.LODScore], inplace=True)

pinery_samples = df_manipulation.get_pinery_samples()
pinery_samples = pinery_samples[[
    PINERY_COL.SequencerRunName,
    PINERY_COL.LaneNumber,
    PINERY_COL.IUSTag,
    PINERY_COL.ParentSampleName,
    PINERY_COL.SampleName,
    PINERY_COL.RootSampleName,
]]

swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.Run, COL.Lane, COL.Barcode]
)
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.RunMatch, COL.LaneMatch, COL.BarcodeMatch], "_MATCH"
)
swap = df_manipulation.df_with_run_info(swap, COL.Run)
swap = df_manipulation.df_with_run_info(swap, COL.RunMatch, "_MATCH")

# Take all the runs where a swap has been called for a given library and store the latest run
swap["start_date_max"] = swap[[RUN_COLS.StartDate, RUN_COLS.StartDate + "_MATCH"]].max(axis=1)
latest_swap = swap[swap[COL.PairwiseSwap]].groupby(COL.LibraryName)["start_date_max"].max().rename(special_cols["latest_run"])
swap = swap.merge(latest_swap, how="outer", left_on=COL.LibraryName, right_index=True)
swap[special_cols["latest_run"]] = swap[special_cols["latest_run"]].fillna(swap["start_date_max"])
swap[special_cols["latest_run"]] = swap[special_cols["latest_run"]].dt.date
swap.drop(columns="start_date_max")

swap[special_cols["miso"]] = swap[COL.LibraryDesign] + "_" + swap[COL.TissueType] + "_" + swap[COL.TissueOrigin]
swap[special_cols["miso_match"]] = swap[COL.LibraryDesignMatch] + "_" + swap[COL.TissueTypeMatch] + "_" + swap[COL.TissueOriginMatch]

# There is a row for each lib, lib_match, lane, run permutation
# The LODs are stable between the lanes, so pick the highest one
# If there is both a swap and a not swap call, both will be shown
swap = swap.drop_duplicates(
    [COL.LibraryName, COL.LibraryNameMatch, COL.PairwiseSwap], keep="last"
)

# The swaps to display. Basically all swaps and then the first expected match (if it exists)
indx = []
for _, g in swap.groupby(COL.LibraryName, sort=False):
    indx.extend(g[g[COL.PairwiseSwap]].index)
    mtch = g[~g[COL.PairwiseSwap]].index
    if len(mtch) > 0 and any(g[COL.SwapCall]):
        indx.append(mtch[0])

swap['swap_display'] = swap.index.isin(indx)

DATA_COLUMN = [
    COL.Project,
    COL.LibraryName,
    special_cols["miso"],
    COL.LibraryNameMatch,
    special_cols["miso_match"],
    COL.LODScore,
    COL.PairwiseSwap,
    COL.SameBatch,
    special_cols["latest_run"],
    PINERY_COL.ParentSampleName,
    PINERY_COL.ParentSampleName + "_MATCH",
]

# These columns will be in the downloaded csv, but not displayed by default in Dashi
DOWNLOAD_ONLY_COLUMNS = [
    PINERY_COL.ParentSampleName,
    PINERY_COL.ParentSampleName + "_MATCH",
]

TABLE_COLUMNS = [{"name": i, "id": i} for i in DATA_COLUMN]
for d in TABLE_COLUMNS:
    if d["id"] == COL.LODScore:
        d["format"] = dash_table.Format.Format(
            scheme=dash_table.Format.Scheme.decimal_integer,
        )
        d["type"] = "numeric",
    elif PINERY_COL.ParentSampleName in d["id"]:
        d["hideable"] = True

# Pair-wise comparison is done within project (for now), so left project is sufficient
ALL_PROJECTS = df_manipulation.unique_set(swap,COL.Project)

INITIAL = {
    "projects": ALL_PROJECTS,
}


def dataversion():
    return df_manipulation.cache.versions(["crosscheckfingerprints"])


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)

    if len(query["req_projects"]) > 0:
        INITIAL["projects"] = query["req_projects"]

    return core.Loading( fullscreen=True, type="dot", children=[
        html.Div(className='body', children=[
            html.Div(className='row flex-container', children=[
                html.Div(className='sidebar two columns', children=[
                    html.Button('Update', id=ids['update-button-top'], className="update-button"),
                    html.Br(),
                    html.Br(),
                    sidebar_utils.select_projects(
                        ids["all-projects"],
                        ids["projects-list"],
                        ALL_PROJECTS,
                        INITIAL["projects"]
                    ),
                    core.Checklist(
                        id=ids["checkbox_show_swaps"],
                        options=[
                            {"label": "Only show swaps", "value": "swap"},
                        ],
                        value=["swap"]
                    )
                ]),
                html.Div(className="seven columns", children=[
                    dash_table.DataTable(
                        id=ids['table'],
                        columns=TABLE_COLUMNS,
                        hidden_columns=DOWNLOAD_ONLY_COLUMNS,
                        data=swap[swap["swap_display"]].to_dict('records'),
                        sort_action="native",
                        sort_by=[
                            {"column_id": special_cols["latest_run"], "direction": "desc"},
                            {"column_id": COL.LibraryName, "direction": "desc"},
                        ],
                        export_format="csv",
                        export_columns="all",
                        include_headers_on_copy_paste=True,
                        style_data={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_cell={'textAlign': 'left', 'padding-right': '5px'},
                        style_data_conditional=[
                            {
                                "if": {"row_index": "odd"},
                                "backgroundColor": "rgb(248, 248, 248)"
                            }
                        ],
                        style_header={
                            "backgroundColor": "rgb(230, 230, 230)",
                            "fontWeight": "bold"
                        },
                    )
                ])
            ])
        ])
    ])


def init_callbacks(dash_app):
    @dash_app.callback(
        Output(ids["table"], "data"),
        [Input(ids["update-button-top"], "n_clicks")],
        [
            State(ids["projects-list"], "value"),
            State(ids["checkbox_show_swaps"], "value"),
        ]
    )
    def update_pressed(_click, projects, show_swap):
        if "swap" in show_swap:
            df = swap[swap["swap_display"]]
        else:
            df = swap
        df = df[df[COL.Project].isin(projects)]
        return df.to_dict('records')

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]
