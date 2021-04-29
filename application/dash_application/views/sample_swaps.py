import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import pinery
import numpy
import pandas

from ..dash_id import init_ids
from ..utility import df_manipulation, sidebar_utils
from ..utility.df_manipulation import CROSSCHECKFINGERPRINTS_COL as COL

PINERY_COL = pinery.column.SampleProvenanceColumn
RUN_COLS = pinery.column.RunsColumn

page_name = "sample_swaps"
title = "Sample Swaps"

# LOD scores around 0 mean not enough data to determine swap
# Set a zone left and right of 0 that where swaps will be ignored
AMBIGUOUS_ZONE = 20

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
    "latest_run": "LATEST_RUN",
    "same_identity": "SAME_IDENTITY",
    "closest_libraries": "CLOSEST_LIBRARIES",
    "closest_libraries_count": "CLOSEST_LIBRARIES_COUNT",
}

swap = df_manipulation.get_crosscheckfingerprints()
swap = swap[~swap[COL.LibraryLeft].str.startswith("GSICAPBENCH")]
swap = swap[~swap[COL.LibraryLeft].str.startswith("GLCS")]
# The below algorithm won't work if libraries are compared with themselves
swap = swap[swap[COL.LibraryLeft] != swap[COL.LibraryRight]]

pinery_samples = df_manipulation.get_pinery_samples()
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.RunLeft, COL.LaneLeft, COL.BarcodeLeft]
)
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.RunRight, COL.LaneRight, COL.BarcodeRight], "_RIGHT"
)
swap = df_manipulation.df_with_run_info(swap, COL.RunLeft)
swap = df_manipulation.df_with_run_info(swap, COL.RunRight, "_RIGHT")

# Get the latest run of the pair for sorting purposes
swap[special_cols["latest_run"]] = swap[
    [RUN_COLS.StartDate, RUN_COLS.StartDate + "_RIGHT"]
].max(1)
swap[special_cols["same_identity"]] = (
    swap[PINERY_COL.RootSampleName] == swap[PINERY_COL.RootSampleName + "_RIGHT"]
)


def closest_lib(input_df):
    """
    The `input_df` must be sored by LOD_SCORE (descending) and have one library
    in the LEFT_LIBRARY column. Returns the row with the most similar library and
    adds a column that list the most similar libraries that had to be traversed until
    one from the same patient was identified. If there was no swap, only one library
    should have been traversed.
    """
    # Index will be used with `iloc` call, so has to go from 0 to number of rows
    lib_df = input_df.reset_index(drop=True)
    # The closest library
    return_df = lib_df.head(1).copy()
    # Libraries that came from the same patient
    same_ident_df = lib_df[lib_df[special_cols["same_identity"]]]
    if same_ident_df.empty:
        return_df[special_cols["closest_libraries_count"]] = 0
        return_df[special_cols["closest_libraries"]] = numpy.nan
        return return_df

    # Get libraries up to and including the first that came from the same patient
    closest_df = lib_df.iloc[:same_ident_df.index[0] + 1]
    return_df[special_cols["closest_libraries_count"]] = len(closest_df)
    return_df[special_cols["closest_libraries"]] = ",".join(closest_df["RIGHT_LIBRARY"])
    return return_df


result = []
# Two for loops (blah) go through each swap workflow and then check each library
# Will try to vectorize this if this approach proves superior to previous hard LOD cutoff
for _, top in swap.groupby(COL.FileSWID):
    top = top.sort_values([COL.LibraryLeft, COL.LODScore], ascending=False)
    for _, d in top.groupby(COL.LibraryLeft):
        result.append(closest_lib(d))

swap = pandas.concat(result)
swap = swap[swap[COL.LODScore].abs() > AMBIGUOUS_ZONE]
swap = swap[swap[special_cols["closest_libraries_count"]] > 1]

COLUMNS_TO_SHOW = [
    COL.LibraryLeft,
    COL.LibraryRight,
    COL.LODScore,
    special_cols["latest_run"],
    special_cols["closest_libraries"],
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
                        style_cell={'textAlign': 'left', 'padding-right': '50px'},
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
