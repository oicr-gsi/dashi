from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State
import pandas as pd

from . import navbar, footer
from ..dash_id import init_ids
from ..plot_builder import fill_in_colour_col, fill_in_shape_col, \
    fill_in_size_col, generate, generate_total_reads
from ..table_builder import table_tabs, cutoff_table_data
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from gsiqcetl.column import RnaSeqQcColumn as RnaColumn
import pinery

""" Set up elements needed for page """
page_name = "preqc-rna"

ids = init_ids([
    # Buttons
    "update-button",

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
    "show-names",
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
}

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
    special_cols["Total Reads (Passed Filter)"],
    special_cols["Percent Uniq Reads"],
    special_cols["Percent Correct Strand Reads"]
]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.RIN, PINERY_COL.DV200,
    PINERY_COL.ExternalName, PINERY_COL.GroupID, PINERY_COL.TissueOrigin,
    PINERY_COL.TissueType, PINERY_COL.Institute, INSTRUMENT_COLS.ModelName
]
rnaseqqc_table_columns = [*first_col_set, *RNA_COL.values(), *later_col_set]

# Set initial values for dropdown menus
initial_first_sort = PINERY_COL.StudyTitle
initial_second_sort = RNA_COL.TotalReads
initial_colour_col = PINERY_COL.StudyTitle
initial_shape_col = PINERY_COL.PrepKit
initial_shownames_val = 'none'

# Set initial points for graph cutoff lines
initial_cutoff_pf_reads = 0.01
initial_cutoff_rrna = 50

shape_or_colour_by = [
    {"label": "Project", "value": PINERY_COL.StudyTitle},
    {"label": "Run", "value": PINERY_COL.SequencerRunName},
    {"label": "Kit", "value": PINERY_COL.PrepKit},
    {"label": "Tissue Prep", "value": PINERY_COL.TissuePreparation},
    {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
]


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
    # Cast the primary key/join columns to explicit types
    rna_df = util.df_with_normalized_ius_columns(rna_df, RNA_COL.Run,
                                                 RNA_COL.Lane, RNA_COL.Barcodes)

    # Calculate percent uniq reads column
    rna_df[special_cols["Percent Uniq Reads"]] = round(
        (rna_df[RNA_COL.UniqReads] / rna_df[RNA_COL.TotalReads]) * 100, 1)
    rna_df[special_cols["Total Reads (Passed Filter)"]] = round(
        rna_df[RNA_COL.TotalReads] / 1e6, 3)
    rna_df[special_cols["Percent Correct Strand Reads"]] = round(
        (rna_df[RNA_COL.CorrectStrandReads] / rna_df[RNA_COL.TotalReads]) *
        100, 1
    )

    # Pull in sample metadata from Pinery
    pinery_samples = util.get_pinery_samples_from_active_projects()
    # Filter the Pinery samples for only RNA samples.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   ["MR", "SM", "TR", "WT"])

    # Join RNAseqQc and Pinery data
    rna_df = util.df_with_pinery_samples(rna_df, pinery_samples,
                                         util.rnaseqqc_ius_columns)

    # Join RNAseqQc and instrument model
    rna_df = util.df_with_instrument_model(rna_df, PINERY_COL.SequencerRunName)

    return rna_df


# Make the RNA dataframe
RNA_DF = get_rna_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = RNA_DF[PINERY_COL.StudyTitle].sort_values().unique()
ALL_KITS = RNA_DF[PINERY_COL.PrepKit].sort_values().unique()
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(RNA_DF)
ALL_TISSUE_MATERIALS = RNA_DF[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = RNA_DF[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ALL_RUNS = RNA_DF[RNA_COL.Run].sort_values().unique()[::-1]  # reverse the list
ALL_SAMPLES = RNA_DF[PINERY_COL.SampleName].sort_values().unique()

shape_or_colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    PINERY_COL.SequencerRunName: ALL_RUNS,
    PINERY_COL.PrepKit: ALL_KITS,
    PINERY_COL.TissuePreparation: ALL_TISSUE_MATERIALS,
    PINERY_COL.LibrarySourceTemplateType: ALL_LIBRARY_DESIGNS
}


# Add shape col to RNA dataframe
RNA_DF = fill_in_shape_col(RNA_DF, initial_shape_col, shape_or_colour_values)
RNA_DF = fill_in_colour_col(RNA_DF, initial_colour_col, shape_or_colour_values)
RNA_DF = fill_in_size_col(RNA_DF)
# Do initial sort before graphing
RNA_DF = RNA_DF.sort_values(by=[initial_first_sort, initial_second_sort])
EMPTY_RNA = pd.DataFrame(columns=RNA_DF.columns)


def generate_unique_reads(df, colour_by, shape_by, show_names):
    return generate(
        "Unique Passed Filter Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Uniq Reads"]],
        "%",
        colour_by,
        shape_by,
        show_names
    )


def generate_five_to_three(df, colour_by, shape_by, show_names):
    return generate(
        "5 to 3 Prime Bias",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.Median5Primeto3PrimeBias],
        "Ratio",
        colour_by,
        shape_by,
        show_names
    )


def generate_correct_read_strand(df, colour_by, shape_by, show_names):
    return generate(
        "Correct Strand Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Correct Strand Reads"]],
        "%",
        colour_by,
        shape_by,
        show_names
    )


def generate_coding(df, colour_by, shape_by, show_names):
    return generate(
        "Coding (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.ProportionCodingBases],
        "%",
        colour_by,
        shape_by,
        show_names
    )


def generate_rrna_contam(df, colour_by, shape_by, show_names, cutoff):
    return generate(
        "Ribosomal RNA (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.rRNAContaminationreadsaligned],
        "%",
        colour_by,
        shape_by,
        show_names,
        cutoff
    )


def generate_dv200(df, colour_by, shape_by, show_names):
    return generate(
        "DV200",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[PINERY_COL.DV200],
        "",
        colour_by,
        shape_by,
        show_names
    )


def generate_rin(df, colour_by, shape_by, show_names):
    return generate(
        "RIN",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[PINERY_COL.RIN],
        "",
        colour_by,
        shape_by,
        show_names
    )


# Layout elements
layout = core.Loading(fullscreen=True, type="dot", children=[
    html.Div(className="body", children=[
        navbar("Pre-RNA"),
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button']),
                html.Br(),
                html.Br(),

                # Filters
                sidebar_utils.select_runs(ids["all-runs"],
                                          ids["run-id-list"], ALL_RUNS),

                util.run_range_input(ids["date-range"]),

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
                                                initial_first_sort),

                sidebar_utils.select_second_sort(
                    ids["second-sort"],
                    initial_second_sort,
                    [
                        {"label": "Total Reads",
                         "value": RNA_COL.TotalReads},
                        {"label": "% Unique Reads",
                         "value": special_cols["Percent Uniq Reads"]},
                        {"label": "5Prime to 3Prime Bias",
                         "value": RNA_COL.Median5Primeto3PrimeBias},
                        {"label": "% Correct Read Strand",
                         "value": RNA_COL.CorrectStrandReads},
                        {"label": "% Coding",
                         "value": RNA_COL.ProportionCodingBases},
                        {"label": "% rRNA Contamination",
                         "value": RNA_COL.rRNAContaminationreadsaligned},
                        {"label": "DV200",
                         "value": PINERY_COL.DV200},
                        {"label": "RIN",
                         "value": PINERY_COL.RIN}
                    ]
                ),

                sidebar_utils.select_colour_by(ids["colour-by"],
                                               shape_or_colour_by,
                                               initial_colour_col),

                sidebar_utils.select_shape_by(ids["shape-by"],
                                              shape_or_colour_by,
                                              initial_shape_col),

                sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                      ALL_SAMPLES),

                sidebar_utils.show_names_input(ids["show-names"],
                                               initial_shownames_val),

                sidebar_utils.hr(),

                # Cutoffs
                sidebar_utils.total_reads_cutoff_input(
                    ids["passed-filter-reads-cutoff"], initial_cutoff_pf_reads),
                sidebar_utils.cutoff_input(
                    "% rRNA Contamination cutoff",
                    ids["rrna-contamination-cutoff"], initial_cutoff_rrna),
            ]),

            # Graphs
            html.Div(className="seven columns",  children=[
                 core.Graph(
                     id=ids["total-reads"],
                     figure=generate_total_reads(
                         EMPTY_RNA,
                         PINERY_COL.SampleName,
                         special_cols["Total Reads (Passed Filter)"],
                         initial_colour_col,
                         initial_shape_col,
                         initial_shownames_val,
                         initial_cutoff_pf_reads)
                 ),
                 core.Graph(
                     id=ids["unique-reads"],
                     figure=generate_unique_reads(EMPTY_RNA, initial_colour_col,
                                                  initial_shape_col,
                                                  initial_shownames_val)
                 ),
                 core.Graph(
                     id=ids["5-to-3-prime-bias"],
                     figure=generate_five_to_three(EMPTY_RNA,
                                                   initial_colour_col,
                                                   initial_shape_col,
                                                   initial_shownames_val)
                 ),
                 core.Graph(
                     id=ids["correct-read-strand"],
                     figure=generate_correct_read_strand(EMPTY_RNA,
                                                         initial_colour_col,
                                                         initial_shape_col,
                                                         initial_shownames_val)
                 ),
                 core.Graph(
                     id=ids["coding"],
                     figure=generate_coding(EMPTY_RNA, initial_colour_col,
                                            initial_shape_col,
                                            initial_shownames_val)
                 ),
                 core.Graph(
                     id=ids["rrna-contam"],
                     figure=generate_rrna_contam(EMPTY_RNA, initial_colour_col,
                                                 initial_shape_col,
                                                 initial_shownames_val,
                                                 initial_cutoff_rrna)
                 ),
                 core.Graph(
                     id=ids["dv200"],
                     figure=generate_dv200(EMPTY_RNA, initial_colour_col,
                                           initial_shape_col,
                                           initial_shownames_val)
                 ),
                 core.Graph(
                     id=ids["rin"],
                     figure=generate_rin(EMPTY_RNA, initial_colour_col,
                                         initial_shape_col,
                                         initial_shownames_val)
                 ),
             ]),

            # Tables
            table_tabs(
                ids["failed-samples"],
                ids["data-table"],
                EMPTY_RNA,
                rnaseqqc_table_columns,
                RNA_COL.TotalReads,
                [
                    ('Total Reads Cutoff',
                     special_cols["Total Reads (Passed Filter)"],
                     initial_cutoff_pf_reads, True),
                    ('% rRNA Contamination',
                     RNA_COL.rRNAContaminationreadsaligned,
                     initial_cutoff_rrna, True)
                ]
            )
        ]),
        footer()
    ])
])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
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
            State(ids['show-names'], 'value'),
            State(ids['passed-filter-reads-cutoff'], 'value'),
            State(ids['rrna-contamination-cutoff'], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date'),
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
                       end_date):
        if not runs and not instruments and not projects and not kits and not library_designs:
            df = EMPTY_RNA
        else:
            df = RNA_DF

        if runs:
            df = df[df[RNA_COL.Run].isin(runs)]
        if instruments:
            df = df[df[INSTRUMENT_COLS.ModelName].isin(instruments)]
        if projects:
            df = df[df[PINERY_COL.StudyTitle].isin(projects)]
        if kits:
            df = df[df[PINERY_COL.PrepKit].isin(kits)]
        if library_designs:
            df = df[df[PINERY_COL.LibrarySourceTemplateType].isin(
                library_designs)]
        df = df[df[RNA_COL.Run].isin(util.runs_in_range(start_date, end_date))]
        sort_by = [first_sort, second_sort]
        df = df.sort_values(by=sort_by)
        df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
        df = fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample)
        df = fill_in_size_col(df, searchsample)
        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data(df, [
            ('Total Reads Cutoff', special_cols["Total Reads (Passed Filter)"],
             total_reads_cutoff, True),
            ('% rRNA Contamination', RNA_COL.rRNAContaminationreadsaligned,
             rrna_cutoff, False),
        ])
        return [
            generate_total_reads(
                df, PINERY_COL.SampleName,
                special_cols["Total Reads (Passed Filter)"], colour_by,
                shape_by, show_names, total_reads_cutoff),
            generate_unique_reads(df, colour_by, shape_by, show_names),
            generate_five_to_three(df, colour_by, shape_by, show_names),
            generate_correct_read_strand(df, colour_by, shape_by, show_names),
            generate_coding(df, colour_by, shape_by, show_names),
            generate_rrna_contam(df, colour_by, shape_by, show_names, rrna_cutoff),
            generate_dv200(df, colour_by, shape_by, show_names),
            generate_rin(df, colour_by, shape_by, show_names),
            failure_columns,
            failure_df.to_dict('records'),
            df.to_dict("records", into=dd),
        ]
        
    @dash_app.callback(
        Output(ids['run-id-list'], 'value'),
        [Input(ids['all-runs'], 'n_clicks')]
    )
    def all_runs_requested(click):
        return [x for x in ALL_RUNS]

    @dash_app.callback(
        Output(ids['instruments-list'], 'value'),
        [Input(ids['all-instruments'], 'n_clicks')]
    )
    def all_instruments_requested(click):
        return [x for x in ILLUMINA_INSTRUMENT_MODELS]

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        return [x for x in ALL_PROJECTS]

    @dash_app.callback(
        Output(ids['kits-list'], 'value'),
        [Input(ids['all-kits'], 'n_clicks')]
    )
    def all_kits_requested(click):
        return [x for x in ALL_KITS]

    @dash_app.callback(
        Output(ids['library-designs-list'], 'value'),
        [Input(ids['all-library-designs'], 'n_clicks')]
    )
    def all_library_designs_requested(click):
        return [x for x in ALL_LIBRARY_DESIGNS]