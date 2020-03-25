from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs, cutoff_table_data_ius
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from gsiqcetl.column import RnaSeqQcColumn as RnaColumn, FastqcColumn
import pinery
import logging

logger = logging.getLogger(__name__)

""" Set up elements needed for page """
page_name = "single-lane-rna"
title = "Single-Lane RNA-seq"

ids = init_ids([
    # Buttons
    "jira-issue-with-runs-button",
    "general-jira-issue-button",
    "update-button",
    "approve-run-button",

    # Sidebar controls
    "all-runs",
    "run-id-list",
    "all-instruments",
    "instruments-list",
    "all-projects",
    "projects-list",
    "all-kits",
    "kits-list",
    "all-library-designs",
    "library-designs-list",
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "search-sample",
    "show-data-labels",
    "show-all-data-labels",
    "rrna-contamination-cutoff",
    "passed-filter-reads-cutoff",
    "date-range",

    # Graphs
    "total-reads",
    "unique-reads",
    "5-to-3-prime-bias",
    "correct-read-strand",
    "coding",
    "rrna-contam",
    "dv200",
    "rin",

    "failed-samples",
    "data-table",
])

RNA_COL = RnaColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "Total Reads PassedFilter",
    "Percent Uniq Reads": "Percent Unique Reads",
    "Percent Correct Strand Reads": "Percent Correct Strand Reads",
    "Percent Coding": "Percent Coding",
}

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
    special_cols["Total Reads (Passed Filter)"],
    special_cols["Percent Uniq Reads"],
    special_cols["Percent Correct Strand Reads"],
    special_cols["Percent Coding"],
]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.RIN, PINERY_COL.DV200,
    PINERY_COL.ExternalName, PINERY_COL.GroupID, PINERY_COL.TissueOrigin,
    PINERY_COL.TissueType, PINERY_COL.Institute, INSTRUMENT_COLS.ModelName
]
rnaseqqc_table_columns = [*first_col_set, *RNA_COL.values(), *later_col_set]


initial = get_initial_single_lane_values()
# Set additional initial values for dropdown menus
initial["second_sort"] = RNA_COL.TotalReads
# Set initial values for graph cutoff lines
cutoff_pf_reads_label = "Total PF Reads minimum"
cutoff_pf_reads = "cutoff_pf_reads"
initial[cutoff_pf_reads] = 0.01
cutoff_rrna_label = "% rRNA contamination maximum"
cutoff_rrna = "cutoff_rrna"
initial[cutoff_rrna] = 50


def get_rna_data():
    """
    Join together all the dataframes needed for graphing:
      * RNA-SeqQC (where most of the graphed QC data comes from)
      * Pinery (sample information)
      * Instruments (to allow filtering by instrument model)
      * Runs (needed to join Pinery to Instruments)
    """
    # Get the RNA-SeqQC data
    # NB: have to go two layers down to get the actual cache:
    #  * QCETLCache(): returns an object of all caches
    #  * QCETLCache().rnaseqqc: returns the items associated with the
    #  rnaseqqc cache
    #  * QCETLCache().rnaseqqc.rnaseqqc: returns the DataFrame/cache named
    #  "rnaseqqc" within the rnaseqqc cache (as some caches like bcl2fastq
    #  contain multiple DataFrame/caches)
    rna_df = util.get_rnaseqqc()

    # RNA-SeqQC does not correctly report total reads :(
    # Use FastQC (summing R1 and R2) to get machine produced total reads
    # `groupby` groups the fastqc files for each sample
    # For each grouped sample, the Total Sequences are summed
    # The result is a Series, converted to a DataFrame
    # The indexes are the groupby values and are reset to allow for merging
    fq_total_reads = util.get_fastqc().groupby(
        [FastqcColumn.Run, FastqcColumn.Lane, FastqcColumn.Barcodes]
    )[FastqcColumn.TotalSequences].sum().to_frame().reset_index()

    rna_df = rna_df.merge(
        fq_total_reads,
        how="left",
        left_on=util.rnaseqqc_ius_columns,
        right_on=util.fastqc_ius_columns,
        suffixes=('', '_fastqc')
    )

    # Calculate percent uniq reads column
    rna_df[special_cols["Percent Uniq Reads"]] = round(
        (rna_df[RNA_COL.UniqReads] / rna_df[RNA_COL.TotalReads]) * 100, 1)
    # Use FastQC derived Total Reads
    rna_df[special_cols["Total Reads (Passed Filter)"]] = round(
        rna_df[FastqcColumn.TotalSequences] / 1e6, 3)
    rna_df[special_cols["Percent Correct Strand Reads"]] = round(
        rna_df[RNA_COL.ProportionCorrectStrandReads] * 100, 3)
    rna_df[special_cols["Percent Coding"]] = round(
        rna_df[RNA_COL.ProportionCodingBases] * 100, 3)

    # Pull in sample metadata from Pinery
    pinery_samples = util.get_pinery_samples()
    # Filter the Pinery samples for only RNA samples.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   util.rna_lib_designs)

    # Join RNAseqQc and Pinery data
    rna_df = util.df_with_pinery_samples_ius(rna_df, pinery_samples,
                                         util.rnaseqqc_ius_columns)

    # Join RNAseqQc and instrument model
    rna_df = util.df_with_instrument_model(rna_df, PINERY_COL.SequencerRunName)

    return rna_df, util.cache.versions(["rnaseqqc"])


# Make the RNA dataframe
(RNA_DF, DATAVERSION) = get_rna_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(RNA_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(RNA_DF, PINERY_COL.PrepKit)
ILLUMINA_INSTRUMENT_MODELS = list(util.get_illumina_instruments(RNA_DF))
ALL_TISSUE_MATERIALS = util.unique_set(RNA_DF, PINERY_COL.TissuePreparation)
ALL_LIBRARY_DESIGNS = util.unique_set(RNA_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_RUNS = util.unique_set(RNA_DF, PINERY_COL.SequencerRunName, True)  # reverse the list
ALL_SAMPLE_TYPES = util.unique_set(RNA_DF, util.sample_type_col)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
}

shape_colour = ColourShapeSingleLane(ALL_PROJECTS, ALL_RUNS, ALL_KITS,
                                     ALL_TISSUE_MATERIALS, ALL_LIBRARY_DESIGNS)

# Add shape, colour, and size cols to RNA dataframe
RNA_DF = add_graphable_cols(RNA_DF, initial, shape_colour.items_for_df())


def generate_unique_reads(df, graph_params):
    return generate(
        "Unique Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Uniq Reads"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_five_to_three(df, graph_params):
    fig = generate(
        "5 to 3 Prime Bias",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.Median5Primeto3PrimeBias],
        "Log Ratio",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )
    fig.update_layout(yaxis_type="log")
    return fig


def generate_correct_read_strand(df, graph_params):
    return generate(
        "Correct Strand Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Correct Strand Reads"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_coding(df, graph_params):
    return generate(
        "Coding (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Coding"]],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_rrna_contam(df, graph_params):
    return generate(
        "rRNA Contamination (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.rRNAContaminationreadsaligned],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_rrna_label, graph_params[cutoff_rrna])]
    )


def generate_dv200(df, graph_params):
    return generate(
        "DV200 (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[PINERY_COL.DV200],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_rin(df, graph_params):
    return generate(
        "RIN",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[PINERY_COL.RIN],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )

def dataversion():
    return DATAVERSION


# Layout elements
def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # intial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters
    #    will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown

    df = reshape_single_lane_df(RNA_DF, initial["runs"], initial["instruments"],
                                initial["projects"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
    html.Div(className="body", children=[
        html.Div(className="row jira-buttons", children=[
            sidebar_utils.jira_button("File a ticket",
                                      ids['general-jira-issue-button'],
                                      {"display": "inline-block"},
                                      sidebar_utils.construct_jira_link([], title)),
            sidebar_utils.jira_button("File a ticket about these runs",
                                      ids['jira-issue-with-runs-button'],
                                      {"display": "none"}, "")]),
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button'], className="update-button"),
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
                                              ALL_PROJECTS),

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
                sidebar_utils.select_first_sort(ids["first-sort"],
                                                initial["first_sort"]),

                sidebar_utils.select_second_sort(
                    ids["second-sort"],
                    initial["second_sort"],
                    [
                        {"label": "Total Reads",
                         "value": RNA_COL.TotalReads},
                        {"label": "Unique Reads",
                         "value": special_cols["Percent Uniq Reads"]},
                        {"label": "5Prime to 3Prime Bias",
                         "value": RNA_COL.Median5Primeto3PrimeBias},
                        {"label": "Correct Read Strand",
                         "value": RNA_COL.CorrectStrandReads},
                        {"label": "Coding",
                         "value": RNA_COL.ProportionCodingBases},
                        {"label": "rRNA Contamination",
                         "value": RNA_COL.rRNAContaminationreadsaligned},
                        {"label": "DV200",
                         "value": PINERY_COL.DV200},
                        {"label": "RIN",
                         "value": PINERY_COL.RIN}
                    ]
                ),

                sidebar_utils.select_colour_by(ids["colour-by"],
                                               shape_colour.dropdown(),
                                               initial["colour_by"]),

                sidebar_utils.select_shape_by(ids["shape-by"],
                                              shape_colour.dropdown(),
                                              initial["shape_by"]),

                sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                      []),

                sidebar_utils.show_data_labels_input_single_lane(ids["show-data-labels"],
                                                     initial["shownames_val"],
                                                     "ALL LABELS",
                                                     ids["show-all-data-labels"]),

                sidebar_utils.hr(),

                # Cutoffs
                sidebar_utils.total_reads_cutoff_input(
                    ids["passed-filter-reads-cutoff"], initial[cutoff_pf_reads]),
                sidebar_utils.cutoff_input(
                    cutoff_rrna_label,
                    ids["rrna-contamination-cutoff"], initial[cutoff_rrna]),
            ]),

		        # Graphs + Tables tabs
                html.Div(className="seven columns", 
                children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(label="Graphs",
                        children=[
                            core.Graph(
                                id=ids["total-reads"],
                                figure=generate_total_reads(
                                    df,
                                    PINERY_COL.SampleName,
                                    special_cols["Total Reads (Passed Filter)"],
                                    initial["colour_by"],
                                    initial["shape_by"],
                                    initial["shownames_val"],
                                    [(cutoff_pf_reads_label, initial[cutoff_pf_reads])])
                            ),
                            core.Graph(
                                id=ids["unique-reads"],
                                figure=generate_unique_reads(df, initial)
                            ),
                            core.Graph(
                                id=ids["5-to-3-prime-bias"],
                                figure=generate_five_to_three(df,
                                                            initial)
                            ),
                            core.Graph(
                                id=ids["correct-read-strand"],
                                figure=generate_correct_read_strand(df,
                                                                    initial)
                            ),
                            core.Graph(
                                id=ids["coding"],
                                figure=generate_coding(df, initial)
                            ),
                            core.Graph(
                                id=ids["rrna-contam"],
                                figure=generate_rrna_contam(df, initial)
                            ),
                            core.Graph(
                                id=ids["dv200"],
                                figure=generate_dv200(df, initial)
                            ),
                            core.Graph(
                                id=ids["rin"],
                                figure=generate_rin(df, initial)
                            ),
                        ]),
                        # Tables tab
                        core.Tab(label="Tables",
                        children=[
                            table_tabs(
                                ids["failed-samples"],
                                ids["data-table"],
                                df,
                                rnaseqqc_table_columns,
                                [
                                    (cutoff_pf_reads_label,
                                    special_cols["Total Reads (Passed Filter)"], initial[cutoff_pf_reads],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_rrna_label,
                                    RNA_COL.rRNAContaminationreadsaligned, initial[cutoff_rrna],
                                    (lambda row, col, cutoff: row[col] > cutoff))
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
            Output(ids["total-reads"], "figure"),
            Output(ids["unique-reads"], "figure"),
            Output(ids["5-to-3-prime-bias"], "figure"),
            Output(ids["correct-read-strand"], "figure"),
            Output(ids["coding"], "figure"),
            Output(ids["rrna-contam"], "figure"),
            Output(ids["dv200"], "figure"),
            Output(ids["rin"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids["data-table"], "data"),
            Output(ids["search-sample"], "options"),
            Output(ids["jira-issue-with-runs-button"], "href"),
            Output(ids["jira-issue-with-runs-button"], "style"),
        ],
        [
            Input(ids["update-button"], "n_clicks")
        ],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['instruments-list'], 'value'),
            State(ids['projects-list'], 'value'),
            State(ids['kits-list'], 'value'),
            State(ids['library-designs-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['search-sample'], 'value'),
            State(ids['show-data-labels'], 'value'),
            State(ids['passed-filter-reads-cutoff'], 'value'),
            State(ids['rrna-contamination-cutoff'], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date'),
            State('url', 'search'),
        ]
    )
    def update_pressed(click,
                       runs,
                       instruments,
                       projects,
                       kits,
                       library_designs,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       searchsample,
                       show_names,
                       total_reads_cutoff,
                       rrna_cutoff,
                       start_date,
                       end_date,
                       search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = reshape_single_lane_df(RNA_DF, runs, instruments, projects, kits, library_designs,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        (approve_run_href, approve_run_style) = sidebar_utils.approve_run_url(runs)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            cutoff_rrna: rrna_cutoff,
            cutoff_pf_reads: total_reads_cutoff 
        }

        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data_ius(df, [
            (cutoff_pf_reads_label, special_cols["Total Reads (Passed Filter)"], total_reads_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff)),
            (cutoff_rrna_label, RNA_COL.rRNAContaminationreadsaligned, rrna_cutoff,
             (lambda row, col, cutoff: row[col] > cutoff)),
        ])

        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        (jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)

        return [
            approve_run_href,
            approve_run_style,
            generate_total_reads(
                df, PINERY_COL.SampleName,
                special_cols["Total Reads (Passed Filter)"], colour_by,
                shape_by, show_names, [(cutoff_pf_reads_label, total_reads_cutoff)]),
            generate_unique_reads(df, graph_params),
            generate_five_to_three(df, graph_params),
            generate_correct_read_strand(df, graph_params),
            generate_coding(df, graph_params),
            generate_rrna_contam(df, graph_params),
            generate_dv200(df, graph_params),
            generate_rin(df, graph_params),
            failure_columns,
            failure_df.to_dict('records'),
            df.to_dict("records", into=dd),
            [{'label': x, 'value': x} for x in new_search_sample],
            jira_href,
            jira_style
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
