from collections import defaultdict

import dash_html_components as html
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs_single_lane, cutoff_table_data_ius
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from gsiqcetl.column import FastqcColumn
import logging

logger = logging.getLogger(__name__)

""" Set up elements needed for page """
page_name = "single-lane-wgs"
title = "Single-Lane WGS"

ids = init_ids([
    # Buttons
    "jira-issue-with-runs-button",
    "general-jira-issue-button",
    "update-button-top",
    "update-button-bottom",
    "approve-run-button",
    "miso-request-body",
    "miso-button",

    # Alerts
    "alerts-unknown-run",

    # Sidebar controls
    "all-runs",
    "run-id-list",
    "all-instruments",
    "instruments-list",
    "all-library-designs",
    "library-designs-list",
    "all-projects",
    "projects-list",
    "all-references",
    "references-list",
    "all-kits",
    "kits-list",
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "search-sample",
    "search-sample-ext",
    "insert-median-cutoff",
    "percent-duplication-cutoff",
    "clusters-per-sample-cutoff",
    "date-range",
    "show-data-labels",
    "show-all-data-labels",

    # Graphs
    "graphs",

    "failed-samples",
    "data-table",
    "failed-count",
    "data-count",
])

BAMQC_COL = gsiqcetl.column.BamQc4Column
FASTQC_COL = FastqcColumn
ICHOR_COL = gsiqcetl.column.IchorCnaColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "total reads passed filter",
    "Unmapped Reads": "percent unmapped reads",
    "Non-Primary Reads": "percent non-primary reads",
    "On-target Reads": "percent on-target reads",
    "Purity": "percent purity",
    "Coverage per Gb": "coverage per gb",
    # Column comes from `df_with_fastqc_data` call
    "Total Clusters (Passed Filter)": "Total Clusters",
}

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
    special_cols["Total Reads (Passed Filter)"],
    special_cols["Total Clusters (Passed Filter)"],
    special_cols["Unmapped Reads"],
    special_cols["Non-Primary Reads"],
    special_cols["On-target Reads"],
    special_cols["Purity"],
    special_cols["Coverage per Gb"]
]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.ExternalName,
    PINERY_COL.GroupID, PINERY_COL.TissueOrigin, PINERY_COL.TissueType,
    PINERY_COL.Institute, INSTRUMENT_COLS.ModelName
]
wgs_table_columns = [*first_col_set, *BAMQC_COL.values(), *ICHOR_COL.values(), *later_col_set]

initial = get_initial_single_lane_values()
# Set additional initial values for dropdown menus
initial["second_sort"] = special_cols["Total Clusters (Passed Filter)"]
# Set initial values for graph cutoff lines
# Sourced from https://docs.google.com/document/d/1L056bikfIJDeX6Qzo6fwBb9j7A5NgC6o/edit
cutoff_insert_median_label = sidebar_utils.insert_median_cutoff_label
initial["cutoff_insert_median"] = 150
cutoff_percent_duplication_label = sidebar_utils.percent_duplication_cutoff_label
initial["cutoff_percent_duplication"] = 50
cutoff_clusters_per_sample_label = sidebar_utils.clusters_per_sample_cutoff_label
# This is 10 000, but the stat is / 10^6
initial["cutoff_clusters_per_sample"] = 0.01


def get_wgs_data():
    """
    Join together all the dataframes needed for graphing:
      * BamQC (where most of the graphed QC data comes from)
      * ichorCNA (where the remainder of the graphed QC data comes from)
      * Pinery (sample information)
      * Instruments (to allow filtering by instrument model)
      * Runs (needed to join Pinery to Instruments)
    """
    # Pull in sample metadata from Pinery.
    pinery_samples = util.get_pinery_samples()
    # Filter the Pinery samples for WG samples and others which will have BAM files generated.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   util.wgs_lib_designs)

    ichorcna_df = util.get_ichorcna()
    ichorcna_df = ichorcna_df[[ICHOR_COL.Run,
                               ICHOR_COL.Lane,
                               ICHOR_COL.Barcodes,
                               ICHOR_COL.Ploidy,
                               ICHOR_COL.TumorFraction]]

    bamqc_df = util.get_bamqc3_and_4()
    bamqc_df = util.df_with_fastqc_data(bamqc_df, [BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes])

    bamqc_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc_df[FASTQC_COL.TotalSequences] / 1e6, 3)
    bamqc_df[special_cols["Total Clusters (Passed Filter)"]] = round(
        bamqc_df[special_cols["Total Clusters (Passed Filter)"]] / 1e6, 3)
    bamqc_df[special_cols["Unmapped Reads"]] = round(
        bamqc_df[BAMQC_COL.UnmappedReadsMeta] * 100.0 /
        bamqc_df[BAMQC_COL.TotalInputReadsMeta], 3)
    bamqc_df[special_cols["Non-Primary Reads"]] = round(
        bamqc_df[BAMQC_COL.NonPrimaryReadsMeta] * 100.0 /
        bamqc_df[BAMQC_COL.TotalInputReadsMeta], 3)
    bamqc_df[special_cols["On-target Reads"]] = round(
        bamqc_df[BAMQC_COL.ReadsOnTarget] * 100.0 /
        bamqc_df[BAMQC_COL.TotalReads], 3)
    bamqc_df[special_cols["Coverage per Gb"]] = round(
        bamqc_df[BAMQC_COL.CoverageDeduplicated] / (
                bamqc_df[FASTQC_COL.TotalSequences] *
                bamqc_df[BAMQC_COL.AverageReadLength] / 1e9)
        , 3)
    ichorcna_df[special_cols["Purity"]] = round(
        ichorcna_df[ICHOR_COL.TumorFraction] * 100.0, 3)

    # Join ichorCNA and BamQC data
    wgs_df = bamqc_df.merge(
        ichorcna_df, how="outer",
        left_on=util.bamqc4_ius_columns,
        right_on=util.ichorcna_ius_columns,
        suffixes=['', '_ichorcn']
    )

    # Join BamQC+ichorCNA and Pinery data
    wgs_df = util.df_with_pinery_samples_ius(wgs_df, pinery_samples,
                                         util.bamqc4_ius_columns)

    # Join df and instrument model
    wgs_df = util.df_with_run_info(wgs_df, PINERY_COL.SequencerRunName)

    # Filter the dataframe to only include Illumina data
    illumina_models = util.get_illumina_instruments(wgs_df)
    wgs_df = wgs_df[wgs_df[INSTRUMENT_COLS.ModelName].isin(illumina_models)]

    return wgs_df, util.cache.versions(["bamqc4", "ichorcna"])


# Make the WGS dataframe
(WGS_DF, DATAVERSION) = get_wgs_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(WGS_DF,PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(WGS_DF, PINERY_COL.PrepKit)
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(WGS_DF)
ALL_TISSUE_MATERIALS = util.unique_set(WGS_DF, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(WGS_DF, PINERY_COL.TissueOrigin)
ALL_LIBRARY_DESIGNS = util.unique_set(WGS_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_RUNS = util.unique_set(WGS_DF, PINERY_COL.SequencerRunName, True)# reverse the list
ALL_SAMPLE_TYPES = util.unique_set(WGS_DF, util.sample_type_col)
ALL_REFERENCES = util.unique_set(WGS_DF, BAMQC_COL.Reference)

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

shape_colour = ColourShapeSingleLane(
    ALL_PROJECTS, ALL_RUNS, ALL_KITS, ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN,
    ALL_LIBRARY_DESIGNS, ALL_REFERENCES,
)

# Add shape col to WG dataframe
WGS_DF = add_graphable_cols(WGS_DF, initial, shape_colour.items_for_df())

SORT_BY = sidebar_utils.default_first_sort + [
    {"label": "Total Clusters",
     "value": special_cols["Total Clusters (Passed Filter)"]},
    {"label": "Duplication",
     "value": BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION},
    {"label": "Unmapped Reads",
     "value": special_cols["Unmapped Reads"]},
    {"label": "Non-Primary Reads",
     "value": special_cols["Non-Primary Reads"]},
    {"label": "On-target Reads",
     "value": special_cols["On-target Reads"]},
    {"label": "Purity",
     "value": special_cols["Purity"]},
    {"label": "Ploidy",
     "value": ICHOR_COL.Ploidy},
    {"label": "Median Insert Size",
     "value": BAMQC_COL.InsertMedian},
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
        cutoff_lines=[(cutoff_clusters_per_sample_label, graph_params["cutoff_clusters_per_sample"])],
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


def generate_median_insert_size(df, graph_params):
    return SingleLaneSubplot(
        "Median Insert Size with 10/90 Percentile",
        df,
        lambda d: d[BAMQC_COL.InsertMedian],
        "Base Pairs",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_insert_median_label, graph_params["cutoff_insert_median"])],
        bar_positive=BAMQC_COL.Insert90Percentile,
        bar_negative=BAMQC_COL.Insert10Percentile,
    )


def generate_duplication(df, graph_params):
    return SingleLaneSubplot(
        "Duplication (%)",
        df,
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_percent_duplication_label, graph_params["cutoff_percent_duplication"])],
    )


def generate_unmapped_reads(df, graph_params):
    return SingleLaneSubplot(
        "Unmapped Reads (%)",
        df,
        lambda d: d[special_cols["Unmapped Reads"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_non_primary(df, graph_params):
    return SingleLaneSubplot(
        "Non-Primary Reads (%)",
        df,
        lambda d: d[special_cols["Non-Primary Reads"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_on_target_reads(df, graph_params):
    return SingleLaneSubplot(
        "On Target Reads (%)",
        df,
        lambda d: d[special_cols["On-target Reads"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


GRAPHS = [
    generate_total_clusters,
    generate_deduplicated_coverage,
    generate_deduplicated_coverage_per_gb,
    generate_median_insert_size,
    generate_duplication,
    generate_unmapped_reads,
    generate_non_primary,
    generate_on_target_reads,
]


def dataversion():
    return DATAVERSION

# Layout elements
def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # intial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]

    df = reshape_single_lane_df(WGS_DF, initial["runs"], initial["instruments"],
                                initial["projects"], initial["references"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
    html.Div(className="body", children=[
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
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button-top'], className="update-button"),
                sidebar_utils.miso_qc_button(ids['miso-request-body'], ids['miso-button']),
                sidebar_utils.approve_run_button(ids["approve-run-button"]),

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
                    ids["second-sort"],
                    initial["second_sort"],
                    SORT_BY,
                ),

                sidebar_utils.select_colour_by(ids['colour-by'],
                                              shape_colour.dropdown(),
                                              initial["colour_by"]),

                sidebar_utils.select_shape_by(ids['shape-by'],
                                             shape_colour.dropdown(),
                                             initial["shape_by"]),

                sidebar_utils.highlight_samples_input(ids['search-sample'], []),

                sidebar_utils.highlight_samples_by_ext_name_input_single_lane(ids['search-sample-ext'],
                                                          None),

                sidebar_utils.show_data_labels_input_single_lane(ids["show-data-labels"],
                                                     initial["shownames_val"],
                                                     "ALL LABELS",
                                                     ids["show-all-data-labels"]),

                sidebar_utils.hr(),

                # Cutoffs
                sidebar_utils.cutoff_input(cutoff_insert_median_label,
                    ids["insert-median-cutoff"], initial["cutoff_insert_median"]),
                sidebar_utils.cutoff_input(cutoff_percent_duplication_label, 
                    ids["percent-duplication-cutoff"], initial["cutoff_percent_duplication"]),
                sidebar_utils.cutoff_input(cutoff_clusters_per_sample_label,
                    ids["clusters-per-sample-cutoff"], initial["cutoff_clusters_per_sample"]),

                html.Br(),
                html.Button("Update", id=ids['update-button-bottom'], className="update-button"),
            ]),

            	# Graphs + Tables tabs
                html.Div(className="seven columns", 
                children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(
                            label="Graphs",
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
                                wgs_table_columns,
                                [
                                    (cutoff_insert_median_label, BAMQC_COL.InsertMedian, initial["cutoff_insert_median"],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_percent_duplication_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION, initial["cutoff_percent_duplication"],
                                    (lambda row, col, cutoff: row[col] >= cutoff)),
                                    (cutoff_clusters_per_sample_label, special_cols["Total Clusters (Passed Filter)"], initial["cutoff_clusters_per_sample"],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                ]
                            )                    
                        ])
                    ]) # End Tabs
                ]) # End Div
            ]) # End Div
        ]) # End Div
    ]) # End Loading


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["approve-run-button"], "href"),
            Output(ids["approve-run-button"], "style"),
            Output(ids["graphs"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
            Output(ids["failed-count"], "children"),
            Output(ids["data-count"], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids["search-sample-ext"], "options"),
            Output(ids["jira-issue-with-runs-button"], "href"),
            Output(ids["jira-issue-with-runs-button"], "style"),
            Output(ids['miso-request-body'], 'value'),
            Output(ids['miso-button'], 'style')
        ],
        [
            Input(ids["update-button-top"], "n_clicks"),
            Input(ids["update-button-bottom"], "n_clicks")
        ],
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
            State(ids["search-sample-ext"], 'value'),
            State(ids['show-data-labels'], 'value'),
            State(ids["insert-median-cutoff"], 'value'),
            State(ids["percent-duplication-cutoff"], 'value'),
            State(ids["clusters-per-sample-cutoff"], 'value'),
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
                       insert_median_cutoff,
                       percent_duplication_cutoff,
                       clusters_per_sample_cutoff,
                       start_date,
                       end_date,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if searchsample and searchsampleext:
            searchsample += searchsampleext
        elif not searchsample and searchsampleext:
            searchsample = searchsampleext
        df = reshape_single_lane_df(WGS_DF, runs, instruments, projects, references, kits, library_designs,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        (approve_run_href, approve_run_style) = sidebar_utils.approve_run_url(runs)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_insert_median": insert_median_cutoff,
            "cutoff_percent_duplication": percent_duplication_cutoff,
            "cutoff_clusters_per_sample": clusters_per_sample_cutoff,
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_ius(df, [
            (cutoff_insert_median_label, BAMQC_COL.InsertMedian, insert_median_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_percent_duplication_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION, percent_duplication_cutoff,
             (lambda row, col, cutoff: row[col] >= cutoff)),
            (cutoff_clusters_per_sample_label, special_cols["Total Clusters (Passed Filter)"], clusters_per_sample_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        (jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)

        (miso_request, miso_button_style) = util.build_miso_info(df, title, 
            [{
                'title': "Median Insert Size",
                'threshold_type': 'ge',
                'threshold': insert_median_cutoff,
                'value': BAMQC_COL.InsertMedian
            }, {
                'title': "% Duplication",
                'threshold_type': 'lt',
                'threshold': percent_duplication_cutoff,
                'value': BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION
            }, {
                'title': "Clusters per Sample (* 10^6)",
                'threshold_type': 'ge',
                'threshold': clusters_per_sample_cutoff,
                'value': special_cols["Total Clusters (Passed Filter)"]
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
