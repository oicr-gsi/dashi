from collections import defaultdict
import logging

import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State

import gsiqcetl.column
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
        "jira-issue-button",
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
		"graphs",

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
    pinery_samples = util.get_pinery_merged_samples()
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
    callability_df[special_cols["Percent Callability"]] = round(
        callability_df[CALL_COL.Callability]* 100.0, 3)
    bamqc3_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc3_df[BAMQC_COL.TotalReads] / 1e6, 3)
    bamqc3_df[special_cols["Unique Reads (Passed Filter)"]] = (1 - (bamqc3_df[BAMQC_COL.NonPrimaryReads] /
        bamqc3_df[BAMQC_COL.TotalReads])) * 100
    ichorcna_df.rename(columns={ICHOR_COL.FileSWID: special_cols["File SWID ichorCNA"]}, inplace=True)
    callability_df.rename(columns = {CALL_COL.FileSWID: special_cols["File SWID MutectCallability"]},
        inplace = True)
    bamqc3_df.rename(columns = {BAMQC_COL.FileSWID: special_cols["File SWID BamQC3"]}, inplace=True)

    # Join IchorCNA and Callability data
    wgs_df = ichorcna_df.merge(
        callability_df,
        how="outer",
        left_on=util.ichorcna_merged_columns,
        right_on=util.callability_merged_columns,
        suffixes=('', '_x')
    )

    # Join BamQC3 and IchorCNA+Pinery data
    wgs_df = wgs_df.merge(
			bamqc3_df,
			how="left",
			left_on=util.ichorcna_merged_columns,
			right_on = util.bamqc3_merged_columns,
            suffixes=('', '_y')
		)

    # Join QC data and Pinery data
    wgs_df = util.df_with_pinery_samples_merged(wgs_df, pinery_samples, util.ichorcna_merged_columns)

    wgs_df = util.remove_suffixed_columns(wgs_df, '_q')  # Pinery duplicate columns
    wgs_df = util.remove_suffixed_columns(wgs_df, '_x')  # Callability duplicate columns
    wgs_df = util.remove_suffixed_columns(wgs_df, '_y')  # BamQC3 duplicate columns

    return wgs_df, util.cache.versions(["ichorcnamerged", "mutectcallability", "bamqc3merged"])

# Make the WGS dataframe
(WGS_DF, DATAVERSION) = get_merged_wgs_data()
wgs_table_columns = WGS_DF.columns

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
cutoff_callability_label = "Callability minimum"
cutoff_callability = "cutoff_callability"
initial[cutoff_callability] = 50
cutoff_insert_mean_label = "Insert Mean minimum"
cutoff_insert_mean = "cutoff_insert_mean"
initial[cutoff_insert_mean] = 150
cutoff_duplicate_rate_label = "Duplication (%) maximum"
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
ALL_SAMPLE_TYPES = util.unique_set(WGS_DF, util.sample_type_col)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "tissue_preps": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_TISSUE_PREPS, "all_tissue_preps"),
    "sample_types": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_SAMPLE_TYPES, "all_sample_types")
}

shape_colour = ColourShapeCallReady(ALL_PROJECTS, ALL_LIBRARY_DESIGNS, ALL_INSTITUTES, ALL_SAMPLE_TYPES, ALL_TISSUE_PREPS)
WGS_DF = add_graphable_cols(WGS_DF, initial, shape_colour.items_for_df(), None, True)


def generate_total_reads(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Total Reads (Passed Filter)"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_pf_reads_normal_label, graph_params[cutoff_pf_reads_normal]),
         (cutoff_pf_reads_tumour_label, graph_params[cutoff_pf_reads_tumour])],
        util.ml_col)


def generate_unique_reads(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Unique Reads (Passed Filter)"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_deduplicated_coverage(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[BAMQC_COL.CoverageDeduplicated],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_coverage_tumour_label, graph_params[cutoff_coverage_tumour]),
         (cutoff_coverage_normal_label, graph_params[cutoff_coverage_normal])],
        util.ml_col, showlegend=False)


def generate_callability(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Percent Callability"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_callability_label, graph_params[cutoff_callability])],
        util.ml_col, showlegend=False)


def generate_mean_insert_size(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[BAMQC_COL.InsertMean],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])],
        util.ml_col, showlegend=False)


def generate_duplicate_rate(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_duplicate_rate_label, graph_params[cutoff_duplicate_rate])],
        util.ml_col, showlegend=False)


def generate_purity(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[special_cols["Purity"]],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_ploidy(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[ICHOR_COL.Ploidy],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_unmapped_reads(df, graph_params):
    return generate_traces(df,
        lambda d: d[util.ml_col],
        lambda d: d[BAMQC_COL.UnmappedReads],
        graph_params["colour_by"], graph_params["shape_by"],
        graph_params["shownames_val"], [],
        util.ml_col, showlegend=False)


def generate_graphs(df, graph_params):
    """
    Subplots are necessary because of the WebGL contexts limit (GR-932).
    """
    graphs = [
        (generate_total_reads, "Total Reads (Passed Filter)", "# PF Reads x "
                                                              "10^6"),
        (generate_unique_reads,
         "🚧  Unique Reads (Passed Filter) -- DATA MAY BE "
         "SUSPECT 🚧", "%"),
        (generate_deduplicated_coverage, "Deduplicated Coverage", ""),
        (generate_callability, "Callability (14x/18x)", "%"),
        (generate_mean_insert_size, "Mean Insert Size", "Base Pairs"),
        (generate_duplicate_rate, "Duplicate Rate", "%"),
        (generate_purity, "Purity", "%"),
        (generate_ploidy, "Ploidy", ""),
        (generate_unmapped_reads, "Unmapped Reads", "Read Counts")
    ]
    return generate_subplot(
        df, graph_params,
        [graph[0] for graph in graphs],
        [graph[1] for graph in graphs],
        [graph[2] for graph in graphs]
    )


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # no queries apply here...yet

    df = reshape_call_ready_df(WGS_DF, initial["projects"],
        initial["tissue_preps"], initial["sample_types"],
        initial["first_sort"], initial["second_sort"], initial["colour_by"],
        initial["shape_by"], shape_colour.items_for_df(), [])

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
                    sidebar_utils.select_library_designs(
                        ids["all-library-designs"], ids["library-designs-list"],
                        ALL_LIBRARY_DESIGNS),
                    sidebar_utils.select_tissue_prep(
                        ids["all-tissue-preps"], ids["tissue-preps-list"],
                        ALL_TISSUE_PREPS),
                    sidebar_utils.select_sample_type(
                        ids["all-sample-types"], ids["sample-types-list"],
                        ALL_SAMPLE_TYPES),
                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(ids["first-sort"],
                        initial["first_sort"], shape_colour.dropdown()),

                    sidebar_utils.select_second_sort(ids["second-sort"],
                        initial["second_sort"],
                        [
                            {"label": "Total Reads",
                            "value": BAMQC_COL.TotalReads},
                            {"label": "Unique Reads",
                            "value": special_cols["Unique Reads (Passed Filter)"]},
                            {"label": "Callability",
                            "value": CALL_COL.Callability},
                            {"label": "Purity",
                            "value": special_cols["Purity"]},
                            {"label": "Ploidy",
                            "value": ICHOR_COL.Ploidy}
                        ]),
                    
                    sidebar_utils.select_colour_by(ids["colour-by"],
                        shape_colour.dropdown(), initial["colour_by"], True),

                    sidebar_utils.select_shape_by(ids["shape-by"],
                        shape_colour.dropdown(), initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                      []),

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

                # Graphs + Tables tabs
                html.Div(className="seven columns", 
                children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(label="Graphs",
                        children=[
                            core.Graph(
                                id=ids["unique-reads"],
                                figure=generate_unique_reads(df, initial)
                            ),
                            core.Graph(
                                id=ids["total-reads"],
                                figure=generate_total_reads(
                                    df, util.ml_col,
                                    special_cols["Total Reads (Passed Filter)"],
                                    initial["colour_by"], initial["shape_by"],
                                    initial["shownames_val"],
                                    [(cutoff_pf_reads_tumour_label, initial[cutoff_pf_reads_tumour]),
                                    (cutoff_pf_reads_normal_label, initial[cutoff_pf_reads_normal])]
                                )
                            ),
                            core.Graph(
                                id=ids["mean-coverage"],
                                figure=generate_deduplicated_coverage(df, initial)
                            ),
                            core.Graph(
                                id=ids["callability"],
                                figure=generate_callability(df, initial)
                            ),
                            core.Graph(
                                id=ids["mean-insert"],
                                figure=generate_mean_insert_size(df, initial)
                            ),
                            core.Graph(
                                id=ids["duplicate-rate"],
                                figure=generate_duplicate_rate(df, initial)
                            ),
                            core.Graph(
                                id=ids["purity"],
                                figure=generate_purity(df, initial)
                            ),
                            core.Graph(
                                id=ids["ploidy"],
                                figure=generate_ploidy(df, initial)
                            ),
                            core.Graph(
                                id=ids["unmapped-reads"],
                                figure=generate_unmapped_reads(df, initial)
                            )
                        ]),
                        # Tables tab
                        core.Tab(label="Tables",
                        children=[
                            table_tabs(
                                ids["failed-samples"],
                                ids["data-table"],
                                df,
                                wgs_table_columns,
                                [
                                    (cutoff_pf_reads_tumour_label, special_cols["Total Reads (Passed Filter)"],
                                    initial[cutoff_pf_reads_tumour],
                                    (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
                                    (cutoff_pf_reads_normal_label, special_cols["Total Reads (Passed Filter)"],
                                    initial[cutoff_pf_reads_normal],
                                    (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
                                    (cutoff_coverage_tumour_label, BAMQC_COL.CoverageDeduplicated,
                                    initial[cutoff_coverage_tumour],
                                    (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
                                    (cutoff_coverage_normal_label, BAMQC_COL.CoverageDeduplicated,
                                    initial[cutoff_coverage_normal],
                                    (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
                                    (cutoff_callability_label, special_cols["Percent Callability"],
                                    initial[cutoff_callability],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_insert_mean_label, BAMQC_COL.InsertMean, initial[cutoff_insert_mean],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
                                    initial[cutoff_duplicate_rate], (lambda row, col, cutoff: row[col] > cutoff)),
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
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
            Output(ids["search-sample"], "options")
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
                       tissue_preps,
                       sample_types,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       show_names,
                       search_sample,
                       pf_reads_tumour_cutoff,
                       pf_reads_normal_cutoff,
                       coverage_tumour_cutoff,
                       coverage_normal_cutoff,
                       callability_cutoff,
                       insert_mean_cutoff,
                       duplicate_rate_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = reshape_call_ready_df(WGS_DF, projects, tissue_preps, sample_types, first_sort,
                second_sort, colour_by, shape_by, shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            cutoff_pf_reads_tumour: pf_reads_tumour_cutoff,
            cutoff_pf_reads_normal: pf_reads_normal_cutoff,
            cutoff_coverage_tumour: coverage_tumour_cutoff,
            cutoff_coverage_normal: coverage_normal_cutoff,
            cutoff_callability: callability_cutoff,
            cutoff_insert_mean: insert_mean_cutoff,
            cutoff_duplicate_rate: duplicate_rate_cutoff,
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_pf_reads_tumour_label, special_cols["Total Reads (Passed Filter)"],
             pf_reads_tumour_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_pf_reads_normal_label, special_cols["Total Reads (Passed Filter)"],
             pf_reads_normal_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
            (cutoff_coverage_tumour_label, BAMQC_COL.CoverageDeduplicated,
             coverage_tumour_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff and util.is_tumour(row))),
            (cutoff_coverage_normal_label, BAMQC_COL.CoverageDeduplicated,
             coverage_normal_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff and util.is_normal(row))),
            (cutoff_callability_label, special_cols["Percent Callability"], callability_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_insert_mean_label, BAMQC_COL.InsertMean, insert_mean_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_duplicate_rate_label, BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
             duplicate_rate_cutoff, (lambda row, col, cutoff: row[col] > cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.RootSampleName)

        return [
            generate_all_subplots(df, graph_params),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=dd),
            [{'label': x, 'value': x} for x in new_search_sample],
        ]


    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]


    @dash_app.callback(
        Output(ids['tissue-preps-list'], 'value'),
        [Input(ids['all-tissue-preps'], 'n_clicks')]
    )
    def all_tissue_preps_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_TISSUE_PREPS]


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

    @dash_app.callback(
        [
            Output(ids["colour-by"], "value"),
            Output(ids["colour-by"], "disabled"),
        ],
        [Input(ids["first-sort"], "value")]
    )
    def pin_colour_to_first_sort(first_sort):
        return [first_sort, True]
