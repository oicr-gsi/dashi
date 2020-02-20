from collections import defaultdict
import logging

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State

import gsiqcetl.column
from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils

logger = logging.getLogger(__name__)

page_name = 'call-ready-ts'
title = "Call-Ready TS"

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
    'show-data-labels',
    'show-all-data-labels',
    'tumour-coverage-cutoff',
    'normal-coverage-cutoff',
    'duplicate-rate-max',
    'callability-cutoff',
    'insert-size-cutoff',
    'pf-tumour-cutoff',
    'pf-normal-cutoff',

    # Graphs
    'graphs',

    # Tables
    'failed-samples',
    'data-table'
])

BAMQC_COL = gsiqcetl.column.BamQc3MergedColumn
HSMETRICS_COL = gsiqcetl.column.HsMetricsColumn
ICHOR_COL = gsiqcetl.column.IchorCnaMergedColumn
CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
PINERY_COL = pinery.column.SampleProvenanceColumn


def dataversion():
    return DATAVERSION


special_cols = {
    "Total Reads (Passed Filter)": "Total reads passed filter",
    "Percent Unique Reads (PF)": "Percent unique reads",
    "Callability (14x/8x)": "callability",
    "Purity": "Purity",
    "File SWID ichorCNA": "File SWID ichorCNA",
    "File SWID MutectCallability": "File SWID MutectCallability",
    "File SWID BamQC3": "File SWID BamQC3",
    "File SWID HsMetrics": "File SWID HsMetrics"
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

    bamqc3_df = util.get_bamqc3_merged()
    bamqc3_df = util.filter_by_library_design(bamqc3_df, util.ex_lib_designs, BAMQC_COL.LibraryDesign)

    bamqc3_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalReads] / 1e6, 3)
    bamqc3_df[special_cols["Percent Unique Reads (PF)"]] = round(
        bamqc3_df[BAMQC_COL.NonPrimaryReads] / bamqc3_df[
            BAMQC_COL.TotalReads], 3)
    ichorcna_df[special_cols["Purity"]] = round(
        ichorcna_df[ICHOR_COL.TumorFraction] * 100.0, 3)
    callability_df[special_cols["Callability (14x/8x)"]] = round(
        callability_df[CALL_COL.Callability] * 100.0, 3)

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
initial["second_sort"] = BAMQC_COL.TotalReads
# Set initial values for graph cutoff lines
cutoff_pf_reads_tumour_label = "Total PF Reads (Tumour) minimum"
cutoff_pf_reads_tumour = "cutoff_pf_reads_tumour"
initial[cutoff_pf_reads_tumour] = 148
cutoff_pf_reads_normal_label = "Total PF Reads (Normal) minimum"
cutoff_pf_reads_normal = "cutoff_pf_reads_normal"
initial[cutoff_pf_reads_normal] = 44
cutoff_coverage_tumour_label = "Coverage (Tumour) minimum"
cutoff_coverage_tumour = "cutoff_coverage_tumour"
initial[cutoff_coverage_tumour] = 80
cutoff_coverage_normal_label = "Coverage (Normal) minimum"
cutoff_coverage_normal = "cutoff_coverage_normal"
initial[cutoff_coverage_normal] = 30
cutoff_duplicate_rate_label = "Duplication (%) maximum"
cutoff_duplicate_rate = "cutoff_duplicate_rate"
initial[cutoff_duplicate_rate] = 50
cutoff_callability_label = "Callability minimum"
cutoff_callability = "cutoff_callability"
initial[cutoff_callability] = 50
cutoff_insert_mean_label = "Insert Mean minimum"
cutoff_insert_mean = "cutoff_insert_mean"
initial[cutoff_insert_mean] = 150

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(TS_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(TS_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(TS_DF, PINERY_COL.Institute)
ALL_TISSUE_MATERIALS = util.unique_set(TS_DF, PINERY_COL.TissuePreparation)
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
    ALL_TISSUE_MATERIALS, ALL_REFERENCES
)
TS_DF = add_graphable_cols(TS_DF, initial, shape_colour.items_for_df(), None, True)


def generate_total_reads_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Total Reads (Passed Filter)"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_pf_reads_normal_label, graph_params[cutoff_pf_reads_normal]),
         (cutoff_pf_reads_tumour_label, graph_params[cutoff_pf_reads_tumour])],
        util.ml_col)


def generate_unique_reads_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Percent Unique Reads (PF)"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_mean_target_coverage_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[HSMETRICS_COL.MeanTargetCoverage],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_callability_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Callability (14x/8x)"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_callability_label, graph_params[cutoff_callability])],
        util.ml_col, showlegend=False)


def generate_mean_insert_size_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[BAMQC_COL.InsertMean],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])],
        util.ml_col, showlegend=False)


def generate_hs_library_size_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[HSMETRICS_COL.HsLibrarySize],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_duplicate_rate_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_duplicate_rate_label, graph_params[cutoff_duplicate_rate])],
        util.ml_col, showlegend=False)


def generate_purity_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Purity"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_fraction_excluded_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[HSMETRICS_COL.PctExcOverlap],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col,
        showlegend=False
    )


def generate_at_dropout_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[HSMETRICS_COL.AtDropout],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col,
        showlegend=False
    )


def generate_gc_dropout_subplot(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[HSMETRICS_COL.GCDropout],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col,
        showlegend=False
    )


def generate_graphs(df, graph_params):
    """
    Subplots are necessary because of the WebGL contexts limit (GR-932).
    """
    graphs = [
        (generate_total_reads_subplot, "Total Reads (Passed Filter)", ""),
        (generate_unique_reads_subplot, "🚧 Percent Unique Reads (PF) -- DATA "
                                        "MAY BE SUSPECT 🚧", "%"),
        (generate_mean_target_coverage_subplot, "Mean Target Coverage", ""),
        (generate_callability_subplot, "Callability (14x/8x) (%)", "%"),
        (generate_mean_insert_size_subplot, "Mean Insert Size", "Base Pairs"),
        (generate_hs_library_size_subplot, "HS Library Size", ""),
        (generate_duplicate_rate_subplot, "Duplication (%)", "%"),
        (generate_purity_subplot, "Purity (%)", "%"),
        (generate_fraction_excluded_subplot, "Fraction Excluded due to "
                                             "Overlap", ""),
        (generate_at_dropout_subplot, "AT Dropout (%)", "%"),
        (generate_gc_dropout_subplot, "GC Dropout (%)", "%")
    ]
    return generate_subplot(
        df, graph_params,
        [graph[0] for graph in graphs],
        [graph[1] for graph in graphs],
        [graph[2] for graph in graphs]
    )


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)

    df = reshape_call_ready_df(TS_DF, initial["projects"], initial["references"],
                               initial["tissue_materials"], initial["sample_types"],
                               initial["first_sort"], initial["second_sort"],
                               initial["colour_by"], initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("File a ticket",
                                          ids['jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title))]),
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
                    html.Button("Update", id=ids["update-button"]),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_projects(ids["all-projects"],
                                                  ids["projects-list"],
                                                  ALL_PROJECTS),
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
                    sidebar_utils.select_first_sort(ids["first-sort"],
                                                    initial["first_sort"],
                                                    shape_colour.dropdown()),

                    sidebar_utils.select_second_sort(ids["second-sort"],
                                                     initial["second_sort"],
                                                     [
                                                         {"label": "Total Reads",
                                                          "value": BAMQC_COL.TotalReads},
                                                         {"label": "Mean Target Coverage",
                                                          "value": HSMETRICS_COL.MeanTargetCoverage},
                                                         {"label": "Callability",
                                                          "value": CALL_COL.Callability},
                                                         {"label": "Tumor Fraction",
                                                          "value": ICHOR_COL.TumorFraction},
                                                         {"label": "HS Library Size",
                                                          "value": HSMETRICS_COL.HsLibrarySize},
                                                         {"label": "Percent Exact Duplicates",
                                                          "value": HSMETRICS_COL.PctExcDupe},
                                                         {"label": "Fraction Excluded due to Overlap",
                                                          "value": HSMETRICS_COL.PctExcOverlap},
                                                         {"label": "AT Dropout",
                                                          "value": HSMETRICS_COL.AtDropout},
                                                         {"label": "GC Dropout",
                                                          "value": HSMETRICS_COL.GCDropout}
                                                     ]),

                    sidebar_utils.select_colour_by(ids["colour-by"],
                                                   shape_colour.dropdown(),
                                                   initial["colour_by"], True),

                    sidebar_utils.select_shape_by(ids["shape-by"],
                                                  shape_colour.dropdown(),
                                                  initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids["search-sample"],
                                                          []),

                    sidebar_utils.show_data_labels_input_call_ready(ids["show-data-labels"],
                                                                    initial["shownames_val"],
                                                                    "ALL LABELS",
                                                                    ids["show-all-data-labels"]),
                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_reads_tumour_label),
                                               ids["pf-tumour-cutoff"], initial[cutoff_pf_reads_tumour]),
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_reads_normal_label),
                                               ids["pf-normal-cutoff"], initial[cutoff_pf_reads_normal]),
                    sidebar_utils.cutoff_input(cutoff_coverage_tumour_label,
                                               ids["tumour-coverage-cutoff"], initial[cutoff_coverage_tumour]),
                    sidebar_utils.cutoff_input(cutoff_coverage_normal_label,
                                               ids["normal-coverage-cutoff"], initial[cutoff_coverage_normal]),
                    sidebar_utils.cutoff_input(cutoff_callability_label,
                                               ids["callability-cutoff"], initial[cutoff_callability]),
                    sidebar_utils.cutoff_input(cutoff_insert_mean_label,
                                               ids["insert-size-cutoff"], initial[cutoff_insert_mean]),
                    sidebar_utils.cutoff_input(cutoff_duplicate_rate_label,
                                               ids["duplicate-rate-max"], initial[cutoff_duplicate_rate]),
                ]),

                # Graphs + Tables tabs
                html.Div(className="seven columns", 
                children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(label="Graphs",
                        children=[
                            core.Graph(
                                id=ids["graphs"],
                                figure=generate_graphs(df, initial)
                            ),
                ])
            ]),
            table_tabs(
                ids["failed-samples"],
                ids["data-table"],
                df,
                ts_table_columns,
                [
                    (cutoff_pf_reads_tumour_label, special_cols["Total Reads (Passed Filter)"],
                     initial[cutoff_pf_reads_tumour],
                     (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
                    (cutoff_pf_reads_normal_label, special_cols["Total Reads (Passed Filter)"],
                     initial[cutoff_pf_reads_normal],
                     (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
                    (cutoff_coverage_tumour_label, HSMETRICS_COL.MeanTargetCoverage,
                     initial[cutoff_coverage_tumour],
                     (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
                    (cutoff_coverage_normal_label, HSMETRICS_COL.MeanTargetCoverage,
                     initial[cutoff_coverage_normal],
                    (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
                    (cutoff_callability_label, special_cols["Callability (14x/8x)"],
                     initial[cutoff_callability],
                     (lambda row, col, cutoff: row[col] < cutoff)),
                    (cutoff_insert_mean_label, BAMQC_COL.InsertMean, initial[cutoff_insert_mean],
                     (lambda row, col, cutoff: row[col] < cutoff)),
                    (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
                     initial[cutoff_duplicate_rate], (lambda row, col, cutoff: row[col] > cutoff)),
                ]
            )
        ])
            ])
        ])
    ])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["graphs"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
            Output(ids["search-sample"], "options"),
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
            State(ids["tumour-coverage-cutoff"], "value"),
            State(ids["normal-coverage-cutoff"], "value"),
            State(ids["duplicate-rate-max"], "value"),
            State(ids["callability-cutoff"], "value"),
            State(ids["insert-size-cutoff"], "value"),
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
                       tumour_coverage_cutoff,
                       normal_coverage_cutoff,
                       duplicate_rate_max,
                       callability_cutoff,
                       insert_size_cutoff,
                       pf_tumour_cutoff,
                       pf_normal_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = reshape_call_ready_df(TS_DF, projects, references, tissue_materials,
                                   sample_types, first_sort, second_sort,
                                   colour_by, shape_by,
                                   shape_colour.items_for_df(), search_sample)
        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            cutoff_coverage_tumour: tumour_coverage_cutoff,
            cutoff_coverage_normal: normal_coverage_cutoff,
            cutoff_duplicate_rate: duplicate_rate_max,
            cutoff_callability: callability_cutoff,
            cutoff_insert_mean: insert_size_cutoff,
            cutoff_pf_reads_tumour: pf_tumour_cutoff,
            cutoff_pf_reads_normal: pf_normal_cutoff
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_pf_reads_tumour_label, special_cols["Total Reads (Passed Filter)"],
             pf_tumour_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_pf_reads_normal_label, special_cols["Total Reads (Passed Filter)"],
             pf_normal_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
            (cutoff_coverage_tumour_label, HSMETRICS_COL.MeanTargetCoverage, tumour_coverage_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_coverage_normal_label, HSMETRICS_COL.MeanTargetCoverage, normal_coverage_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
            (cutoff_callability_label, special_cols["Callability (14x/8x)"], callability_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_insert_mean_label, BAMQC_COL.InsertMean, insert_size_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
             duplicate_rate_max, (lambda row, col, cutoff: row[col] > cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.RootSampleName)

        return [
            generate_graphs(df, graph_params),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=dd),
            [{'label': x, 'value': x} for x in new_search_sample],
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

    @dash_app.callback(
        [
            Output(ids["colour-by"], "value"),
            Output(ids["colour-by"], "disabled"),
        ],
        [Input(ids["first-sort"], "value")]
    )
    def pin_colour_to_first_sort(first_sort):
        return [first_sort, True]
