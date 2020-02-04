from collections import defaultdict
import logging
import json

import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd

import gsiqcetl.column
import pinery
from ..dash_id import init_ids

from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils, log_utils

logger = logging.getLogger(__name__)

""" Set up elements needed for page """
page_name = "call-ready-wgs"
title = "Call-Ready WGS"

ids = init_ids([
        # Buttons
        "update-button",

        # Sidebar controls
        "all-library-designs",
        "library-designs-list",
        "all-projects",
        "projects-list",
        "all-institutes",
        "institutes-list",
        "all-tissue-preps",
        "tissue-preps-list",
        "all-sample-types",
        "sample-types-list",
        "first-sort",
        "second-sort",
        "colour-by",
        "shape-by",
        "search-sample",
        "show-data-labels",
        "show-all-data-labels",
        "cutoff-pf-tumour",
        "cutoff-pf-normal",
        "cutoff-coverage-tumour",
        "cutoff-coverage-normal",
        "cutoff-callability",
        "cutoff-mean-insert",
        "cutoff-duplicate-rate",

		# Graphs
		"total-reads",
		"unique-reads",
		"mean-coverage",
		"callability",
		"mean-insert",
		"duplicate-rate",
		"purity",
		"ploidy",
		"unmapped-reads",

		# Tables
		"failed-samples",
		"data-table",
])

BAMQC_COL = gsiqcetl.column.BamQc3MergedColumn
ICHOR_COL = gsiqcetl.column.IchorCnaMergedColumn
CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
PINERY_COL = pinery.column.SampleProvenanceColumn


def dataversion():
    return DATAVERSION


special_cols = {
    "Total Reads (Passed Filter)": "total reads passed filter",
    "Unique Reads (Passed Filter)": "percent unique reads",
    "Unmapped Reads": "percent unmapped reads",
    "Purity": "percent purity",
    "Percent Callability": "percent callability",
    "File SWID MutectCallability": "File SWID MutectCallability",
    "File SWID ichorCNA": "File SWID ichorCNA",
    "File SWID BamQC3": "File SWID BamQC3",
}
wgs_table_columns = [*BAMQC_COL.values(), *ICHOR_COL.values(), *CALL_COL.values(), *special_cols.values()]

def get_merged_wgs_data():
    """
    Join together all the dataframes needed for graphing:
      * BamQC (where most of the graphed QC data comes from)
      * ichorCNA (where the remainder of the graphed QC data comes from)
      * Pinery (sample information)
      * Instruments (to allow filtering by instrument model)
      * Runs (needed to join Pinery to Instruments)
    """
    # Pull in sample metadata from Pinery.
    pinery_samples = util.get_pinery_merged_samples(False) # TODO: remove the "False" when we have real data
    # Filter the Pinery samples for WG samples and others which will have BAM files generated.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   util.wgs_lib_designs)
																					
    ichorcna_df = util.get_ichorcna_merged()
    ichorcna_df = util.filter_by_library_design(ichorcna_df, util.wgs_lib_designs, ICHOR_COL.LibraryDesign)
    callability_df = util.get_mutect_callability()
    callability_df = util.filter_by_library_design(callability_df, util.wgs_lib_designs, CALL_COL.LibraryDesign)
    bamqc3_df = util.get_bamqc3_merged()

    ichorcna_df[special_cols["Purity"]] = round(
        ichorcna_df[ICHOR_COL.TumorFraction]* 100.0, 3)
    ichorcna_df.rename(columns={ICHOR_COL.FileSWID: special_cols["File SWID ichorCNA"]}, inplace=True)
    callability_df[special_cols["Percent Callability"]] = round(
        callability_df[CALL_COL.Callability]* 100.0, 3)
    callability_df.rename(columns = {CALL_COL.FileSWID: special_cols["File SWID MutectCallability"]},
        inplace = True)
    bamqc3_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalReads] / 1e6, 3)
    bamqc3_df[special_cols["Unique Reads (Passed Filter)"]] = (1 - (bamqc3_df[BAMQC_COL.NonPrimaryReads] /
        bamqc3_df[BAMQC_COL.TotalReads])) * 100
    bamqc3_df.rename(columns = {BAMQC_COL.FileSWID: special_cols["File SWID BamQC3"]}, inplace=True)

    # Join IchorCNA and Callability data
    wgs_df = ichorcna_df.merge(
        callability_df,
        how = "outer",
        left_on = util.ichorcna_merged_columns,
        right_on=util.callability_merged_columns
    )

    # Join QC data and Pinery data
    wgs_df = util.df_with_pinery_samples_merged(wgs_df, pinery_samples, util.ichorcna_merged_columns)
      
    # Join BamQC3 and IchorCNA+Pinery data
    wgs_df = wgs_df.merge(
			bamqc3_df,
			how="left",
			left_on=util.pinery_merged_columns,
			right_on=util.bamqc3_merged_columns
		)

    # bamqc3 unique_reads: % unique = 1 - NonPrimaryReads/TotalReads

    return wgs_df, util.cache.versions(["ichorcnamerged", "mutectcallability"])

# Make the WGS dataframe
(WGS_DF, DATAVERSION) = get_merged_wgs_data()

initial = get_initial_call_ready_values()

# Set additional initial values for dropdown menus
# TODO: revert back to total reads
#initial["second_sort"] = BAMQC_COL.TotalReads
initial["second_sort"] = CALL_COL.Callability
# Set initial values for graph cutoff lines
cutoff_pf_reads_tumour_label = "Total PF Reads (Tumour) minimum"
cutoff_pf_reads_tumour = "cutoff_pf_reads_tumour"
initial[cutoff_pf_reads_tumour] = 148
cutoff_pf_reads_normal_label = "Total PF Reads (Normal) minimum"
cutoff_pf_reads_normal = "cutoff_pf_reads_normal"
initial[cutoff_pf_reads_normal] = 44
cutoff_callability_label = "Callability minimum"
cutoff_callability = "cutoff_callability"
initial[cutoff_callability] = 50
cutoff_insert_mean_label = "Insert Mean minimum"
cutoff_insert_mean = "cutoff_insert_mean"
initial[cutoff_insert_mean] = 150
cutoff_duplicate_rate_label = "Duplicate Rate maximum"
cutoff_duplicate_rate = "cutoff_duplicate_rate"
initial[cutoff_duplicate_rate] = 50
cutoff_coverage_tumour_label = "Coverage (Tumour) minimum"
cutoff_coverage_tumour = "cutoff_coverage_tumour"
initial[cutoff_coverage_tumour] = 80
cutoff_coverage_normal_label = "Coverage (Normal) minimum"
cutoff_coverage_normal = "cutoff_coverage_normal"
initial[cutoff_coverage_normal] = 30

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(WGS_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(WGS_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(WGS_DF, PINERY_COL.Institute)
ALL_TISSUE_PREPS = util.unique_set(WGS_DF, PINERY_COL.TissuePreparation)
ALL_LIBRARY_DESIGNS = util.unique_set(WGS_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_SAMPLES = util.unique_set(WGS_DF, PINERY_COL.RootSampleName)
ALL_SAMPLE_TYPES = util.unique_set(WGS_DF, util.sample_type_col)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
}

shape_colour = ColourShapeCallReady(ALL_PROJECTS, ALL_KITS, ALL_LIBRARY_DESIGNS, ALL_INSTITUTES, ALL_SAMPLE_TYPES)
WGS_DF = add_graphable_cols(WGS_DF, initial, shape_colour.items_for_df(), None, True)


# N.B. The keys in this object must match the argument names for
# the `update_pressed` function.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS,
        "all_projects"),
  #  "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
  #  "institutes": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_INSTITUTES,
  #      "all_institutes"),
  #  "tissue_prep": lambda selected: log_utils.collapse_if_all_selected(selected,
  #      ALL_TISSUE_PREPS, "all_tissue_preps"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected,
        ALL_LIBRARY_DESIGNS, "all_library_designs"),
  #  "sample_types": lambda selected: log_utils.collapse_if_all_selected(selected,
  #      ALL_SAMPLE_TYPES, "all_sample_types"),
}

def generate_unique_reads(df, graph_params):
    return generate(
        "Unique Reads (Passed Filter)", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[special_cols["Unique Reads (Passed Filter)"]],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        PINERY_COL.RootSampleName)


def generate_mean_coverage(df, graph_params):
    # TODO: should display two cutoffs: cutoff_coverage_tumour, cutoff_coverage_normal 
    return "https://jira.oicr.on.ca/browse/GR-848?focusedCommentId=160788&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-160788"


def generate_callability(df, graph_params):
    return generate(
        "Callability (14x/18x)", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[special_cols["Percent Callability"]],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_callability_label, graph_params[cutoff_callability])],
        PINERY_COL.RootSampleName)


def generate_mean_insert_size(df, graph_params):
    return generate(
        "Mean Insert Size", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[BAMQC_COL.InsertMean],
        "Base Pairs", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])],
        PINERY_COL.RootSampleName)


def generate_duplicate_rate(df, graph_params):
    return generate(
        "Duplicate Rate", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], graph_params["cutoff_duplicate_rate"],
        PINERY_COL.RootSampleName)


def generate_purity(df, graph_params):
    return generate(
        "Purity", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[special_cols["Purity"]],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        PINERY_COL.RootSampleName)


def generate_ploidy(df, graph_params):
    return generate(
        "Ploidy", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[ICHOR_COL.Ploidy],
        "", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        PINERY_COL.RootSampleName)


def generate_unmapped_reads(df, graph_params):
    return generate(
        "Unmapped Reads (%)", df,
        lambda d: d[PINERY_COL.RootSampleName],
        lambda d: d[BAMQC_COL.UnmappedReads],
        "%", graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        PINERY_COL.RootSampleName)


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # nothing applies here...yet

    df = reshape_call_ready_df(WGS_DF, initial["projects"], #initial["kits"],
        initial["library_designs"], #initial["institutes"], initial["sample_types"],
        initial["first_sort"], initial["second_sort"], initial["colour_by"],
        initial["shape_by"], shape_colour.items_for_df(), [])

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
                    sidebar_utils.select_library_designs(
                        ids["all-library-designs"], ids["library-designs-list"],
                        ALL_LIBRARY_DESIGNS),
                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(ids["first-sort"],
                        initial["first_sort"], shape_colour.dropdown()),

                    sidebar_utils.select_second_sort(ids["second-sort"],
                        initial["second_sort"],
                        [
                            #{"label": "Total Reads",
                            #"value": BAMQC_COL.TotalReads},
                            #{"label": "Unique Reads",
                            #"value": special_cols["unique_reads"]}
                            {"label": "Callability",
                            "value": CALL_COL.Callability},
                            {"label": "Purity",
                            "value": special_cols["Purity"]},
                            {"label": "Ploidy",
                            "value": ICHOR_COL.Ploidy}
                        ]),
                    
                    sidebar_utils.select_colour_by(ids["colour-by"],
                        shape_colour.dropdown(), initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids["shape-by"],
                        shape_colour.dropdown(), initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                      ALL_SAMPLES),

                    sidebar_utils.show_data_labels_input_call_ready(ids["show-data-labels"],
                                               initial["shownames_val"],
                                               "ALL LABELS",
                                               ids["show-all-data-labels"]),

                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_reads_tumour_label),
                        ids["cutoff-pf-tumour"], initial[cutoff_pf_reads_tumour]),
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_reads_normal_label),
                        ids["cutoff-pf-normal"], initial[cutoff_pf_reads_normal]),
                    sidebar_utils.cutoff_input(cutoff_coverage_tumour_label,
                        ids["cutoff-coverage-tumour"], initial[cutoff_coverage_tumour]),
                    sidebar_utils.cutoff_input(cutoff_coverage_normal_label,
                        ids["cutoff-coverage-normal"], initial[cutoff_coverage_normal]),
                    sidebar_utils.cutoff_input(cutoff_callability_label,
                        ids["cutoff-callability"], initial[cutoff_callability]),
                    sidebar_utils.cutoff_input(cutoff_insert_mean_label,
                        ids["cutoff-mean-insert"], initial[cutoff_insert_mean]),
                    sidebar_utils.cutoff_input(cutoff_duplicate_rate_label,
                        ids["cutoff-duplicate-rate"], initial[cutoff_duplicate_rate]),
                ]),

                html.Div(className="seven columns", children=[
                    # core.Graph(
                    #     id=ids["total-reads"],
                    #     figure=generate_total_reads(
                    #         df, PINERY_COL.RootSampleName,
                    #         special_cols["Total Reads (Passed Filter)"],
                    #         initial
                    #         # TODO: add initial_cutoff_pf_reads_tumour
                    #     )
                    # ),
                    # core.Graph(
                    #     id=ids["unique-reads"],
                    #     figure=generate_unique_reads(df, initial)
                    # ),
                    # core.Graph(
                    #     id=ids["mean-coverage"],
                    #     figure=generate_mean_coverage(df, initial)
                    # ),
                    core.Graph(
                        id=ids["callability"],
                        figure=generate_callability(df, initial)
                    ),
                    # core.Graph(
                    #     id=ids["mean-insert"],
                    #     figure=generate_mean_insert_size(df, initial)
                    # ),
                    # core.Graph(
                    #     id=ids["duplicate-rate"],
                    #     figure=generate_duplicate_rate(df, initial)
                    # ),
                    core.Graph(
                        id=ids["purity"],
                        figure=generate_purity(df, initial)
                    ),
                    core.Graph(
                        id=ids["ploidy"],
                        figure=generate_ploidy(df, initial)
                    ),
                    # core.Graph(
                    #     id=ids["unmapped-reads"],
                    #     figure=generate_unmapped_reads(df, initial)
                    # ),
                    
            ])
        ]),
        table_tabs(
            ids["failed-samples"],
            ids["data-table"],
            df,
            wgs_table_columns,
            [
                # TODO: add the tumour/normal cutoff differences for total PF reads
                # TODO: add the tumour/normal cutoff differences for coverage
                (cutoff_callability_label, special_cols["Percent Callability"],
                initial["cutoff_callability"], True),
                # (cutoff_insert_mean_label, BAMQC_COL.InsertMean,
                # initial["cutoff_insert_mean"], True),
                # (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
                # initial["cutoff_duplicate_rate"], False),

            ]
        )
    ])
])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            # Output(ids["total-reads"], "figure"),
            # Output(ids["unique-reads"], "figure"),
            # Output(ids["mean-coverage"], "figure"),
            Output(ids["callability"], "figure"),
            # Output(ids["mean-insert"], "figure"),
            # Output(ids["duplicate-rate"], "figure"),
            Output(ids["purity"], "figure"),
            Output(ids["ploidy"], "figure"),
            # Output(ids["unmapped-reads"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
        ],
        [Input(ids["update-button"], "n_clicks")],
        [
            State(ids["projects-list"], "value"),
            State(ids["library-designs-list"], "value"),
            State(ids["first-sort"], "value"),
            State(ids["second-sort"], "value"),
            State(ids["colour-by"], "value"),
            State(ids["shape-by"], "value"),
            State(ids["show-data-labels"], "value"),
            State(ids["search-sample"], "value"),
            State(ids["cutoff-pf-tumour"], "value"),
            State(ids["cutoff-pf-normal"], "value"),
            State(ids["cutoff-coverage-tumour"], "value"),
            State(ids["cutoff-coverage-normal"], "value"),
            State(ids["cutoff-callability"], "value"),
            State(ids["cutoff-mean-insert"], "value"),
            State(ids["cutoff-duplicate-rate"], "value"),
            State('url', 'search'),
        ]
    )
    def update_pressed(click,
                       projects,
                       library_designs,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       show_names,
                       search_sample,
                       cutoff_pf_reads_tumour,
                       cutoff_pf_reads_normal,
                       cutoff_coverage_tumour,
                       cutoff_coverage_normal,
                       cutoff_callability,
                       cutoff_mean_insert,
                       cutoff_duplicate_rate,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = reshape_call_ready_df(WGS_DF, projects, library_designs, first_sort,
                second_sort, colour_by, shape_by, shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            cutoff_pf_reads_tumour: cutoff_pf_reads_tumour,
            cutoff_pf_reads_normal: cutoff_pf_reads_normal,
            cutoff_coverage_tumour: cutoff_coverage_tumour,
            cutoff_coverage_normal: cutoff_coverage_normal,
            cutoff_callability: cutoff_callability,
            cutoff_mean_insert: cutoff_mean_insert,
            cutoff_duplicate_rate: cutoff_duplicate_rate
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            # TODO: add the tumour/normal cutoff differences for total PF reads
            # TODO: add the tumour/normal cutoff differences for coverage
            (cutoff_callability_label, special_cols["Percent Callability"],
            cutoff_callability, True),
            # (cutoff_insert_mean_label, BAMQC_COL.InsertMean,
            # initial_cutoff_insert_mean, True),
            # (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
            # initial_cutoff_duplicate_rate, False),

        ])

        return [
            # generate_total_reads(
            #     df, PINERY_COL.RootSampleName,
            #     special_cols["Total Reads (Passed Filter)"],
            #     colour_by, shape_by, show_names,
            #     cutoff_pf_reads_normal
            #     # TODO: add initial_cutoff_pf_reads_tumour
            # ),
            # generate_unique_reads(df, graph_params),
            # generate_mean_coverage(df, graph_params
            #     # TODO: add initial_cutoff_coverage_tumour
            # ),
            generate_callability(df, graph_params),
            # generate_mean_insert_size(df, graph_params),
            # generate_duplicate_rate(df, graph_params),
            generate_purity(df, graph_params),
            generate_ploidy(df, graph_params),
            # generate_unmapped_reads(df, graph_params),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=dd),
        ]


    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]


    @dash_app.callback(
        Output(ids['library-designs-list'], 'value'),
        [Input(ids['all-library-designs'], 'n_clicks')]
    )
    def all_library_designs_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_LIBRARY_DESIGNS]


    @dash_app.callback(
        Output(ids["show-data-labels"], "value"),
        [Input(ids["show-all-data-labels"], "n_clicks")],
        [State(ids["show-data-labels"], "options")]
    )
    def all_data_labels_requested(click, avail_options):
        sidebar_utils.update_only_if_clicked(click)
        return [x["value"] for x in avail_options]
