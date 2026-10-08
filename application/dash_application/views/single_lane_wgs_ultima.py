from dash import html
from dash.dependencies import Input, Output, State
from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import build_table
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from qcetl.column import UltimaLibraryMetricsColumn
import pinery
import logging
logger = logging.getLogger(__name__)

page_name = 'single-lane-ultima'
title = "Single-Lane Ultima"

ids = init_ids([
    # Buttons
    'update-button-top',
    'update-button-bottom',

    # Alerts
    "alerts-unknown-run",

    # Sidebar controls
    'all-runs',
    'run-id-list',
    'all-instruments',
    'instruments-list',
    'all-projects',
    'projects-list',
    'all-kits',
    'kits-list',
    'all-library-designs',
    'library-designs-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'search-sample-ext',
    'show-data-labels',
    'show-all-data-labels',
    "date-range",
    "percent-duplication-cutoff",

    #Graphs
    "graphs",

    #Data table
    'all-samples',
    'all-count',
])

ULTIMA_COL = UltimaLibraryMetricsColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

initial = get_initial_single_lane_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = ULTIMA_COL.MeanCoverage

# Set initial values for graph cutoff lines
cutoff_percent_duplication_label = sidebar_utils.percent_duplication_cutoff_label
initial["cutoff_percent_duplication"] = 50


def get_ultima_data():
    ultima_df = util.get_ultima_library_metrics()

    pinery_samples = util.get_pinery_samples()

    ultima_df = util.df_with_pinery_samples_lims_id(ultima_df, pinery_samples, ULTIMA_COL.PineryLimsID)

    ultima_df = util.df_with_run_info(ultima_df, PINERY_COL.SequencerRunName)

    return ultima_df, util.cache.versions(["ultimalibrarymetrics"])


(ultima, DATAVERSION) = get_ultima_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(ultima, PINERY_COL.StudyTitle)
ALL_RUNS = util.unique_set(ultima, PINERY_COL.SequencerRunName, True) # reverse order
ALL_KITS = util.unique_set(ultima, PINERY_COL.PrepKit)
ALL_TISSUE_MATERIALS = util.unique_set(ultima, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(ultima, PINERY_COL.TissueOrigin)
ALL_LIBRARY_DESIGNS = util.unique_set(ultima, PINERY_COL.LibrarySourceTemplateType)
ULTIMA_INSTRUMENT_MODELS = util.get_illumina_instruments(ultima)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ULTIMA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
}

ultima_curated_columns = [
    PINERY_COL.SampleName,
    PINERY_COL.IUSTag,
    PINERY_COL.SequencerRunName,
    PINERY_COL.TissueType,
    PINERY_COL.LibrarySourceTemplateType,
    PINERY_COL.StudyTitle,
    PINERY_COL.ExternalName,
    PINERY_COL.GroupID,
    PINERY_COL.PrepKit,
    PINERY_COL.TissuePreparation,
    PINERY_COL.UMIs,
    INSTRUMENT_COLS.ModelName,
    util.sample_type_col,
    ULTIMA_COL.Barcode,
    ULTIMA_COL.PineryLimsID,
    ULTIMA_COL.MeanCoverage,
    ULTIMA_COL.PercentDuplicates,
    ULTIMA_COL.MeanReadLength,
    ULTIMA_COL.PFBarcodeReads,
]

shape_colour = ColourShapeSingleLane(
    ALL_PROJECTS, ALL_RUNS, ALL_KITS, ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN,
    ALL_LIBRARY_DESIGNS, [],
)
# Reference isn't available, so it can't be used for colour or shape
SHAPE_COLOUR_DROPDOWN = [x for x in shape_colour.dropdown() if x["value"] != COMMON_COL.Reference]
# Add shape, colour, and size cols to dataframe
ultima = add_graphable_cols(ultima, initial, shape_colour.items_for_df())

SORT_BY = sidebar_utils.default_first_sort + [
    {"label": "Mean Coverage (Deduplicated)",
     "value": ULTIMA_COL.MeanCoverage},
    {"label": "Duplication",
     "value": ULTIMA_COL.PercentDuplicates},
    {"label": "Mean Read Length",
     "value": ULTIMA_COL.MeanReadLength},
    {"label": "PF Barcode Reads",
     "value": ULTIMA_COL.PFBarcodeReads},
    {"label": "Sample Name",
     "value": PINERY_COL.SampleName},
    {"label": "Run Start Date",
     "value": RUN_COLS.StartDate},
    {"label": "Run End Date",
     "value": RUN_COLS.CompletionDate},
]


def generate_deduplicated_coverage(current_data, graph_params):
    return SingleLaneSubplot(
        "Mean Coverage (Deduplicated)",
        current_data,
        lambda d: d[ULTIMA_COL.MeanCoverage],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_duplication(current_data, graph_params):
    return SingleLaneSubplot(
        "Duplication (%)",
        current_data,
        lambda d: d[ULTIMA_COL.PercentDuplicates],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_percent_duplication_label, graph_params["cutoff_percent_duplication"])],
    )


def generate_mean_read_length(current_data, graph_params):
    return SingleLaneSubplot(
        "Mean Read Length",
        current_data,
        lambda d: d[ULTIMA_COL.MeanReadLength],
        "Base Pairs",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_pf_barcode_reads(current_data, graph_params):
    return SingleLaneSubplot(
        "Barcode Reads (Passed Filter)",
        current_data,
        lambda d: d[ULTIMA_COL.PFBarcodeReads],
        "Reads",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


GRAPHS = [
    generate_deduplicated_coverage,
    generate_duplication,
    generate_mean_read_length,
    generate_pf_barcode_reads,
]

def dataversion():
    return DATAVERSION


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # initial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]

    df = reshape_single_lane_df(ultima, initial["runs"], initial["instruments"],
                                initial["projects"], initial["references"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className='body', children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.unknown_run_alert(
                    ids['alerts-unknown-run'],
                    initial["runs"],
                    ALL_RUNS
                ),
            ]),
            html.Div(className='row flex-container', children=[
                html.Div(className='sidebar four columns', children=[
                    html.Button('Update', id=ids['update-button-top'], className="update-button"),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_runs(ids["all-runs"],
                                              ids["run-id-list"], ALL_RUNS,
                                              query["req_runs"]),

                    sidebar_utils.run_range_input(ids["date-range"],
                                                  query["req_start"],
                                                  query["req_end"]),

                    sidebar_utils.hr(),

                    sidebar_utils.select_projects(ids["all-projects"],
                                                  ids["projects-list"],
                                                  ALL_PROJECTS,
                                                  query["req_projects"]),

                    sidebar_utils.select_kits(ids["all-kits"], ids["kits-list"],
                                              ALL_KITS),

                    sidebar_utils.select_instruments(ids["all-instruments"],
                                                     ids["instruments-list"],
                                                     ULTIMA_INSTRUMENT_MODELS),

                    sidebar_utils.select_library_designs(
                        ids["all-library-designs"], ids["library-designs-list"],
                        ALL_LIBRARY_DESIGNS),

                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(
                        ids['first-sort'],
                        initial["first_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_second_sort(
                        ids['second-sort'],
                        initial["second_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_colour_by(ids['colour-by'],
                                                   SHAPE_COLOUR_DROPDOWN,
                                                   initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids['shape-by'],
                                                  SHAPE_COLOUR_DROPDOWN,
                                                  initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                          []),

                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(ids['search-sample-ext'],
                                                                                  None),

                    sidebar_utils.show_data_labels_input_single_lane(ids['show-data-labels'],
                                                                     initial["shownames_val"],
                                                                     'ALL LABELS',
                                                                     ids['show-all-data-labels']),

                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input(cutoff_percent_duplication_label,
                                               ids["percent-duplication-cutoff"],
                                               initial["cutoff_percent_duplication"]),

                    html.Br(),
                    html.Button('Update', id=ids['update-button-bottom'], className="update-button"),
                ]),

                # Graphs + Tables tabs
                html.Div(className="seven columns",
                         children=[
                             core.Tabs([
                                 # Graphs tab
                                 core.Tab(label="Graphs",
                                          children=[
                                              create_graph_element_with_subplots(ids["graphs"], df, initial, GRAPHS),
                                          ]),
                                 # Data tab
                                 core.Tab(label="Data",
                                          children=[
                                              html.Div(className='data-table',
                                                       children=[
                                                           build_table(ids['all-samples'], ultima_curated_columns, df),
                                                       ]),
                                              html.Br(),
                                              html.P(id=ids['all-count'], children=["Rows: {0}".format(len(df.index))]),
                                          ])
                             ]) # End Tabs
                         ]) # End Div
            ]) # End Div
        ]) # End Div
    ]) # End Loading


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids['graphs'], 'figure'),
            Output(ids['all-samples'], "data"),
            Output(ids['all-count'], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids["search-sample-ext"], "options"),
        ],
        [Input(ids['update-button-top'], 'n_clicks'),
         Input(ids['update-button-bottom'], 'n_clicks')],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['instruments-list'], 'value'),
            State(ids['projects-list'], 'value'),
            State(ids['kits-list'], 'value'),
            State(ids['library-designs-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['search-sample'], 'value'),
            State(ids['search-sample-ext'], 'value'),
            State(ids['show-data-labels'], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date'),
            State(ids["percent-duplication-cutoff"], 'value'),
            State('url', 'search'),
        ]
    )
    def update_pressed(click,
                       click2,
                       runs,
                       instruments,
                       projects,
                       kits,
                       library_designs,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       searchsample,
                       searchsampleext,
                       show_names,
                       start_date,
                       end_date,
                       percent_duplication_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if searchsample and searchsampleext:
            searchsample += searchsampleext
        elif not searchsample and searchsampleext:
            searchsample = searchsampleext
        df = reshape_single_lane_df(ultima, runs, instruments, projects, [], kits, library_designs,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_percent_duplication": percent_duplication_cutoff,
        }

        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        return [
            generate_subplot_from_func(df, graph_params, GRAPHS),
            df[ultima_curated_columns].to_dict('records'),
            "Rows: {0}".format(len(df.index)),
            [{'label': x, 'value': x} for x in new_search_sample],
            [{'label': d[PINERY_COL.ExternalName], 'value': d[PINERY_COL.SampleName]} for i, d in df[[PINERY_COL.ExternalName, PINERY_COL.SampleName]].iterrows()],
        ]

    @dash_app.callback(
        Output(ids['run-id-list'], 'value'),
        [Input(ids['all-runs'], 'n_clicks')]
    )
    def all_runs_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_RUNS]

    @dash_app.callback(
        Output(ids['instruments-list'], 'value'),
        [Input(ids['all-instruments'], 'n_clicks')]
    )
    def all_instruments_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ULTIMA_INSTRUMENT_MODELS]

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]

    @dash_app.callback(
        Output(ids['kits-list'], 'value'),
        [Input(ids['all-kits'], 'n_clicks')]
    )
    def all_kits_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_KITS]

    @dash_app.callback(
        Output(ids['library-designs-list'], 'value'),
        [Input(ids['all-library-designs'], 'n_clicks')]
    )
    def all_library_designs_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_LIBRARY_DESIGNS]

    @dash_app.callback(
        Output(ids['show-data-labels'], 'value'),
        [Input(ids['show-all-data-labels'], 'n_clicks')],
        [State(ids['show-data-labels'], 'options')]
    )
    def all_data_labels_requested(click, avail_options):
        sidebar_utils.update_only_if_clicked(click)
        return [x['value'] for x in avail_options]
