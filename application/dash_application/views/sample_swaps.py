from dash import dcc as core
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table
from dash.dash_table import Format
import pinery
import pandas
import os
import logging

from ..dash_id import init_ids
from ..utility import df_manipulation, sidebar_utils
from ..utility.df_manipulation import CROSSCHECKFINGERPRINTS_COL as COL

logger = logging.getLogger(__name__)

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
    "checkbox_show_swaps",
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

rename_columns = {
    PINERY_COL.StudyTitle: 'PROJECT',
}

df = df_manipulation.get_crosscheckfingerprints()

# The COL.ClosestLibrariesCount column states how many libraries had to be traversed until a matching one is found
# If 0: No matching library exist (patient has been sequenced only once), so no other libraries should match
# If 1: Closest library is from the same patient. No swap.
# If 2 or more: Closest library is NOT from the same patient. Swap has occurred.

# Libraries that correctly match (the closest library count is 1) don't have ot go through expensive `groupby`
swap = df[df[COL.ClosestLibrariesCount] != 1].sort_values([COL.QueryLibrary, COL.LODScore], ascending=False)

result = []
for _, lib in swap.groupby(COL.QueryLibrary, sort=False):
    # The closest library
    return_df = lib.head(1).copy()
    rest = lib.iloc[1:]
    if len(rest) > 0:
        closest_lib = (
                rest[COL.MatchLibrary] +
                " (" +
                rest[COL.LODScore].round().astype(int).astype(str) +
                ")"
        )
        return_df[special_cols["closest_libraries"]] = ", ".join(closest_lib)
    result.append(return_df)

if len(result) > 0:
    swap = pandas.concat(result)
else:
    swap = pandas.DataFrame(columns=df.columns)

# If there is no swap, the closest library is just the matched library
non_swaps = df[df[COL.ClosestLibrariesCount] == 1].copy()
non_swaps[special_cols["closest_libraries"]] = non_swaps[COL.MatchLibrary]
swap = pandas.concat([swap, non_swaps])

pinery_samples = df_manipulation.get_pinery_samples()
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.QueryRun, COL.QueryLane, COL.QueryBarcode]
)
swap = df_manipulation.df_with_pinery_samples_ius(
    swap, pinery_samples, [COL.MatchRun, COL.MatchLane, COL.MatchBarcode], "_MATCH"
)
swap = df_manipulation.df_with_run_info(swap, COL.QueryRun)
swap = df_manipulation.df_with_run_info(swap, COL.MatchRun, "_MATCH")

# DataFrame that's empty has issues with date column type
if len(swap) > 0:
    # Get the latest run of the pair for sorting purposes and make format YYYY-MM-DD
    swap[special_cols["latest_run"]] = swap[
        [RUN_COLS.StartDate, RUN_COLS.StartDate + "_MATCH"]
    ].max(1).dt.date
    swap[special_cols["same_identity"]] = (
        swap[PINERY_COL.RootSampleName] == swap[PINERY_COL.RootSampleName + "_MATCH"]
    )

swap[COL.QueryLibrary] = (
        swap[COL.QueryLibrary] +
        " (" +
        swap[PINERY_COL.LibrarySourceTemplateType] +
        ", " +
        swap[PINERY_COL.TissueType] +
        ", " +
        swap[PINERY_COL.TissueOrigin] +
        ")"
)
swap[COL.MatchLibrary] = (
        swap[COL.MatchLibrary] +
        " (" +
        swap[PINERY_COL.LibrarySourceTemplateType + "_MATCH"] +
        ", " +
        swap[PINERY_COL.TissueType + "_MATCH"] +
        ", " +
        swap[PINERY_COL.TissueOrigin + "_MATCH"] +
        ")"
)


def exclude_false_positives(swap_df):
    """
    Excludes specific library pair swaps defined in an external file.

    Current workflow setup prevents this from being done by Shesmu.

    Args:
        swap_df: The swaps called by Dashi

    Returns: The input table minus the library pairs in the file

    """
    excl_file = os.getenv("EXCLUDE_SWAP_LIBS")
    if excl_file is None:
        return swap_df

    if not os.path.isfile(excl_file):
        logger.warning("False positive swap file does not exist")
        return swap_df

    false_pos = pandas.read_csv(excl_file, sep="\t", comment="#")
    # Merge will preserve all rows of swap_df. If a row is a false positive, it will
    # have non-NA values in the false_pol columns
    matches = swap_df.merge(
        false_pos,
        how="left",
        left_on=[COL.QueryLibrary, COL.MatchLibrary],
        right_on=["LEFT_LIBRARY", "RIGHT_LIBRARY"],
    )
    true_pos = matches["JIRA_ISSUE"].isna()
    return swap_df[list(true_pos)].copy()


def filter_for_swaps(df):
    """
    Filter for rows that are swaps

    Args:
        df: The DataFrame must have the been annotated by the `closest_lib` function

    Returns:

    """
    # Libraries from patients with more than one library
    # Check for both positive and negative LOD values
    multi_lib = df[df[special_cols["closest_libraries_count"]] > 1]
    multi_lib = multi_lib[multi_lib[COL.LODScore].abs() > AMBIGUOUS_ZONE]

    # Libraries from patients with only one library
    # Negative LOD scores are expected, so only check for positive ones
    single_lib = df[df[special_cols["closest_libraries_count"]] == 0]
    single_lib = single_lib[single_lib[COL.LODScore] > AMBIGUOUS_ZONE]

    swaps = pandas.concat([multi_lib, single_lib])
    swaps = exclude_false_positives(swaps)

    return swaps


DATA_COLUMN = [
    PINERY_COL.StudyTitle,
    COL.QueryLibrary,
    COL.MatchLibrary,
    COL.LODScore,
    special_cols["latest_run"],
    special_cols["closest_libraries"],
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

    if d["id"] in rename_columns:
        d["name"] = rename_columns[d["id"]]


# Pair-wise comparison is done within project (for now), so left project is sufficient
ALL_PROJECTS = df_manipulation.unique_set(swap,PINERY_COL.StudyTitle)

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
                        data=filter_for_swaps(swap).to_dict('records'),
                        sort_action="native",
                        sort_by=[{"column_id": "LATEST_RUN", "direction": "desc"}],
                        export_format="csv",
                        export_columns="all",
                        include_headers_on_copy_paste=True,
                        style_data={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_cell_conditional=[
                            {'if': {'column_id': special_cols["closest_libraries"]},
                             'width': "500px"},
                        ],
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
        [
            State(ids["projects-list"], "value"),
            State(ids["checkbox_show_swaps"], "value"),
        ]
    )
    def update_pressed(_click, projects, show_swap):
        if "swap" in show_swap:
            df = filter_for_swaps(swap)
        else:
            df = swap
        df = df[df[PINERY_COL.StudyTitle].isin(projects)]
        return df.to_dict('records')

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]
