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
    'update-button',

    # Sidebar controls
    'all-projects',
    'projects-list',
    'all-tissue-preps',
    'tissue-preps-list',
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
    'total-reads',
    'unique-reads',
    'mean-target-coverage',
    'callability',
    'mean-insert-size',
    'hs-library-size',
    'duplicate-rate',
    'purity',
    'fraction-excluded',
    'at-dropout',
    'gc-dropout',

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


# todo: come back and include whatever else should be a special column
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

ts_table_columns = [*BAMQC_COL.values(), *HSMETRICS_COL.values(), *ICHOR_COL.values(), *CALL_COL.values(),
                    *special_cols.values()]


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
    pinery_samples = util.get_pinery_merged_samples(False)  # todo: come back
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
        right_on=util.hsmetrics_merged_columns)

    # Join IchorCNA+HsMetrics and Callability data
    ts_df = ts_df.merge(
        callability_df,
        how="outer",
        left_on=util.hsmetrics_merged_columns,
        right_on=util.callability_merged_columns)

    # Join BamQC3 and QC data
    ts_df = ts_df.merge(
        bamqc3_df,
        how="outer",
        left_on=util.callability_merged_columns,
        right_on=util.bamqc3_merged_columns)

    # Join QC data and Pinery data
    ts_df = util.df_with_pinery_samples_merged(ts_df, pinery_samples, util.bamqc3_merged_columns)

    return ts_df, util.cache.versions(["bamqc3merged", "ichorcnamerged", "mutectcallability", "hsmetrics"])


(TS_DF, DATAVERSION) = get_merged_ts_data()

# Set additional initial values for dropdown menus
initial = get_initial_call_ready_values()
initial["second_sort"] = BAMQC_COL.TotalReads
initial["tumour_coverage_cutoff"] = 80
initial["normal_coverage_cutoff"] = 30
initial["duplicate_rate_max"] = 50
initial["callability_cutoff"] = 50
initial["insert_size_cutoff"] = 150
initial["pf_tumour_cutoff"] = 148
initial["pf_normal_cutoff"] = 44

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(TS_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(TS_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(TS_DF, PINERY_COL.Institute)
ALL_TISSUE_PREPS = util.unique_set(TS_DF, PINERY_COL.TissuePreparation)
ALL_LIBRARY_DESIGNS = util.unique_set(TS_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_SAMPLE_TYPES = util.unique_set(TS_DF, util.sample_type_col)
ALL_SAMPLES = util.unique_set(TS_DF, PINERY_COL.RootSampleName)

collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "tissue_preps": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_TISSUE_PREPS, "all_tissue_preps"),
    "sample_types": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_SAMPLE_TYPES, "all_sample_types")
}

shape_colour = ColourShapeCallReady(ALL_PROJECTS, ALL_KITS, ALL_LIBRARY_DESIGNS, ALL_INSTITUTES, ALL_SAMPLE_TYPES)
TS_DF = add_graphable_cols(TS_DF, initial, shape_colour.items_for_df(), None, True)


def generate_total_reads(df, graph_params):
    return generate(
        "Total Reads (Passed Filter)", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[special_cols["Total Reads (Passed Filter)"]],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


# def generate_unique_reads(df, graph_params):
#    return generate(
#        "Percent Unique Reads (PF)", df,
#        lambda d: d[PINERY_COL.RootSampleName],
#        lambda d: d[special_cols["Percent Unique Reads (PF)"]],
#        "%", graph_params["colour_by"], graph_params["shape_by"],
#        graph_params["shownames_val"], None,
#        PINERY_COL.RootSampleName)


def generate_mean_target_coverage(df, graph_params):
    return generate(
        "Mean Target Coverage", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[HSMETRICS_COL.MeanTargetCoverage],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


def generate_callability(df, graph_params):
    return generate(
        "Callability (14x/8x)", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[special_cols["Callability (14x/8x)"]],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], graph_params["callability_cutoff"],
        PINERY_COL.RootSampleName)


def generate_mean_insert_size(df, graph_params):
    return generate(
        "Mean Insert Size", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[BAMQC_COL.InsertMean],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], graph_params["insert_size_cutoff"],
        PINERY_COL.RootSampleName)


def generate_hs_library_size(df, graph_params):
    return generate(
        "HS Library Size", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[HSMETRICS_COL.HsLibrarySize],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


def generate_duplicate_rate(df, graph_params):
    return generate(
        "Duplicate Rate", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], graph_params["duplicate_rate_max"],
        PINERY_COL.RootSampleName)


def generate_purity(df, graph_params):
    return generate(
        "Purity", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[special_cols["Purity"]],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


def generate_fraction_excluded(df, graph_params):
    return generate(
        "Fraction Excluded due to Overlap", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[HSMETRICS_COL.PctExcOverlap],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


def generate_at_dropout(df, graph_params):
    return generate(
        "AT Dropout %", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[HSMETRICS_COL.AtDropout],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


def generate_gc_dropout(df, graph_params):
    return generate(
        "GC Dropout %", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[HSMETRICS_COL.GCDropout],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], None,
        PINERY_COL.RootSampleName)


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)

    df = reshape_call_ready_df(TS_DF, initial["projects"], initial["tissue_preps"], initial["sample_types"],
                               initial["first_sort"], initial["second_sort"],
                               initial["colour_by"], initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
                    html.Button("Update", id=ids["update-button"]),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_projects(ids["all-projects"],
                                                  ids["projects-list"],
                                                  ALL_PROJECTS),
                    sidebar_utils.select_tissue_prep(ids["all-tissue-preps"],
                                                     ids["tissue-preps-list"],
                                                     ALL_TISSUE_PREPS),
                    sidebar_utils.select_sample_type(ids["all-sample-types"],
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
                                                         # {"label": "Unique Reads",
                                                         # "value": },
                                                         {"label": "Mean Target Coverage",
                                                          "value": HSMETRICS_COL.MeanTargetCoverage},
                                                         {"label": "Callability",
                                                          "value": CALL_COL.Callability},
                                                         {"label": "Tumor Fraction",
                                                          "value": ICHOR_COL.TumorFraction},
                                                         {"label": "HS Library Size",
                                                          "value": HSMETRICS_COL.HsLibrarySize},
                                                         {"label": "PctExcDupe??",
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
                                                   initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids["shape-by"],
                                                  shape_colour.dropdown(),
                                                  initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids["search-sample"],
                                                          ALL_SAMPLES),

                    sidebar_utils.show_data_labels_input_call_ready(ids["show-data-labels"],
                                                                    initial["shownames_val"],
                                                                    "ALL LABELS",
                                                                    ids["show-all-data-labels"]),
                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input("Tumour Coverage minimum",
                                               ids["tumour-coverage-cutoff"], initial["tumour_coverage_cutoff"]),
                    sidebar_utils.cutoff_input("Normal Coverage minimum",
                                               ids["normal-coverage-cutoff"], initial["normal_coverage_cutoff"]),
                    sidebar_utils.cutoff_input("Duplicate Rate maximum",
                                               ids["duplicate-rate-max"], initial["duplicate_rate_max"]),
                    sidebar_utils.cutoff_input("Callability minimum",
                                               ids["callability-cutoff"], initial["callability_cutoff"]),
                    sidebar_utils.cutoff_input("Mean Insert Size minimum",
                                               ids["insert-size-cutoff"], initial["insert_size_cutoff"]),
                    sidebar_utils.cutoff_input("Passed Filter Reads (Tumour) minimum",
                                               ids["pf-tumour-cutoff"], initial["pf_tumour_cutoff"]),
                    sidebar_utils.cutoff_input("Passed Filter Reads (Normal) minimum",
                                               ids["pf-normal-cutoff"], initial["pf_normal_cutoff"]),
                ]),

                html.Div(className="seven columns", children=[
                    core.Graph(
                        id=ids["total-reads"],
                        figure=generate_total_reads(df, initial)),

                    # core.Graph(
                    #    id=ids["unique-reads"],
                    #    figure=generate_unique_reads(df, initial)),

                    core.Graph(
                        id=ids["mean-target-coverage"],
                        figure=generate_mean_target_coverage(df, initial)),

                    core.Graph(
                        id=ids["callability"],
                        figure=generate_callability(df, initial)),

                    core.Graph(
                        id=ids["mean-insert-size"],
                        figure=generate_mean_insert_size(df, initial)),

                    core.Graph(
                        id=ids["hs-library-size"],
                        figure=generate_hs_library_size(df, initial)),

                    core.Graph(
                        id=ids["duplicate-rate"],
                        figure=generate_duplicate_rate(df, initial)),

                    core.Graph(
                        id=ids["purity"],
                        figure=generate_purity(df, initial)),

                    core.Graph(
                        id=ids["fraction-excluded"],
                        figure=generate_fraction_excluded(df, initial)),

                    core.Graph(
                        id=ids["at-dropout"],
                        figure=generate_at_dropout(df, initial)),

                    core.Graph(
                        id=ids["gc-dropout"],
                        figure=generate_gc_dropout(df, initial)),

                ])
            ]),
            table_tabs(
                ids["failed-samples"],
                ids["data-table"],
                df,
                ts_table_columns,
                [
                    # TODO: add the tumour/normal cutoff differences for total PF reads
                    # TODO: add the tumour/normal cutoff differences for coverage
                    ('Callability Cutoff', special_cols["Callability (14x/8x)"],
                     initial["callability_cutoff"], True),
                    ('Insert Mean Cutoff', BAMQC_COL.InsertMean,
                     initial["insert_size_cutoff"], True),
                    ('Duplicate Cutoff', BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
                     initial["duplicate_rate_max"], False),
                ]
            )
        ])
    ])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["total-reads"], "figure"),
            # Output(ids["unique-reads"], "figure"),
            Output(ids["mean-target-coverage"], "figure"),
            Output(ids["callability"], "figure"),
            Output(ids["mean-insert-size"], "figure"),
            Output(ids["hs-library-size"], "figure"),
            Output(ids["duplicate-rate"], "figure"),
            Output(ids["purity"], "figure"),
            Output(ids["fraction-excluded"], "figure"),
            Output(ids["at-dropout"], "figure"),
            Output(ids["gc-dropout"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
        ],
        [Input(ids["update-button"], "n_clicks")],
        [
            State(ids["projects-list"], "value"),
            State(ids["tissue-preps-list"], "value"),
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
                       projects,
                       tissue_preps,
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

        df = reshape_call_ready_df(TS_DF, projects, tissue_preps, sample_types, first_sort, second_sort, colour_by,
                                   shape_by, shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "tumour_coverage_cutoff": tumour_coverage_cutoff,
            "normal_coverage_cutoff": normal_coverage_cutoff,
            "duplicate_rate_max": duplicate_rate_max,
            "callability_cutoff": callability_cutoff,
            "insert_size_cutoff": insert_size_cutoff,
            "pf_tumour_cutoff": pf_tumour_cutoff,
            "pf_normal_cutoff": pf_normal_cutoff
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            # Todo: add the rest of the cutoff differences
            ('Callability Cutoff', special_cols["Callability (14x/8x)"],
             callability_cutoff, True),
            ('Insert Mean Cutoff', BAMQC_COL.InsertMean,
             insert_size_cutoff, True),
            ('Duplicate Cutoff', BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
             duplicate_rate_max, True)
        ])

        return [
            generate_total_reads(df, graph_params),
            # generate_unique_reads(df, graph_params),
            generate_mean_target_coverage(df, graph_params),
            generate_callability(df, graph_params),
            generate_mean_insert_size(df, graph_params),
            generate_hs_library_size(df, graph_params),
            generate_duplicate_rate(df, graph_params),
            generate_purity(df, graph_params),
            generate_fraction_excluded(df, graph_params),
            generate_at_dropout(df, graph_params),
            generate_gc_dropout(df, graph_params),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=dd),
        ]

    @dash_app.callback(
        Output(ids["projects-list"], "value"),
        [Input(ids["all-projects"], "n_clicks")]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]

    @dash_app.callback(
        Output(ids["tissue-preps-list"], "value"),
        [Input(ids["all-tissue-preps"], "n_clicks")]
    )
    def all_tissue_preps_selected(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_TISSUE_PREPS]

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
