from collections import defaultdict

import dash_html_components as html
from dash.dependencies import Input, Output, State
from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs_single_lane, cutoff_table_data_ius
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from gsiqcetl.column import BamQc4Column, FastqcColumn, HsMetricsColumn
import pinery
import logging

logger = logging.getLogger(__name__)

page_name = 'single-lane-tar'
title = "Single-Lane Targeted Sequencing"

ids = init_ids([
    # Buttons
    'jira-issue-with-runs-button',
    'general-jira-issue-button',
    'update-button-top',
    'update-button-bottom',
    'approve-run-button',
    'miso-request-body',
    'miso-button',

    # Alerts
    "alerts-unknown-run",

    # Sidebar controls
    'all-runs',
    'run-id-list',
    'all-instruments',
    'instruments-list',
    'all-projects',
    'projects-list',
    "all-references",
    "references-list",
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
    'insert-size-mean-cutoff',
    'passed-filter-clusters-cutoff',
    "date-range",

    # Graphs
    "graphs",

    # Data table
    'failed-samples',
    'data-table',
    'failed-count',
    'data-count'
])

BAMQC_COL = BamQc4Column
FASTQC_COL = FastqcColumn
HSMETRICS_COL = HsMetricsColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "Total Reads PassedFilter",
    "On Target Reads (%)": "On Target Reads (%)",
    "Unmapped Reads (%)": "Unmapped Reads (%)",
    "Non-Primary Reads (%)": "Non-Primary Reads (%)",
    "Coverage per Gb": "coverage per gb",
    # Column comes from `df_with_fastqc_data` call
    "Total Clusters (Passed Filter)": "Total Clusters"
}

initial = get_initial_single_lane_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = special_cols["Total Clusters (Passed Filter)"]
# Set initial values for graph cutoff lines
cutoff_pf_clusters_label = sidebar_utils.clusters_per_sample_cutoff_label
initial["cutoff_pf_clusters"] = 0.01
cutoff_insert_mean_label = sidebar_utils.insert_mean_cutoff_label
initial["cutoff_insert_mean"] = 150


def get_bamqc_data():
    bamqc_df = util.get_dnaseqqc_and_bamqc4()
    bamqc_df = util.df_with_fastqc_data(bamqc_df, [BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes])

    hsmetrics_df = util.get_hsmetrics_merged()
    hsmetrics_df = util.filter_by_library_design(hsmetrics_df, util.ex_lib_designs, HSMETRICS_COL.LibraryDesign)

    bamqc_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc_df[FASTQC_COL.TotalSequences] / 1e6, 3)
    bamqc_df[special_cols["Total Clusters (Passed Filter)"]] = round(
        bamqc_df[special_cols["Total Clusters (Passed Filter)"]] / 1e6, 3)
    bamqc_df[special_cols["Unmapped Reads (%)"]] = round(
        bamqc_df[BAMQC_COL.UnmappedReadsMeta] * 100.0 /
        bamqc_df[BAMQC_COL.TotalInputReadsMeta], 3)
    bamqc_df[special_cols["Non-Primary Reads (%)"]] = round(
        bamqc_df[BAMQC_COL.NonPrimaryReadsMeta] * 100.0 /
        bamqc_df[BAMQC_COL.TotalInputReadsMeta], 3)
    hsmetrics_df[special_cols["On Target Reads (%)"]] = hsmetrics_df[HSMETRICS_COL.PctSelectedBases] * 100.0
    bamqc_df[special_cols["Coverage per Gb"]] = round(
        bamqc_df[BAMQC_COL.CoverageDeduplicated] / (
                bamqc_df[FASTQC_COL.TotalSequences] *
                bamqc_df[BAMQC_COL.AverageReadLength] / 1e9)
        , 3)

    pinery_samples = util.get_pinery_samples()

    bamqc_df = util.df_with_pinery_samples_ius(bamqc_df, pinery_samples, util.bamqc4_ius_columns)

    bamqc_df = util.df_with_run_info(bamqc_df, PINERY_COL.SequencerRunName)

    bamqc_df = util.filter_by_library_design(bamqc_df, util.ex_lib_designs)

    return bamqc_df, util.cache.versions(["bamqc4"])


(bamqc, DATAVERSION) = get_bamqc_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(bamqc, PINERY_COL.StudyTitle)
ALL_RUNS = util.unique_set(bamqc, PINERY_COL.SequencerRunName, True)  # reverse order
ALL_KITS = util.unique_set(bamqc, PINERY_COL.PrepKit)
ALL_TISSUE_MATERIALS = util.unique_set(bamqc, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(bamqc, PINERY_COL.TissueOrigin)
ALL_LIBRARY_DESIGNS = util.unique_set(bamqc, PINERY_COL.LibrarySourceTemplateType)
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(bamqc)
ALL_SAMPLE_TYPES = util.unique_set(bamqc, util.sample_type_col)
ALL_REFERENCES = util.unique_set(bamqc, BAMQC_COL.Reference)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
    "references": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_REFERENCES, "all_references"),
}

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
]
most_bamqc_cols = [*BAMQC_COL.values()]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.ExternalName,
    PINERY_COL.GroupID, PINERY_COL.TissueOrigin, PINERY_COL.TissueType,
    PINERY_COL.TargetedResequencing, PINERY_COL.Institute,
    INSTRUMENT_COLS.ModelName
]
ex_table_columns = [
    *first_col_set, *most_bamqc_cols, *special_cols.values(), *later_col_set
]

shape_colour = ColourShapeSingleLane(
    ALL_PROJECTS, ALL_RUNS, ALL_KITS, ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN,
    ALL_LIBRARY_DESIGNS, ALL_REFERENCES,
)
# Add shape, colour, and size cols to dataframe 
bamqc = add_graphable_cols(bamqc, initial, shape_colour.items_for_df())

SORT_BY = sidebar_utils.default_first_sort + [
    {"label": "Total Clusters",
     "value": special_cols["Total Clusters (Passed Filter)"]},
    {"label": "Unmapped Reads",
     "value": special_cols["Unmapped Reads (%)"]},
    {"label": "Non-primary Reads",
     "value": special_cols["Non-Primary Reads (%)"]},
    {"label": "On Target Reads",
     "value": special_cols["On Target Reads (%)"]},
    {"label": "Mean Insert Size",
     "value": BAMQC_COL.InsertMean},
    {"label": "Sample Name",
     "value": PINERY_COL.SampleName},
    {"label": "Run Start Date",
     "value": RUN_COLS.StartDate},
    {"label": "Run End Date",
     "value": RUN_COLS.CompletionDate},
]


def generate_total_clusters(df, graph_params):
    return SingleLaneSubplot(
        "Total Clusters (Passed Filter)",
        df,
        lambda d: d[special_cols["Total Clusters (Passed Filter)"]],
        "# PF Clusters X 10^6",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_pf_clusters_label, graph_params["cutoff_pf_clusters"])]
    )


def generate_deduplicated_coverage(df, graph_params):
    return SingleLaneSubplot(
        "Mean Coverage (Deduplicated)",
        df,
        lambda d: d[BAMQC_COL.CoverageDeduplicated],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_deduplicated_coverage_per_gb(df, graph_params):
    return SingleLaneSubplot(
        "Mean Coverage per Gb (Deduplicated)",
        df,
        lambda d: d[special_cols["Coverage per Gb"]],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"], )


def generate_unmapped_reads(current_data, graph_params):
    return SingleLaneSubplot(
        "Unmapped Reads (%)",
        current_data,
        lambda d: d[special_cols["Unmapped Reads (%)"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_nonprimary_reads(current_data, graph_params):
    return SingleLaneSubplot(
        "Non-Primary Reads (%)",
        current_data,
        lambda d: d[special_cols["Non-Primary Reads (%)"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_on_target_reads(current_data, graph_params):
    return SingleLaneSubplot(
        "On Target Reads (%)",
        current_data,
        lambda d: d[special_cols["On Target Reads (%)"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_mean_insert_size(current_data, graph_params):
    return SingleLaneSubplot(
        "Mean Insert Size",
        current_data,
        lambda d: d[BAMQC_COL.InsertMean],
        "Base Pairs",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_insert_mean_label, graph_params["cutoff_insert_mean"])],
    )


GRAPHS = [
    generate_total_clusters,
    generate_deduplicated_coverage,
    generate_deduplicated_coverage_per_gb,
    generate_unmapped_reads,
    generate_nonprimary_reads,
    generate_on_target_reads,
    generate_mean_insert_size,
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

    df = reshape_single_lane_df(bamqc, initial["runs"], initial["instruments"],
                                initial["projects"], initial["references"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className='body', children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("Open an issue",
                                          ids['general-jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title)),
                sidebar_utils.jira_button("Open an issue about these runs",
                                          ids['jira-issue-with-runs-button'],
                                          {"display": "none"}, ""),
                sidebar_utils.unknown_run_alert(
                    ids['alerts-unknown-run'],
                    initial["runs"],
                    ALL_RUNS
                ),
            ]),
            html.Div(className='row flex-container', children=[
                html.Div(className='sidebar four columns', children=[
                    html.Button('Update', id=ids['update-button-top'], className="update-button"),
                    sidebar_utils.miso_qc_button(ids["miso-request-body"], ids["miso-button"]),
                    sidebar_utils.approve_run_button(ids['approve-run-button']),
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

                    sidebar_utils.select_reference(ids["all-references"],
                                                   ids["references-list"],
                                                   ALL_REFERENCES),

                    sidebar_utils.select_kits(ids["all-kits"], ids["kits-list"],
                                              ALL_KITS),

                    sidebar_utils.select_instruments(ids["all-instruments"],
                                                     ids["instruments-list"],
                                                     ILLUMINA_INSTRUMENT_MODELS),

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
                                                   shape_colour.dropdown(),
                                                   initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids['shape-by'],
                                                  shape_colour.dropdown(),
                                                  initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                          []),

                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(
                        ids['search-sample-ext'],
                        None),

                    sidebar_utils.show_data_labels_input_single_lane(ids['show-data-labels'],
                                                                     initial["shownames_val"],
                                                                     'ALL LABELS',
                                                                     ids['show-all-data-labels']),

                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input(cutoff_pf_clusters_label,
                                               ids['passed-filter-clusters-cutoff'], initial["cutoff_pf_clusters"]),
                    sidebar_utils.cutoff_input(cutoff_insert_mean_label,
                                               ids['insert-size-mean-cutoff'], initial["cutoff_insert_mean"]),

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
                                 # Tables tab
                                 core.Tab(label="Tables",
                                          children=[
                                              table_tabs_single_lane(
                                                  ids["failed-samples"],
                                                  ids["data-table"],
                                                  ids["failed-count"],
                                                  ids["data-count"],
                                                  df,
                                                  ex_table_columns,
                                                  [
                                                      (cutoff_insert_mean_label, BAMQC_COL.InsertMean, initial["cutoff_insert_mean"],
                                                       (lambda row, col, cutoff: row[col] < cutoff)),
                                                      (cutoff_pf_clusters_label,
                                                       special_cols["Total Clusters (Passed Filter)"], initial["cutoff_pf_clusters"],
                                                       (lambda row, col, cutoff: row[col] < cutoff)),
                                                  ]
                                              ),
                                          ])
                             ])  # End Tabs
                         ])  # End Div
            ])  # End Div
        ])  # End Div
    ])  # End Loading


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["approve-run-button"], "href"),
            Output(ids["approve-run-button"], "style"),
            Output(ids['graphs'], 'figure'),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids['data-table'], 'data'),
            Output(ids['failed-count'], "children"),
            Output(ids['data-count'], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids["search-sample-ext"], "options"),
            Output(ids["jira-issue-with-runs-button"], "href"),
            Output(ids["jira-issue-with-runs-button"], "style"),
            Output(ids["miso-request-body"], "value"),
            Output(ids["miso-button"], "style")
        ],
        [Input(ids['update-button-top'], 'n_clicks'),
         Input(ids['update-button-bottom'], 'n_clicks')],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['instruments-list'], 'value'),
            State(ids['projects-list'], 'value'),
            State(ids['references-list'], 'value'),
            State(ids['kits-list'], 'value'),
            State(ids['library-designs-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['search-sample'], 'value'),
            State(ids['search-sample-ext'], 'value'),
            State(ids['show-data-labels'], 'value'),
            State(ids['insert-size-mean-cutoff'], 'value'),
            State(ids['passed-filter-clusters-cutoff'], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date'),
            State('url', 'search'),
        ]
    )
    def update_pressed(click,
                       click2,
                       runs,
                       instruments,
                       projects,
                       references,
                       kits,
                       library_designs,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       searchsample,
                       searchsampleext,
                       show_names,
                       insert_mean_cutoff,
                       total_clusters_cutoff,
                       start_date,
                       end_date,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if searchsample and searchsampleext:
            searchsample += searchsampleext
        elif not searchsample and searchsampleext:
            searchsample = searchsampleext
        df = reshape_single_lane_df(bamqc, runs, instruments, projects, references, kits, library_designs,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        (approve_run_href, approve_run_style) = sidebar_utils.approve_run_url(runs)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_pf_clusters": total_clusters_cutoff,
            "cutoff_insert_mean": insert_mean_cutoff
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_ius(df, [
            (cutoff_insert_mean_label, BAMQC_COL.InsertMean, insert_mean_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_pf_clusters_label, special_cols["Total Clusters (Passed "
                                                    "Filter)"], total_clusters_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
        ])
        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        (jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)

        (miso_request, miso_button_style) = util.build_miso_info(df, title,
                                                                 [{
                                                                     'title': 'Mean Insert Size',
                                                                     'threshold_type': 'ge',
                                                                     'threshold': insert_mean_cutoff,
                                                                     'value': BAMQC_COL.InsertMean
                                                                 }, {
                                                                     'title': 'Clusters per Sample (* 10^6)',
                                                                     'threshold_type': 'ge',
                                                                     'threshold': total_clusters_cutoff,
                                                                     'value': special_cols[
                                                                         "Total Clusters (Passed Filter)"]
                                                                 }]
                                                                 )

        return [
            approve_run_href,
            approve_run_style,
            generate_subplot_from_func(df, graph_params, GRAPHS),
            failure_columns,
            failure_df.to_dict('records'),
            df.to_dict('records', into=dd),
            "Rows: {0}".format(len(failure_df.index)),
            "Rows: {0}".format(len(df.index)),
            [{'label': x, 'value': x} for x in new_search_sample],
            [{'label': d[PINERY_COL.ExternalName], 'value': d[PINERY_COL.SampleName]} for i, d in df[[PINERY_COL.ExternalName, PINERY_COL.SampleName]].iterrows()],
            jira_href,
            jira_style,
            miso_request,
            miso_button_style
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
        return [x for x in ILLUMINA_INSTRUMENT_MODELS]

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]

    @dash_app.callback(
        Output(ids['references-list'], 'value'),
        [Input(ids['all-references'], 'n_clicks')]
    )
    def all_references_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_REFERENCES]

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
