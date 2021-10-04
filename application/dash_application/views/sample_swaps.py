import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import dash_table.Format
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

# Get the latest run of the pair for sorting purposes and make format YYYY-MM-DD
swap[special_cols["latest_run"]] = swap[
    [RUN_COLS.StartDate, RUN_COLS.StartDate + "_RIGHT"]
].max(1).dt.date
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
    # There must be at least two libraries for swap comparison
    if len(input_df) < 2:
        return pandas.DataFrame(columns=list(input_df) + [
            special_cols["closest_libraries_count"], special_cols["closest_libraries"]
        ])
    # Index will be used with `iloc` call, so has to go from 0 to number of rows
    lib_df = input_df.reset_index(drop=True)
    # The closest library
    return_df = lib_df.head(1).copy()
    # Libraries that came from the same patient
    same_ident_df = lib_df[lib_df[special_cols["same_identity"]]]
    # Patient has only one library sequenced
    # Get the next closest library (should not match, as it is from different patient)
    if same_ident_df.empty:
        closest_other_patient = lib_df.iloc[1]
        # As there are no expected close libraries, this is always 0
        return_df[special_cols["closest_libraries_count"]] = 0
        return_df[special_cols["closest_libraries"]] = (
            closest_other_patient["RIGHT_LIBRARY"] +
            " (" +
            closest_other_patient[COL.LODScore].round().astype(int).astype(str) +
            ")"
        )
        return return_df

    # Get libraries up to and including the first that came from the same patient
    closest_df = lib_df.iloc[:same_ident_df.index[0] + 1]
    return_df[special_cols["closest_libraries_count"]] = len(closest_df)
    closest_lib = (
            closest_df["RIGHT_LIBRARY"] +
            " (" +
            closest_df[COL.LODScore].round().astype(int).astype(str) +
            ")"
    )
    return_df[special_cols["closest_libraries"]] = ", ".join(closest_lib)
    return return_df


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
        left_on=["LEFT_LIBRARY", "RIGHT_LIBRARY"],
        right_on=["LEFT_LIBRARY", "RIGHT_LIBRARY"],
    )
    true_pos = matches["JIRA_ISSUE"].isna()
    return swap_df[list(true_pos)].copy()

result = []
# Two for loops (blah) go through each swap workflow and then check each library
# Will try to vectorize this if this approach proves superior to previous hard LOD cutoff
for _, top in swap.groupby(COL.FileSWID):
    top = top.sort_values([COL.LibraryLeft, COL.LODScore], ascending=False)
    for _, d in top.groupby(COL.LibraryLeft):
        result.append(closest_lib(d))

swap = pandas.concat(result)

# Libraries from patients with more than one library
# Check for both positive and negative LOD values
multi_lib = swap[swap[special_cols["closest_libraries_count"]] > 1]
multi_lib = multi_lib[multi_lib[COL.LODScore].abs() > AMBIGUOUS_ZONE]

# Libraries from patients with only one library
# Negative LOD scores are expected, so only check for positive ones
single_lib = swap[swap[special_cols["closest_libraries_count"]] == 0]
single_lib = single_lib[single_lib[COL.LODScore] > AMBIGUOUS_ZONE]

swap = pandas.concat([multi_lib, single_lib])
swap = exclude_false_positives(swap)

DATA_COLUMN = [
    COL.LibraryLeft,
    COL.LibraryRight,
    COL.LODScore,
    special_cols["latest_run"],
    special_cols["closest_libraries"],
    PINERY_COL.ParentSampleName,
    PINERY_COL.ParentSampleName + "_RIGHT",
]

# These columns will be in the downloaded csv, but not displayed by default in Dashi
DOWNLOAD_ONLY_COLUMNS = [
    PINERY_COL.ParentSampleName,
    PINERY_COL.ParentSampleName + "_RIGHT",
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
                ]),
                html.Div(className="seven columns", children=[
                    dash_table.DataTable(
                        id=ids['table'],
                        columns=TABLE_COLUMNS,
                        hidden_columns=DOWNLOAD_ONLY_COLUMNS,
                        data=swap.to_dict('records'),
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
