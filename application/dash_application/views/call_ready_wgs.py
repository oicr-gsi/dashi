from collections import defaultdict
import logging

import dash_html_components as html
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids

from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs_call_ready, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils, log_utils

logger = logging.getLogger(__name__)

""" Set up elements needed for page """
page_name = "call-ready-wgs"
title = "Call-Ready WGS"

ids = init_ids([
    # Buttons
    "jira-issue-button",
    "update-button-top",
    "update-button-bottom",

    # Sidebar controls
    "all-projects",
    "projects-list",
    "all-references",
    "references-list",
    "all-institutes",
    "institutes-list",
    "all-tissue-materials",
    "tissue-materials-list",
    "all-sample-types",
    "sample-types-list",
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "search-sample",
    "search-sample-ext",
    "show-data-labels",
    "show-all-data-labels",
    "cutoff-coverage-tumour",
    "cutoff-coverage-normal",
    "cutoff-callability",
    "cutoff-median-insert",
    "cutoff-duplicate-rate",
    "cutoff-tumor-purity",

    # Graphs
    "graphs",

    # Tables
    "failed-samples",
    "data-table",
    "failed-count",
    "data-count",
])

BAMQC_COL = gsiqcetl.column.BamQc4MergedColumn
CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
ICHOR_COL = gsiqcetl.column.IchorCnaMergedColumn


def dataversion():
    return DATAVERSION


special_cols = {
    # WARNING: Unmapped reads and non-primary reads are filtered out during BAM
    # merging. Do not include any graphs based on those metrics
    "Total Reads (Passed Filter)": "total reads passed filter",
    "Coverage per Gb": "coverage per gb",
    "Percent Callability": "percent callability",
    "File SWID MutectCallability": "File SWID MutectCallability",
    "File SWID BamQC3": "File SWID BamQC3",
    "Tumor Purity (%)": "tumor purity percentage",
    "Total Clusters (Passed Filter)": "Total Clusters",
}


def get_merged_wgs_data():
    """
    Join together all the dataframes needed for graphing:
      * BamQC (where most of the graphed QC data comes from)
      * Pinery (sample information)
      * Instruments (to allow filtering by instrument model)
      * Runs (needed to join Pinery to Instruments)
    """
    # Pull in sample metadata from Pinery.
    pinery_samples = util.get_pinery_merged_samples()
    # Filter the Pinery samples for WG samples and others which will have BAM files generated.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   util.wgs_lib_designs)

    callability_df = util.get_mutect_callability()
    callability_df = util.filter_by_library_design(callability_df,
                                                   util.wgs_lib_designs,
                                                   CALL_COL.LibraryDesign)
    bamqc3_df = util.get_bamqc3_and_4_merged()

    ichorcna_df = util.get_ichorcna_merged()
    ichorcna_df = ichorcna_df[
        util.ichorcna_merged_columns + [ICHOR_COL.TumorFraction]
    ]
    ichorcna_df[special_cols["Tumor Purity (%)"]] = round(
        ichorcna_df[ICHOR_COL.TumorFraction] * 100.0, 3
    )

    callability_df[special_cols["Percent Callability"]] = round(
        callability_df[CALL_COL.Callability] * 100.0, 3)
    bamqc3_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalReads] / 1e6, 3)
    bamqc3_df[special_cols["Total Clusters (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalClusters] / 1e6, 3)
    bamqc3_df[special_cols["Coverage per Gb"]] = round(
        bamqc3_df[BAMQC_COL.CoverageDeduplicated] / (bamqc3_df[
                 BAMQC_COL.TotalReads] *  bamqc3_df[
                 BAMQC_COL.AverageReadLength] / 1e9), 3)
    callability_df.rename(columns={
        CALL_COL.FileSWID: special_cols["File SWID MutectCallability"]},
                          inplace=True)
    bamqc3_df.rename(
        columns={BAMQC_COL.FileSWID: special_cols["File SWID BamQC3"]},
        inplace=True)

    # Join BamQC3 and Callability data
    wgs_df = bamqc3_df.merge(
        callability_df,
        how="left",
        left_on=util.bamqc3_merged_columns,
        right_on=util.callability_merged_columns,
        suffixes=('', '_x')
    )

    # Join QC data and Pinery data
    wgs_df = util.df_with_pinery_samples_merged(wgs_df, pinery_samples,
                                                util.bamqc3_merged_columns)

    # Join in ichorcna data
    wgs_df = wgs_df.merge(
        ichorcna_df,
        how="left",
        left_on=util.bamqc3_merged_columns,
        right_on=util.ichorcna_merged_columns,
        suffixes=('', '_i')
    )

    wgs_df = util.remove_suffixed_columns(wgs_df, '_q')  # Pinery duplicate columns
    wgs_df = util.remove_suffixed_columns(wgs_df, '_x')  # Callability duplicate columns
    wgs_df = util.remove_suffixed_columns(wgs_df, '_i')  # Ichorcna duplicate columns

    return wgs_df, util.cache.versions(
        ["mutectcallability", "bamqc3merged"])


# Make the WGS dataframe
(WGS_DF, DATAVERSION) = get_merged_wgs_data()
wgs_table_columns = WGS_DF.columns

initial = get_initial_call_ready_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = BAMQC_COL.TotalClusters
# Set initial values for graph cutoff lines
# Sourced from https://docs.google.com/document/d/1L056bikfIJDeX6Qzo6fwBb9j7A5NgC6o/edit
# TODO: This is supposed to depend on Coverage being 80x/30x?
cutoff_callability_label = "Callability minimum"
initial["cutoff_callability"] = 50
cutoff_insert_median_label = sidebar_utils.insert_median_cutoff_label
initial["cutoff_insert_median"] = 150
cutoff_duplicate_rate_label = sidebar_utils.percent_duplication_cutoff_label
initial["cutoff_duplicate_rate"] = 50
cutoff_coverage_tumour_label = "Coverage (Tumour) minimum"
initial["cutoff_coverage_tumour"] = 80
cutoff_coverage_normal_label = "Coverage (Normal) minimum"
initial["cutoff_coverage_normal"] = 30
cutoff_tumor_purity_label = "Tumor Purity (%) minimum"
initial["cutoff_tumor_purity"] = 30

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(WGS_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(WGS_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(WGS_DF, PINERY_COL.Institute)
ALL_TISSUE_MATERIALS = util.unique_set(WGS_DF, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(WGS_DF, PINERY_COL.TissueOrigin)
ALL_LIBRARY_DESIGNS = util.unique_set(WGS_DF,
                                      PINERY_COL.LibrarySourceTemplateType)
ALL_SAMPLE_TYPES = util.unique_set(WGS_DF, util.sample_type_col)
ALL_REFERENCES = util.unique_set(WGS_DF, BAMQC_COL.Reference)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected,
                                                                    ALL_PROJECTS,
                                                                    "all_projects"),
    "tissue_materials": lambda selected: log_utils.collapse_if_all_selected(
        selected, ALL_TISSUE_MATERIALS, "all_tissue_materials"),
    "sample_types": lambda selected: log_utils.collapse_if_all_selected(
        selected, ALL_SAMPLE_TYPES, "all_sample_types"),
    "references": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_REFERENCES, "all_references"),
}

shape_colour = ColourShapeCallReady(
    ALL_PROJECTS,
    ALL_LIBRARY_DESIGNS,
    ALL_INSTITUTES,
    ALL_SAMPLE_TYPES,
    ALL_TISSUE_MATERIALS,
    ALL_TISSUE_ORIGIN,
    ALL_REFERENCES
)
WGS_DF = add_graphable_cols(
    WGS_DF, initial, shape_colour.items_for_df(), None, REPORT_TYPE["Call-Ready"]
)

SORT_BY = shape_colour.dropdown() + [
    {
        "label": "Total Clusters (Passed Filter)",
        "value": BAMQC_COL.TotalClusters
    },
    {
        "label": "Coverage (Deduplicated)",
        "value": BAMQC_COL.CoverageDeduplicated,
    },
    {
        "label": "Callability",
        "value": CALL_COL.Callability
    },
    {
        "label": "Median Insert Size",
        "value": BAMQC_COL.InsertMedian
    },
    {
        "label": "Duplication",
        "value": BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION
    },
    {
        "label": "Tumor Purity",
        "value": special_cols["Tumor Purity (%)"]
    },
    {
        "label": "Merged Lane",
        "value": util.ml_col
    }
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
    )

def generate_deduplicated_coverage(df, graph_params):
    return CallReadySubplot(
        "Mean Coverage (Deduplicated)", 
        df,
        lambda d: d[BAMQC_COL.CoverageDeduplicated],
        "", 
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],
        #TODO: Should these move to the CoverageMedian graph? 
        cutoff_lines=[(cutoff_coverage_tumour_label, graph_params["cutoff_coverage_tumour"]), (cutoff_coverage_normal_label, graph_params["cutoff_coverage_normal"])],
    )


def generate_deduplicated_coverage_per_gb(df, graph_params):
    return CallReadySubplot(
        "Mean Coverage per Gb (Deduplicated)", 
        df,
        lambda d: d[special_cols["Coverage per Gb"]],
        "", 
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],)


def generate_median_coverage(df, graph_params):
    return CallReadySubplot(
        "Median Coverage with 10/90 Percentile",
        df,
        lambda d: d[BAMQC_COL.CoverageMedian],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        bar_positive=BAMQC_COL.CoverageMedian90Percentile,
        bar_negative=BAMQC_COL.CoverageMedian10Percentile,
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
        lambda d: d[special_cols["Percent Callability"]],
        "%", 
        graph_params["colour_by"], 
        graph_params["shape_by"],
        hovertext_cols=hover_text,
        cutoff_lines=[(cutoff_callability_label, graph_params["cutoff_callability"])],
    )


def generate_median_insert_size(df, graph_params):
    return CallReadySubplot(
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

def generate_tumor_purity(df, graph_params):
    return CallReadySubplot(
        "Tumor Purity (%)",
        df,
        lambda d: d[special_cols["Tumor Purity (%)"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_tumor_purity_label, graph_params["cutoff_tumor_purity"])],
    )


GRAPHS = [
    generate_total_clusters,
    generate_deduplicated_coverage,
    generate_deduplicated_coverage_per_gb,
    generate_median_coverage,
    generate_callability,
    generate_median_insert_size,
    generate_duplicate_rate,
    generate_tumor_purity,
]
def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]
    elif "req_start" in query and query["req_start"]:
        initial["projects"] = ALL_PROJECTS
        query["req_projects"] = ALL_PROJECTS  # fill in the projects dropdown
    df = reshape_call_ready_df(WGS_DF, initial["projects"], initial["references"],
                               initial["tissue_materials"],
                               initial["sample_types"],
                               initial["first_sort"], initial["second_sort"],
                               initial["colour_by"],
                               initial["shape_by"], shape_colour.items_for_df(),
                               [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("Open an issue",
                                          ids['jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([],
                                                                            title))]),
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
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
                    sidebar_utils.select_sample_types(
                        ids["all-sample-types"], ids["sample-types-list"],
                        ALL_SAMPLE_TYPES),
                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(
                        ids["first-sort"],
                        initial["first_sort"],
                        SORT_BY,
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

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                          []),

                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(ids['search-sample-ext'],
                                                          None),

                    sidebar_utils.show_data_labels_input_call_ready(
                        ids["show-data-labels"],
                        initial["shownames_val"],
                        "ALL LABELS",
                        ids["show-all-data-labels"]),

                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input(cutoff_coverage_tumour_label,
                                               ids["cutoff-coverage-tumour"],
                                               initial["cutoff_coverage_tumour"]),
                    sidebar_utils.cutoff_input(cutoff_coverage_normal_label,
                                               ids["cutoff-coverage-normal"],
                                               initial["cutoff_coverage_normal"]),
                    sidebar_utils.cutoff_input(cutoff_callability_label,
                                               ids["cutoff-callability"],
                                               initial["cutoff_callability"]),
                    sidebar_utils.cutoff_input(cutoff_insert_median_label,
                                               ids["cutoff-median-insert"],
                                               initial["cutoff_insert_median"]),
                    sidebar_utils.cutoff_input(cutoff_duplicate_rate_label,
                                               ids["cutoff-duplicate-rate"],
                                               initial["cutoff_duplicate_rate"]),
                    sidebar_utils.cutoff_input(cutoff_tumor_purity_label,
                                               ids["cutoff-tumor-purity"],
                                               initial["cutoff_tumor_purity"]),

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
                                                  wgs_table_columns,
                                                  [
                                                      (
                                                      cutoff_coverage_tumour_label,
                                                      BAMQC_COL.CoverageDeduplicated,
                                                      initial[
                                                          "cutoff_coverage_tumour"],
                                                      (lambda row, col, cutoff:
                                                       row[
                                                           col] < cutoff and util.is_tumour(
                                                           row))),
                                                      (
                                                      cutoff_coverage_normal_label,
                                                      BAMQC_COL.CoverageDeduplicated,
                                                      initial[
                                                          "cutoff_coverage_normal"],
                                                      (lambda row, col, cutoff:
                                                       row[
                                                           col] < cutoff and util.is_normal(
                                                           row))),
                                                      (cutoff_callability_label,
                                                       special_cols[
                                                           "Percent Callability"],
                                                       initial[
                                                           "cutoff_callability"],
                                                       (lambda row, col, cutoff:
                                                        row[col] < cutoff)),
                                                      (cutoff_insert_median_label,
                                                       BAMQC_COL.InsertMedian,
                                                       initial[
                                                           "cutoff_insert_median"],
                                                       (lambda row, col, cutoff:
                                                        row[col] < cutoff)),
                                                      (
                                                      cutoff_duplicate_rate_label,
                                                      BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
                                                      initial[
                                                          "cutoff_duplicate_rate"],
                                                      (lambda row, col, cutoff:
                                                       row[col] > cutoff)),
                                                      (
                                                          cutoff_tumor_purity_label,
                                                          special_cols["Tumor Purity (%)"],
                                                          initial[
                                                              "cutoff_tumor_purity"],
                                                          (lambda row, col, cutoff:
                                                           row[col] <= cutoff)),
                                                  ]
                                              )
                                          ])
                             ])  # End Tabs
                         ])  # End Div
            ])  # End Div
        ])  # End Div
    ])  # End Loading


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["graphs"], "figure"),
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
            State(ids["cutoff-coverage-tumour"], "value"),
            State(ids["cutoff-coverage-normal"], "value"),
            State(ids["cutoff-callability"], "value"),
            State(ids["cutoff-median-insert"], "value"),
            State(ids["cutoff-duplicate-rate"], "value"),
            State(ids["cutoff-tumor-purity"], "value"),
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
                       coverage_tumour_cutoff,
                       coverage_normal_cutoff,
                       callability_cutoff,
                       insert_median_cutoff,
                       duplicate_rate_cutoff,
                       tumor_purity_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if search_sample and searchsampleext:
            search_sample += searchsampleext
        elif not search_sample and searchsampleext:
            search_sample = searchsampleext
        df = reshape_call_ready_df(WGS_DF, projects, references, tissue_materials,
                                   sample_types, first_sort, second_sort,
                                   colour_by, shape_by,
                                   shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_coverage_tumour": coverage_tumour_cutoff,
            "cutoff_coverage_normal": coverage_normal_cutoff,
            "cutoff_callability": callability_cutoff,
            "cutoff_insert_median": insert_median_cutoff,
            "cutoff_duplicate_rate": duplicate_rate_cutoff,
            "cutoff_tumor_purity": tumor_purity_cutoff,
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_coverage_tumour_label, BAMQC_COL.CoverageDeduplicated,
             coverage_tumour_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_coverage_normal_label, BAMQC_COL.CoverageDeduplicated,
             coverage_normal_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
            (cutoff_callability_label, special_cols["Percent Callability"],
             callability_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_insert_median_label, BAMQC_COL.InsertMedian, insert_median_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_duplicate_rate_label,
             BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
             duplicate_rate_cutoff,
             (lambda row, col, cutoff: row[col] > cutoff)),
            (cutoff_tumor_purity_label,
             special_cols["Tumor Purity (%)"],
             tumor_purity_cutoff,
             (lambda row, col, cutoff: row[col] <= cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.RootSampleName)

        return [
            generate_subplot_from_func(df, graph_params, GRAPHS),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=dd),
            "Rows: {0}".format(len(failure_df.index)),
            "Rows: {0}".format(len(df.index)),
            [{'label': x, 'value': x} for x in new_search_sample],
            [{'label': d[PINERY_COL.ExternalName], 'value': d[PINERY_COL.RootSampleName]} for i, d in df[[PINERY_COL.ExternalName, PINERY_COL.RootSampleName]].iterrows()],
        ]

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
        Output(ids['tissue-materials-list'], 'value'),
        [Input(ids['all-tissue-materials'], 'n_clicks')]
    )
    def all_tissue_materials_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_TISSUE_MATERIALS]

    @dash_app.callback(
        Output(ids['sample-types-list'], 'value'),
        [Input(ids['all-sample-types'], 'n_clicks')]
    )
    def all_sample_types_requested(click):
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
