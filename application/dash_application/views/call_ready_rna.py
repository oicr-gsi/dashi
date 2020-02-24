from collections import defaultdict
import logging

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State

import gsiqcetl.column
from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.plot_builder import GraphTitles as gt
from ..utility.table_builder import table_tabs, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils

logger = logging.getLogger(__name__)

page_name = 'call-ready-rna'
title = "Call-Ready RNA-seq"

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
    'pf-cutoff',
    'rrna-contam-cutoff',

    # Graphs
    'graphs',

    # Tables
    'failed-samples',
    'data-table'
])

RNASEQQC2_COL = gsiqcetl.column.RnaSeqQc2MergedColumn
PINERY_COL = pinery.column.SampleProvenanceColumn


def dataversion():
    return DATAVERSION


special_cols = {
    "Total Reads (Passed Filter)": "Total reads passed filter",
    "Unique Reads (PF)": "Unique reads",
    "File SWID RNAseqQC": "File SWID RNAseqQC",
    "% rRNA Contamination": "Percent rRNA Contamination"
}

def get_merged_rna_data():
    """
    Join together the RNAseqQC and Pinery dataframes
    """
    # Sample metadata from Pinery
    pinery_samples = util.get_pinery_merged_samples()
    pinery_samples = util.filter_by_library_design(pinery_samples, util.rna_lib_designs)

    rna_df = util.get_rnaseqqc2_merged()
    rna_df = util.filter_by_library_design(rna_df, util.rna_lib_designs,
                                           RNASEQQC2_COL.LibraryDesign)

    rna_df[special_cols["Total Reads (Passed Filter)"]] = round(
        rna_df[RNASEQQC2_COL.TotalReads] / 1e6, 3)
    rna_df[special_cols["Unique Reads (PF)"]] = round(
        rna_df[RNASEQQC2_COL.UniqueReads] / rna_df[RNASEQQC2_COL.TotalReads], 3)
    rna_df[special_cols["% rRNA Contamination"]] = round(
        (rna_df[RNASEQQC2_COL.RRnaContaminationMapped] / rna_df[
            RNASEQQC2_COL.TotalReads]) * 100, 2)
    rna_df.rename(columns={RNASEQQC2_COL.FileSWID: special_cols["File "
                                                                     "SWID RNAseqQC"]}, inplace=True)

    # Join RNAseqQC and Pinery data
    rna_df = util.df_with_pinery_samples_merged(rna_df, pinery_samples,
                                                util.rnaseqqc2_merged_columns)

    rna_df = util.remove_suffixed_columns(rna_df, '_q')  # Pinery duplicate columns

    return rna_df, util.cache.versions(["rnaseqqc2merged"])


(RNA_DF, DATAVERSION) = get_merged_rna_data()
rna_table_columns = RNA_DF.columns

initial = get_initial_call_ready_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = RNASEQQC2_COL.TotalReads
# Set initial values for graph cutoff lines
cutoff_pf_reads_label = "Total PF Reads minimum"
cutoff_pf_reads = "cutoff_pf_reads"
initial[cutoff_pf_reads] = 160
cutoff_rrna_contam_label = "rRNA Contamination maximum"
cutoff_rrna_contam = "cutoff_rrna_contam"
initial[cutoff_rrna_contam] = 50

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(RNA_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(RNA_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(RNA_DF, PINERY_COL.Institute)
ALL_TISSUE_MATERIALS = util.unique_set(RNA_DF, PINERY_COL.TissuePreparation)
ALL_LIBRARY_DESIGNS = util.unique_set(RNA_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_SAMPLE_TYPES = util.unique_set(RNA_DF, util.sample_type_col)
ALL_SAMPLES = util.unique_set(RNA_DF, PINERY_COL.RootSampleName)
ALL_REFERENCES = util.unique_set(RNA_DF, RNASEQQC2_COL.Reference)

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
RNA_DF = add_graphable_cols(RNA_DF, initial, shape_colour.items_for_df(), None, True)


def total_reads_subplot(df, graph_params):
    graph_title = gt.TOTAL_READS
    y_label = gt.TOTAL_READS_Y
    return CallReadySubplot(graph_title, y_label, df,
        special_cols["Total Reads (Passed Filter)"], graph_params,
        [(cutoff_pf_reads_label, initial[cutoff_pf_reads])], showlegend=True)


def unique_reads_subplot(df, graph_params):
    graph_title = gt.UNIQUE_READS
    y_label = gt.PCT
    return CallReadySubplot(graph_title, y_label, df,
       special_cols["Unique Reads (PF)"], graph_params)


def five_to_three_subplot(df, graph_params):
    graph_title = gt.FIVE_TO_THREE
    y_label = gt.RATIO
    return CallReadySubplot(graph_title, y_label, df,
       RNASEQQC2_COL.MetricsMedian5PrimeTo3PrimeBias, graph_params)


def correct_read_strand_subplot(df, graph_params):
    graph_title = gt.CORRECT_READ_STRAND
    y_label = gt.PCT
    return CallReadySubplot(graph_title, y_label, df,
        RNASEQQC2_COL.MetricsPercentCorrectStrandReads, graph_params)


def coding_subplot(df, graph_params):
    graph_title = gt.CODING
    y_label = gt.PCT
    return CallReadySubplot(graph_title, y_label, df,
        RNASEQQC2_COL.MetricsPercentCodingBases, graph_params)


def rrna_contam_subplot(df, graph_params):
    graph_title = gt.RRNA_CONTAM
    y_label = gt.PCT
    return CallReadySubplot(graph_title, y_label, df,
        special_cols["% rRNA Contamination"], graph_params,
        [(cutoff_rrna_contam_label, graph_params[cutoff_rrna_contam])])


graph_funcs = [
    total_reads_subplot,
    unique_reads_subplot,
    five_to_three_subplot,
    correct_read_strand_subplot,
    coding_subplot,
    rrna_contam_subplot,
]


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)

    df = reshape_call_ready_df(RNA_DF, initial["projects"], initial["references"],
                               initial["tissue_materials"], initial["sample_types"],
                               initial["first_sort"], initial["second_sort"],
                               initial["colour_by"], initial["shape_by"],
                               shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("File a ticket",
                                          ids['jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title))]),
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
                    html.Button("Update", id=ids["update-button-top"], className="update-button"),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_projects(ids["all-projects"],
                                                  ids["projects-list"],
                                                  ALL_PROJECTS),
                    sidebar_utils.select_reference(ids["all-references"],
                                                   ids["references-list"],
                                                   ALL_REFERENCES),
                    sidebar_utils.select_tissue_materials(ids["all-tissue-materials"],
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
                                                        {"label":"Total Reads",
                                                         "value":
                                                             RNASEQQC2_COL.TotalReads},
                                                        {"label": "5 to 3 Prime Bias",
                                                         "value":
                                                             RNASEQQC2_COL.MetricsMedian5PrimeTo3PrimeBias},
                                                        {"label": "% Correct Read Strand",
                                                         "value":
                                                          RNASEQQC2_COL.MetricsPercentCorrectStrandReads},
                                                        {"label": "% Coding",
                                                         "value":
                                                             RNASEQQC2_COL.MetricsPercentCodingBases},
                                                        {"label": "% rRNA Contamination",
                                                         "value": special_cols["% rRNA Contamination"]}
                                                     ]),

                    sidebar_utils.select_colour_by(ids["colour-by"],
                                                   shape_colour.dropdown(),
                                                   initial["colour_by"], True),

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
                    sidebar_utils.cutoff_input("{} (*10^6)".format(cutoff_pf_reads_label),
                                               ids["pf-cutoff"], initial[cutoff_pf_reads]),
                    sidebar_utils.cutoff_input(cutoff_rrna_contam_label, ids["rrna-contam-cutoff"],
                                               initial[cutoff_rrna_contam]),

                    html.Br(),
                    html.Button("Update", id=ids["update-button-bottom"], className="update-button")
                ]),

                # Graphs + Tables tabs
                html.Div(className="nine columns", 
                children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(label="Graphs",
                        children=[
                            generate_graphs(ids["graphs"], df, initial,
                                            graph_funcs)
                        ]),
                        # Tables tab
                        core.Tab(label="Tables",
                        children=[
                            table_tabs(
                                ids["failed-samples"],
                                ids["data-table"],
                                df,
                                rna_table_columns,
                                [
                                    (cutoff_pf_reads_label, special_cols["Total Reads (Passed Filter)"],
                                    initial[cutoff_pf_reads],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_rrna_contam_label, special_cols["% rRNA Contamination"],
                                    initial[cutoff_rrna_contam],
                                    (lambda row, col, cutoff: row[col] > cutoff)),
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
            State(ids["pf-cutoff"], "value"),
            State(ids["rrna-contam-cutoff"], "value"),
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
                       total_reads_cutoff,
                       rrna_contam_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = reshape_call_ready_df(RNA_DF, projects, references, tissue_materials,
                                   sample_types, first_sort, second_sort,
                                   colour_by, shape_by,
                                   shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            cutoff_pf_reads: total_reads_cutoff,
            cutoff_rrna_contam: rrna_contam_cutoff
        }

        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_pf_reads_label, special_cols["Total Reads (Passed Filter)"], total_reads_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_rrna_contam_label, special_cols["% rRNA Contamination"], rrna_contam_cutoff,
             (lambda row, col, cutoff: row[col] > cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.RootSampleName)

        return [
            update_graphs(df, graph_params, graph_funcs),
            failure_columns,
            failure_df.to_dict("records"),
            df.to_dict("records", into=defaultdict(list)),
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
