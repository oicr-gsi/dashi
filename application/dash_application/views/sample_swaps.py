import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import gsiqcetl.picard.crosscheckfingerprints.utility
import pinery

from ..dash_id import init_ids
from ..utility import df_manipulation, sidebar_utils
from ..utility.df_manipulation import CROSSCHECKFINGERPRINTS_COL as COL

PINERY_COL = pinery.column.SampleProvenanceColumn
RUN_COLS = pinery.column.RunsColumn

page_name = "sample_swaps"
title = "Sample Swaps"

# This cutoff should be very conservative to make sure all shown swaps are real
LOD_CUTOFF = 100

ids = init_ids([
    # Buttons
    'update-button-top',

    # Sidebar
    "all-projects",
    "projects-list",

    # Main Table
    "table",
])

special_cols = {
    "latest_run": "LATEST_RUN"
}

fingerprints = df_manipulation.get_crosscheckfingerprints()
fingerprints[COL.Result] = gsiqcetl.picard.crosscheckfingerprints.utility.calculate_results(
    fingerprints, LOD_CUTOFF, LOD_CUTOFF
)

# Picard uses LOD Score as truth ("UNEXPECTED" refers to the library pair)
# Instead use library pair as truth ("UNEXPECTED" refers to LOD score that does not
# match library identities)
fingerprints[COL.Result] = fingerprints[COL.Result].replace({
    "UNEXPECTED_MATCH": "UNEXPECTED_MISMATCH",
    "UNEXPECTED_MISMATCH": "UNEXPECTED_MATCH",
})

# This pulls out swaps
swap = fingerprints[fingerprints[COL.Result].str.startswith("UNEXPECTED")].copy()

pinery_samples = df_manipulation.get_pinery_samples()
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.RunLeft, COL.LaneLeft, COL.BarcodeLeft]
)
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.RunRight, COL.LaneRight, COL.BarcodeRight], "_RIGHT"
)
swap = df_manipulation.df_with_run_info(swap, COL.RunLeft)
swap = df_manipulation.df_with_run_info(swap, COL.RunRight, "_RIGHT")

# Pair-wise comparison is done both ways. Remove one of them to decrease redundant info
swap["PAIR"] = swap.apply(
    lambda x: tuple(sorted([x[COL.GroupValueLeft], x[COL.GroupValueRight]])), axis=1
)
swap = swap.drop_duplicates("PAIR")
# Exclude OICR control libraries
swap = swap[~swap[COL.LibraryLeft].str.startswith("GSICAPBENCH")]
swap = swap[~swap[COL.LibraryLeft].str.startswith("GLCS")]
# Get the latest run of the pair for sorting purposes
swap[special_cols["latest_run"]] = swap[
    [RUN_COLS.StartDate, RUN_COLS.StartDate + "_RIGHT"]
].max(1)

COLUMNS_TO_SHOW = [
    COL.LibraryLeft,
    COL.LibraryRight,
    special_cols["latest_run"],
    COL.Result,
    COL.LODScore,
]

# Pair-wise comparison is done within project (for now), so left project is sufficient
ALL_PROJECTS = df_manipulation.unique_set(swap, PINERY_COL.StudyTitle)

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
                html.Div(className='sidebar four columns', children=[
                    html.Button('Update', id=ids['update-button-top'], className="update-button"),
                    html.Br(),
                    html.Br(),
                    sidebar_utils.select_projects(
                        ids["all-projects"],
                        ids["projects-list"],
                        ALL_PROJECTS,
                        INITIAL["projects"]
                    ),
                ]),
                html.Div(className="seven columns", children=[
                    dash_table.DataTable(
                        id=ids['table'],
                        columns=[{"name": i, "id": i} for i in COLUMNS_TO_SHOW],
                        data=swap.to_dict('records'),
                        sort_action="native",
                        sort_by=[{"column_id": "LATEST_RUN", "direction": "desc"}],
                        export_format="csv",
                        include_headers_on_copy_paste=True,
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
        [State(ids['projects-list'], 'value')],
    )
    def update_pressed(_click, projects):
        df = swap[swap[PINERY_COL.StudyTitle].isin(projects)]
        return df.to_dict('records')

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]
