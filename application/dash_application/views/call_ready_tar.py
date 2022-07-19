from collections import defaultdict
import logging

import dash_html_components as html
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs_call_ready, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils

logger = logging.getLogger(__name__)

page_name = 'call-ready-tar'
title = "Call-Ready Targeted Sequencing"

ids = init_ids([
    # Buttons
    'jira-issue-button',
    'update-button-top',
    'update-button-bottom',

    # Sidebar controls
    'all-projects',
    'projects-list',
    "all-references",
    "references-list",
    'all-tissue-materials',
    'tissue-materials-list',
    'all-sample-types',
    'sample-types-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'search-sample-ext',
    'show-data-labels',
    'show-all-data-labels',
    'tumour-coverage-cutoff',
    'normal-coverage-cutoff',
    'duplicate-rate-max',
    'callability-cutoff',
    'insert-mean-cutoff',
    'pf-tumour-cutoff',
    'pf-normal-cutoff',

    # Graphs
    'graphs',
    'bait-bases',

    # Tables
    'failed-samples',
    'data-table',
    "failed-count",
    "data-count",
])

BAMQC_COL = gsiqcetl.column.BamQc4MergedColumn
HSMETRICS_COL = gsiqcetl.column.HsMetricsColumn
ICHOR_COL = gsiqcetl.column.IchorCnaMergedColumn
CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
PINERY_COL = pinery.column.SampleProvenanceColumn


def dataversion():
    return DATAVERSION


special_cols = {
    # WARNING: Unmapped reads and non-primary reads are filtered out during BAM
    # merging. Do not include any graphs based on those metrics
    "Total Reads (Passed Filter)": "Total reads passed filter",
    "Callability": "callability",
    "Purity": "Purity",
    "File SWID ichorCNA": "File SWID ichorCNA",
    "File SWID MutectCallability": "File SWID MutectCallability",
    "File SWID BamQC3": "File SWID BamQC3",
    "File SWID HsMetrics": "File SWID HsMetrics",
    "Total Bait Bases": "Total bait bases",
    "On Bait Percentage": "On Bait Percentage",
    "Near Bait Percentage": "Near Bait Percentage",
    "On Target Percentage": "On Target Percentage",
    "Total Clusters (Passed Filter)": "Total Clusters",
    "Coverage per Gb": "coverage per gb",
}


def get_merged_ts_data():
    """"
    Join together all the dataframes needed for graphing:
      * BamQC (where most of the graphed QC data comes from)
      * ichorCNA (where the QC data comes from for Purity)
      * MutectCallability (where the QC data comes from for Callability graph)
      * HSMetrics (where the remainder of the QC data comes from)
      * Pinery (sample information)
    """

    # Sample metadata from Pinery
    pinery_samples = util.get_pinery_merged_samples()
    pinery_samples = util.filter_by_library_design(pinery_samples, util.ex_lib_designs)

    ichorcna_df = util.get_ichorcna_merged()
    ichorcna_df = util.filter_by_library_design(ichorcna_df, util.ex_lib_designs, ICHOR_COL.LibraryDesign)

    hsmetrics_df = util.get_hsmetrics_merged()
    hsmetrics_df = util.filter_by_library_design(hsmetrics_df, util.ex_lib_designs, HSMETRICS_COL.LibraryDesign)

    callability_df = util.get_mutect_callability()
    callability_df = util.filter_by_library_design(callability_df, util.ex_lib_designs, CALL_COL.LibraryDesign)

    bamqc3_df = util.get_bamqc3_and_4_merged()
    bamqc3_df = util.filter_by_library_design(bamqc3_df, util.ex_lib_designs, BAMQC_COL.LibraryDesign)

    bamqc3_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalReads] / 1e6, 3)
    bamqc3_df[special_cols["Total Clusters (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalClusters] / 1e6, 3)
    bamqc3_df[special_cols["Coverage per Gb"]] = round(
        bamqc3_df[BAMQC_COL.CoverageDeduplicated] / (
                bamqc3_df[BAMQC_COL.TotalReads] *
                bamqc3_df[ BAMQC_COL.AverageReadLength] /
                1e9
        ), 3)
    ichorcna_df[special_cols["Purity"]] = round(
        ichorcna_df[ICHOR_COL.TumorFraction] * 100.0, 3)
    callability_df[special_cols["Callability"]] = round(
        callability_df[CALL_COL.Callability] * 100.0, 3)
    hsmetrics_df[special_cols["Total Bait Bases"]] = hsmetrics_df[HSMETRICS_COL.OnBaitBases] + hsmetrics_df[HSMETRICS_COL.NearBaitBases] + hsmetrics_df[HSMETRICS_COL.OffBaitBases]
    hsmetrics_df[special_cols["On Bait Percentage"]] = hsmetrics_df[HSMETRICS_COL.OnBaitBases] /  hsmetrics_df[special_cols["Total Bait Bases"]] * 100
    hsmetrics_df[special_cols["Near Bait Percentage"]] = hsmetrics_df[HSMETRICS_COL.NearBaitBases] /  hsmetrics_df[special_cols["Total Bait Bases"]] * 100
    hsmetrics_df[special_cols["On Target Percentage"]] = hsmetrics_df[HSMETRICS_COL.PCT_SELECTED_BASES] * 100

    ichorcna_df.rename(columns={ICHOR_COL.FileSWID: special_cols["File SWID ichorCNA"]}, inplace=True)
    callability_df.rename(columns={CALL_COL.FileSWID: special_cols["File SWID MutectCallability"]}, inplace=True)
    bamqc3_df.rename(columns={BAMQC_COL.FileSWID: special_cols["File SWID BamQC3"]}, inplace=True)
    hsmetrics_df.rename(columns={HSMETRICS_COL.FileSWID: special_cols["File SWID HsMetrics"]}, inplace=True)

    # Join IchorCNA and HSMetrics Data
    ts_df = ichorcna_df.merge(
        hsmetrics_df,
        how="outer",
        left_on=util.ichorcna_merged_columns,
        right_on=util.hsmetrics_merged_columns,
        suffixes=('', '_x'))

    # Join IchorCNA+HsMetrics and Callability data
    ts_df = ts_df.merge(
        callability_df,
        how="outer",
        left_on=util.ichorcna_merged_columns,
        right_on=util.callability_merged_columns,
        suffixes=('', '_y'))

    # Join BamQC3 and QC data
    ts_df = ts_df.merge(
        bamqc3_df,
        how="outer",
        left_on=util.ichorcna_merged_columns,
        right_on=util.bamqc3_merged_columns,
        suffixes=('', '_z'))

    # Join QC data and Pinery data
    ts_df = util.df_with_pinery_samples_merged(ts_df, pinery_samples, util.bamqc3_merged_columns)

    ts_df = util.remove_suffixed_columns(ts_df, '_q')  # Pinery duplicate columns
    ts_df = util.remove_suffixed_columns(ts_df, '_x')  # IchorCNA duplicate columns
    ts_df = util.remove_suffixed_columns(ts_df, '_y')  # Callability duplicate columns
    ts_df = util.remove_suffixed_columns(ts_df, '_z')  # BamQC3 duplicate columns

    return ts_df, util.cache.versions(["bamqc3merged", "ichorcnamerged", "mutectcallability", "hsmetrics"])


(TS_DF, DATAVERSION) = get_merged_ts_data()
ts_table_columns = TS_DF.columns

initial = get_initial_call_ready_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = BAMQC_COL.TotalClusters
# Set initial values for graph cutoff lines
cutoff_pf_clusters_tumour_label = "Total PF Clusters (Tumour) minimum"
initial["cutoff_pf_clusters_tumour"] = 74
cutoff_pf_clusters_normal_label = "Total PF Clusters (Normal) minimum"
initial["cutoff_pf_clusters_normal"] = 22
cutoff_coverage_tumour_label = "Coverage (Tumour) minimum"
initial["cutoff_coverage_tumour"] = 80
cutoff_coverage_normal_label = "Coverage (Normal) minimum"
initial["cutoff_coverage_normal"] = 30
cutoff_duplicate_rate_label = sidebar_utils.percent_duplication_cutoff_label
initial["cutoff_duplicate_rate"] = 50
# TODO: Look at ALL the reports for common labels
cutoff_callability_label = "Callability minimum"
initial["cutoff_callability"] = 50
cutoff_insert_mean_label = sidebar_utils.insert_mean_cutoff_label
initial["cutoff_insert_mean"] = 150

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(TS_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(TS_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(TS_DF, PINERY_COL.Institute)
ALL_TISSUE_MATERIALS = util.unique_set(TS_DF, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(TS_DF, PINERY_COL.TissueOrigin)
ALL_LIBRARY_DESIGNS = util.unique_set(TS_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_SAMPLE_TYPES = util.unique_set(TS_DF, util.sample_type_col)
ALL_REFERENCES = util.unique_set(TS_DF, ICHOR_COL.Reference)

collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "tissue_materials": lambda selected: log_utils.collapse_if_all_selected(
        selected, ALL_TISSUE_MATERIALS, "all_tissue_materials"),
    "sample_types": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_SAMPLE_TYPES, "all_sample_types"),
    "references": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_REFERENCES, "all_references"),
}

shape_colour = ColourShapeCallReady(
    ALL_PROJECTS, ALL_LIBRARY_DESIGNS, ALL_INSTITUTES, ALL_SAMPLE_TYPES,
    ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN, ALL_REFERENCES
)
TS_DF = add_graphable_cols(
    TS_DF, initial, shape_colour.items_for_df(), None, REPORT_TYPE["Call-Ready"]
)

SORT_BY = shape_colour.dropdown() + [
    {"label": "Total Clusters",
     "value": BAMQC_COL.TotalClusters},
    {"label": "Median Target Coverage",
     "value": HSMETRICS_COL.MedianTargetCoverage},
    {"label": "Callability",
     "value": CALL_COL.Callability},
    {"label": "Tumor Fraction",
     "value": ICHOR_COL.TumorFraction},
    {"label": "HS Library Size",
     "value": HSMETRICS_COL.HsLibrarySize},
    {"label": "Duplication (%)",
     "value": BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION},
    {"label": "Fraction Excluded due to Overlap",
     "value": HSMETRICS_COL.PctExcOverlap},
    {"label": "AT Dropout",
     "value": HSMETRICS_COL.AtDropout},
    {"label": "GC Dropout",
     "value": HSMETRICS_COL.GCDropout},
    {"label": "On Bait",
     "value": special_cols["On Bait Percentage"]},
    {"label": "Near Bait",
     "value": special_cols["Near Bait Percentage"]},
    {"label": "On Target", # Create scatter plot for on target reads (%)
     "value": special_cols["On Target Percentage"]},
    {"label": "Merged Lane",
     "value": util.ml_col}
]

def generate_total_clusters(df, graph_params):
    return CallReadySubplot(
        "Total Clusters (Passed Filter)",
        df,
        lambda d: d[special_cols["Total Clusters (Passed Filter)"]],
        "# PF Clusters X 10^6",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_pf_clusters_normal_label, graph_params["cutoff_pf_clusters_normal"]),
                      (cutoff_pf_clusters_tumour_label, graph_params["cutoff_pf_clusters_tumour"])]
    )


def generate_median_target_coverage(df, graph_params):
    return CallReadySubplot(
        "Median Target Coverage",
        df,
        lambda d: d[HSMETRICS_COL.MedianTargetCoverage],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_callability(df, graph_params):
    extra_cols = [CALL_COL.NormalMinCoverage, CALL_COL.TumorMinCoverage]
    if graph_params["shownames_val"] is None:
        hover_text = extra_cols
    else:
        # 'graph_params object is shared and is not changed
        hover_text = graph_params["shownames_val"] + extra_cols

    return CallReadySubplot(
        "Callability (%)",
        df,
        lambda d: d[special_cols["Callability"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        hovertext_cols=hover_text,
        cutoff_lines=[(cutoff_callability_label, graph_params["cutoff_callability"])],
    )

def generate_mean_insert_size(df, graph_params):
    return CallReadySubplot(
        "Mean Insert Size",
        df,
        lambda d: d[BAMQC_COL.InsertMean],
        "Base Pairs",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_insert_mean_label, graph_params["cutoff_insert_mean"])],
    )

def generate_hs_library_size(df, graph_params):
    return CallReadySubplot(
        "HS Library Size",
        df,
        lambda d: d[HSMETRICS_COL.HsLibrarySize],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_duplicate_rate(df, graph_params):
    return CallReadySubplot(
        "Duplication (%)",
        df,
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_duplicate_rate_label, graph_params["cutoff_duplicate_rate"])],
    )


def generate_fraction_excluded(df, graph_params):
    return CallReadySubplot(
        "Excluded due to Overlap (%)",
        df,
        lambda d: d[HSMETRICS_COL.PctExcOverlap] * 100,
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_at_dropout(df, graph_params):
    return CallReadySubplot(
        "AT Dropout (%)",
        df,
        lambda d: d[HSMETRICS_COL.AtDropout],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_gc_dropout(df, graph_params):
    return CallReadySubplot(
        "GC Dropout (%)",
        df,
        lambda d: d[HSMETRICS_COL.GCDropout],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_bait(df):
    return generate_bar(
        df,
        [special_cols["On Bait Percentage"], special_cols["Near Bait Percentage"], ],
        lambda d: d[util.ml_col],
        lambda d, col: d[col],
        "On and Near Bait Bases (%)",
        "%",
        fill_color={
            special_cols["On Bait Percentage"]: "black",
            special_cols["Near Bait Percentage"]: "red",
        },
    )

def generate_on_target_reads_scatter_TEST_DO_NOT_USE(df, graph_params):
    return CallReadySubplot(
        "TEST DO NOT USE On Target Reads (%)",
        df,
        lambda d: d[special_cols["On Target Percentage"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )



GRAPHS = [
    generate_total_clusters,
    generate_median_target_coverage,
    generate_callability,
    generate_mean_insert_size,
    generate_hs_library_size,
    generate_duplicate_rate,
    generate_fraction_excluded,
    generate_at_dropout,
    generate_gc_dropout,
    generate_on_target_reads_scatter_TEST_DO_NOT_USE
]


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]
    elif "req_start" in query and query["req_start"]:
        initial["projects"] = ALL_PROJECTS
        query["req_projects"] = ALL_PROJECTS  # fill in the projects dropdown

    df = reshape_call_ready_df(TS_DF, initial["projects"], initial["references"],
                               initial["tissue_materials"], initial["sample_types"],
                               initial["first_sort"], initial["second_sort"],
                               initial["colour_by"], initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("Open an issue",
                                          ids['jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title))]),
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
                    html.Br(),
                    html.Button("Update", id=ids["update-button-top"], className="update-button"),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_projects(ids["all-projects"],
                                                  ids["projects-list"],
                                                  ALL_PROJECTS,
                                                  query["req_projects"]),
                    sidebar_utils.select_reference(ids["all-references"],
                                                   ids["references-list"],
                                                   ALL_REFERENCES),
                    sidebar_utils.select_tissue_materials(
                        ids["all-tissue-materials"],
                        ids["tissue-materials-list"],
                        ALL_TISSUE_MATERIALS),
                    sidebar_utils.select_sample_types(ids["all-sample-types"],
                                                      ids["sample-types-list"],
                                                      ALL_SAMPLE_TYPES),
                    sidebar_utils.hr(),

                    # Sort, colour and shape
                    sidebar_utils.select_first_sort(
                        ids["first-sort"],
                        initial["first_sort"],
                        SORT_BY
                    ),

                    sidebar_utils.select_second_sort(
                        ids["second-sort"],
                        initial["second_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_colour_by(ids["colour-by"],
                                                   shape_colour.dropdown(),
                                                   initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids["shape-by"],
                                                  shape_colour.dropdown(),
                                                  initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids["search-sample"],
                                                          []),
                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(ids['search-sample-ext'],
                                                                                  None),

                    sidebar_utils.show_data_labels_input_call_ready(ids["show-data-labels"],
                                                                    initial["shownames_val"],
                                                                    "ALL LABELS",
                                                                    ids["show-all-data-labels"]),
                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_clusters_tumour_label),
                                               ids["pf-tumour-cutoff"], initial["cutoff_pf_clusters_tumour"]),
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_clusters_normal_label),
                                               ids["pf-normal-cutoff"], initial["cutoff_pf_clusters_normal"]),
                    sidebar_utils.cutoff_input(cutoff_coverage_tumour_label,
                                               ids["tumour-coverage-cutoff"], initial["cutoff_coverage_tumour"]),
                    sidebar_utils.cutoff_input(cutoff_coverage_normal_label,
                                               ids["normal-coverage-cutoff"], initial["cutoff_coverage_normal"]),
                    sidebar_utils.cutoff_input(cutoff_callability_label,
                                               ids["callability-cutoff"], initial["cutoff_callability"]),
                    sidebar_utils.cutoff_input(cutoff_insert_mean_label,
                                               ids["insert-mean-cutoff"], initial["cutoff_insert_mean"]),
                    sidebar_utils.cutoff_input(cutoff_duplicate_rate_label,
                                               ids["duplicate-rate-max"], initial["cutoff_duplicate_rate"]),

                    html.Br(),
                    html.Button("Update", id=ids["update-button-bottom"], className="update-button"),
                ]),

                # Graphs + Tables tabs
                html.Div(className="seven columns",
                         children=[
                             core.Tabs([
                                 # Graphs tab
                                 core.Tab(label="Graphs",
                                          children=[
                                              create_graph_element_with_subplots(ids["graphs"], df, initial, GRAPHS),
                                              core.Graph(
                                                  id=ids['bait-bases'],
                                                  figure=generate_bait(df)
                                              ),
                                          ]),
                                 # Tables tab
                                 core.Tab(label="Tables",
                                          children=[
                                              table_tabs_call_ready(
                                                  ids["failed-samples"],
                                                  ids["data-table"],
                                                  ids["failed-count"],
                                                  ids["data-count"],
                                                  df,
                                                  ts_table_columns,
                                                  [
                                                      (cutoff_pf_clusters_tumour_label, special_cols["Total Clusters (Passed Filter)"],
                                                       initial["cutoff_pf_clusters_tumour"],
                                                       (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
                                                      (cutoff_pf_clusters_normal_label, special_cols["Total Clusters (Passed Filter)"],
                                                       initial["cutoff_pf_clusters_normal"],
                                                       (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
                                                      (cutoff_coverage_tumour_label, HSMETRICS_COL.MedianTargetCoverage,
                                                       initial["cutoff_coverage_tumour"],
                                                       (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
                                                      (cutoff_coverage_normal_label, HSMETRICS_COL.MedianTargetCoverage,
                                                       initial["cutoff_coverage_normal"],
                                                       (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
                                                      (cutoff_callability_label, special_cols["Callability"],
                                                       initial["cutoff_callability"],
                                                       (lambda row, col, cutoff: row[col] < cutoff)),
                                                      (cutoff_insert_mean_label, BAMQC_COL.InsertMean, initial["cutoff_insert_mean"],
                                                       (lambda row, col, cutoff: row[col] < cutoff)),
                                                      (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
                                                       initial["cutoff_duplicate_rate"], (lambda row, col, cutoff: row[col] > cutoff)),
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
            Output(ids["graphs"], "figure"),
            Output(ids['bait-bases'], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
            Output(ids["failed-count"], "children"),
            Output(ids["data-count"], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids['search-sample-ext'], 'options'),
        ],
        [Input(ids["update-button-top"], "n_clicks"),
         Input(ids["update-button-bottom"], "n_clicks")],
        [
            State(ids["projects-list"], "value"),
            State(ids['references-list'], 'value'),
            State(ids["tissue-materials-list"], "value"),
            State(ids["sample-types-list"], "value"),
            State(ids["first-sort"], "value"),
            State(ids["second-sort"], "value"),
            State(ids["colour-by"], "value"),
            State(ids["shape-by"], "value"),
            State(ids["show-data-labels"], "value"),
            State(ids["search-sample"], "value"),
            State(ids['search-sample-ext'], 'value'),
            State(ids["tumour-coverage-cutoff"], "value"),
            State(ids["normal-coverage-cutoff"], "value"),
            State(ids["duplicate-rate-max"], "value"),
            State(ids["callability-cutoff"], "value"),
            State(ids["insert-mean-cutoff"], "value"),
            State(ids["pf-tumour-cutoff"], "value"),
            State(ids["pf-normal-cutoff"], "value"),
            State('url', 'search'),
        ]
    )
    def update_pressed(click,
                       click2,
                       projects,
                       references,
                       tissue_materials,
                       sample_types,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       show_names,
                       search_sample,
                       searchsampleext,
                       tumour_coverage_cutoff,
                       normal_coverage_cutoff,
                       duplicate_rate_max,
                       callability_cutoff,
                       insert_mean_cutoff,
                       pf_tumour_cutoff,
                       pf_normal_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if search_sample and searchsampleext:
            search_sample += searchsampleext
        elif not search_sample and searchsampleext:
            search_sample = searchsampleext
        df = reshape_call_ready_df(TS_DF, projects, references, tissue_materials,
                                   sample_types, first_sort, second_sort,
                                   colour_by, shape_by,
                                   shape_colour.items_for_df(), search_sample)
        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_coverage_tumour": tumour_coverage_cutoff,
            "cutoff_coverage_normal": normal_coverage_cutoff,
            "cutoff_duplicate_rate": duplicate_rate_max,
            "cutoff_callability": callability_cutoff,
            "cutoff_insert_mean": insert_mean_cutoff,
            "cutoff_pf_clusters_tumour": pf_tumour_cutoff,
            "cutoff_pf_clusters_normal": pf_normal_cutoff
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_pf_clusters_tumour_label, special_cols["Total Clusters (Passed Filter)"],
             pf_tumour_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_pf_clusters_normal_label, special_cols["Total Clusters (Passed Filter)"],
             pf_normal_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
            (cutoff_coverage_tumour_label, HSMETRICS_COL.MedianTargetCoverage, tumour_coverage_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_coverage_normal_label, HSMETRICS_COL.MedianTargetCoverage, normal_coverage_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
            (cutoff_callability_label, special_cols["Callability"], callability_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_insert_mean_label, BAMQC_COL.InsertMean, insert_mean_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
             duplicate_rate_max, (lambda row, col, cutoff: row[col] > cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.RootSampleName)

        return [
            generate_subplot_from_func(df, graph_params, GRAPHS),
            generate_bait(df),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=dd),
            "Rows: {0}".format(len(failure_df.index)),
            "Rows: {0}".format(len(df.index)),
            [{'label': x, 'value': x} for x in new_search_sample],
            [{'label': d[PINERY_COL.ExternalName], 'value': d[PINERY_COL.RootSampleName]} for i, d in df[[PINERY_COL.ExternalName, PINERY_COL.RootSampleName]].iterrows()],
        ]

    @dash_app.callback(
        Output(ids["projects-list"], "value"),
        [Input(ids["all-projects"], "n_clicks")]
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
        Output(ids["tissue-materials-list"], "value"),
        [Input(ids["all-tissue-materials"], "n_clicks")]
    )
    def all_tissue_materials_selected(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_TISSUE_MATERIALS]

    @dash_app.callback(
        Output(ids["sample-types-list"], "value"),
        [Input(ids["all-sample-types"], "n_clicks")]
    )
    def all_sample_types_selected(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_SAMPLE_TYPES]

    @dash_app.callback(
        Output(ids["show-data-labels"], "value"),
        [Input(ids["show-all-data-labels"], "n_clicks")],
        [State(ids["show-data-labels"], "options")]
    )
    def all_data_labels_requested(click, avail_options):
        sidebar_utils.update_only_if_clicked(click)
        return [x["value"] for x in avail_options]
