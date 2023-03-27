from collections import defaultdict
import logging

from dash import html
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs_call_ready, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils

logger = logging.getLogger(__name__)

page_name = 'call-ready-rna'
title = "Call-Ready RNA-seq"

ids = init_ids([
    # Buttons
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
    'insert-mean-cutoff',
    'clusters-per-sample-cutoff',
    'percent-mapped-to-coding-cutoff',
    'rrna-contam-cutoff',

    # Graphs
    "graphs",

    # Tables
    'failed-samples',
    'all-samples',
    'data-table',
    'failed-count',
    'all-count',
    'data-count'
])

RNASEQQC2_COL = gsiqcetl.column.RnaSeqQc2MergedColumn
PINERY_COL = pinery.column.SampleProvenanceColumn


def dataversion():
    return DATAVERSION


special_cols = {
    # WARNING: Unmapped reads and non-primary reads are filtered out during BAM
    # merging. Do not include any graphs based on those metrics
    "File SWID RNAseqQC": "File SWID RNAseqQC",
    "% rRNA Contamination": "Percent rRNA Contamination",
    "Pipeline Filtered Clusters": "Pipeline Filtered Clusters",
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

    rna_df[special_cols["Pipeline Filtered Clusters"]] = round(
        rna_df[RNASEQQC2_COL.TotalClusters] / 1e6, 3)
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
rna_table_columns = list(RNA_DF.columns.values)
rna_curated_columns = [
    special_cols["Pipeline Filtered Clusters"], 
    RNASEQQC2_COL.InsertMean,
    RNASEQQC2_COL.MetricsMedian5PrimeTo3PrimeBias,
    RNASEQQC2_COL.MetricsPercentCorrectStrandReads,
    RNASEQQC2_COL.MetricsPercentCodingBases,
    special_cols["% rRNA Contamination"]
]

initial = get_initial_call_ready_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = special_cols["Pipeline Filtered Clusters"]
# Set initial values for graph cutoff lines
# Sourced from https://docs.google.com/document/d/1L056bikfIJDeX6Qzo6fwBb9j7A5NgC6o/edit
cutoff_rrna_contam_label = sidebar_utils.rrna_contamination_cutoff_label
initial["cutoff_rrna_contam"] = 35
cutoff_clusters_per_sample_label = sidebar_utils.clusters_per_sample_cutoff_label
initial["cutoff_clusters_per_sample"] = 80
cutoff_percent_mapped_to_coding_label = "% Mapped to Coding"
initial["cutoff_percent_mapped_to_coding"] = 5
cutoff_insert_mean_label = "Insert Size Mean + Intron"
initial["cutoff_insert_mean"] = 150

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(RNA_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(RNA_DF, PINERY_COL.PrepKit)
ALL_INSTITUTES = util.unique_set(RNA_DF, PINERY_COL.Institute)
ALL_TISSUE_MATERIALS = util.unique_set(RNA_DF, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(RNA_DF, PINERY_COL.TissueOrigin)
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
    ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN, ALL_REFERENCES
)
RNA_DF = add_graphable_cols(
    RNA_DF, initial, shape_colour.items_for_df(), None, REPORT_TYPE["Call-Ready"]
)

SORT_BY = shape_colour.dropdown() + [
    {"label":"Pipeline Filtered Clusters",
     "value": special_cols["Pipeline Filtered Clusters"]},
    {"label": "5 to 3 Prime Bias",
     "value": RNASEQQC2_COL.MetricsMedian5PrimeTo3PrimeBias},
    {"label": "% Correct Read Strand",
     "value": RNASEQQC2_COL.MetricsPercentCorrectStrandReads},
    {"label": "% Coding",
     "value": RNASEQQC2_COL.MetricsPercentCodingBases},
    {"label": "% rRNA Contamination",
     "value": special_cols["% rRNA Contamination"]},
    {"label": "Merged Lane",
     "value": util.ml_col}
]

def generate_total_clusters(df, graph_params):
    return CallReadySubplot(
        "Pipeline Filtered Clusters",
        df,
        lambda d: d[special_cols["Pipeline Filtered Clusters"]],
        "# PF Clusters X 10^6",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_clusters_per_sample_label, graph_params["cutoff_clusters_per_sample"])],
    )

def generate_mean_insert_size(df, graph_params):
    return CallReadySubplot(
        "Mean Insert Size + Intron",
        df,
        lambda d: d[RNASEQQC2_COL.InsertMean],
        "Mean Insert Size + Intron",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_insert_mean_label, graph_params["cutoff_insert_mean"])]
    )

def generate_five_to_three(df, graph_params):
    return CallReadySubplot(
        "5 to 3 Prime Bias", 
        df,
        lambda d: d[RNASEQQC2_COL.MetricsMedian5PrimeTo3PrimeBias],
        "Log Ratio",
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],
        log_y=True
    )


def generate_correct_read_strand(df, graph_params):
    return CallReadySubplot(
        "🚧 Correct Read Strand (%) -- DATA MAY BE SUSPECT 🚧", 
        df,
        lambda d: d[RNASEQQC2_COL.MetricsPercentCorrectStrandReads],
        "%",
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_coding(df, graph_params):
    return CallReadySubplot(
        "Coding (%)", 
        df,
        lambda d: d[RNASEQQC2_COL.MetricsPercentCodingBases],
        "%", 
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_percent_mapped_to_coding_label, graph_params["cutoff_percent_mapped_to_coding"])],
    )


def generate_rrna_contam(df, graph_params):
    return CallReadySubplot(
        "rRNA Contamination (%)", 
        df,
        lambda d: d[special_cols["% rRNA Contamination"]],
        "%", 
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_rrna_contam_label, graph_params["cutoff_rrna_contam"])],
    )


GRAPHS = [
    generate_total_clusters,
    generate_mean_insert_size,
    generate_five_to_three,
    generate_correct_read_strand,
    generate_coding,
    generate_rrna_contam,
]


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]
    elif "req_start" in query and query["req_start"]:
        initial["projects"] = ALL_PROJECTS
        query["req_projects"] = ALL_PROJECTS  # fill in the projects dropdown

    df = reshape_call_ready_df(RNA_DF, initial["projects"], initial["references"],
                               initial["tissue_materials"], initial["sample_types"],
                               initial["first_sort"], initial["second_sort"],
                               initial["colour_by"], initial["shape_by"],
                               shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
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
                    sidebar_utils.select_tissue_materials(ids["all-tissue-materials"],
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

                    sidebar_utils.highlight_samples_input(ids["search-sample"],
                                                          ALL_SAMPLES),

                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(ids['search-sample-ext'],
                                                          None),

                    sidebar_utils.show_data_labels_input_call_ready(ids["show-data-labels"],
                                                                    initial["shownames_val"],
                                                                    "ALL LABELS",
                                                                    ids["show-all-data-labels"]),
                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input(cutoff_insert_mean_label, ids["insert-mean-cutoff"],
                        initial["cutoff_insert_mean"]),
                    sidebar_utils.cutoff_input(cutoff_clusters_per_sample_label, ids["clusters-per-sample-cutoff"],
                        initial["cutoff_clusters_per_sample"]),
                    sidebar_utils.cutoff_input(cutoff_rrna_contam_label, ids["rrna-contam-cutoff"],
                        initial["cutoff_rrna_contam"]),
                    sidebar_utils.cutoff_input(cutoff_percent_mapped_to_coding_label,
                        ids["percent-mapped-to-coding-cutoff"], initial["cutoff_percent_mapped_to_coding"]),

                    html.Br(),
                    html.Button("Update", id=ids["update-button-bottom"], className="update-button")
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
                                ids["all-samples"],
                                ids["data-table"],
                                ids["failed-count"],
                                ids['all-count'],
                                ids["data-count"],
                                df,
                                rna_curated_columns,
                                rna_table_columns,
                                [
                                    (cutoff_insert_mean_label, RNASEQQC2_COL.InsertMean,
                                    initial["cutoff_insert_mean"],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_clusters_per_sample_label, special_cols["Pipeline Filtered Clusters"],
                                    initial["cutoff_clusters_per_sample"],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_rrna_contam_label, special_cols["% rRNA Contamination"],
                                    initial["cutoff_rrna_contam"],
                                    (lambda row, col, cutoff: row[col] > cutoff)),
                                    (cutoff_percent_mapped_to_coding_label, RNASEQQC2_COL.MetricsPercentCodingBases,
                                    initial["cutoff_percent_mapped_to_coding"],
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
            Output(ids["graphs"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["all-samples"], "data"),
            Output(ids["data-table"], "data"),
            Output(ids["failed-count"], "children"),
            Output(ids["all-count"], "children"),
            Output(ids["data-count"], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids["search-sample-ext"], "options"),
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
            State(ids["search-sample-ext"], "value"),
            State(ids["insert-mean-cutoff"], "value"),
            State(ids["clusters-per-sample-cutoff"], "value"),
            State(ids["rrna-contam-cutoff"], "value"),
            State(ids["percent-mapped-to-coding-cutoff"], "value"),
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
                       insert_mean_cutoff,
                       clusters_per_sample_cutoff,
                       rrna_contam_cutoff,
                       percent_mapped_to_coding_cutoff,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if search_sample and searchsampleext:
            search_sample += searchsampleext
        elif not search_sample and searchsampleext:
            search_sample = searchsampleext
        df = reshape_call_ready_df(RNA_DF, projects, references, tissue_materials,
                                   sample_types, first_sort, second_sort,
                                   colour_by, shape_by,
                                   shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_insert_mean": insert_mean_cutoff,
            "cutoff_clusters_per_sample": clusters_per_sample_cutoff,
            "cutoff_rrna_contam": rrna_contam_cutoff,
            "cutoff_percent_mapped_to_coding": percent_mapped_to_coding_cutoff,
        }

        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_insert_mean_label, RNASEQQC2_COL.InsertMean, insert_mean_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_clusters_per_sample_label, special_cols["Pipeline Filtered Clusters"], clusters_per_sample_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_rrna_contam_label, special_cols["% rRNA Contamination"], rrna_contam_cutoff,
             (lambda row, col, cutoff: row[col] > cutoff)),
            (cutoff_percent_mapped_to_coding_label, RNASEQQC2_COL.MetricsPercentCodingBases, percent_mapped_to_coding_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.RootSampleName)

        return [
            generate_subplot_from_func(df, graph_params, GRAPHS),
            failure_columns,
            failure_df.to_dict("records"),
            df[rna_curated_columns].to_dict("records",into=defaultdict(list)),
            df[rna_table_columns].to_dict("records", into=defaultdict(list)),
            "Rows: {0}".format(len(failure_df.index)),
            "Rows: {0}".format(len(df.index)),
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
