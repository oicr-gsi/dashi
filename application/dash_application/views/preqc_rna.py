from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State
import pandas as pd

from . import navbar
from ..dash_id import init_ids
from ..utility import df_manipulation as util
from ..plot_builder import fill_in_colour_col, fill_in_shape_col, generate
from ..table_builder import build_table
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
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "reads-per-start-point-slider",
    "rrna-contamination-slider",
    "passed-filter-reads-slider",

    # Graphs
    "total-reads",
    "unique-reads",
    "reads-per-start-point",
    "5-to-3-prime-bias",
    "correct-read-strand",
    "coding",
    "rrna-contam",
    "dv200",
    "rin",

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

# Set initial points for graph cutoff lines
initial_cutoff_rpsp = 5
initial_cutoff_pf_reads = 0.01

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
        rna_df[RNA_COL.TotalReads] / pow(10, 6), 3)
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
ILLUMINA_INSTRUMENT_MODELS = RNA_DF.loc[RNA_DF[
    INSTRUMENT_COLS.Platform] == 'ILLUMINA'][
    INSTRUMENT_COLS.ModelName].sort_values().unique()
ALL_TISSUE_MATERIALS = RNA_DF[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = RNA_DF[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ALL_RUNS = RNA_DF[RNA_COL.Run].sort_values().unique()[::-1]  # reverse the list

shape_or_colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    RNA_COL.Run: ALL_RUNS,
    PINERY_COL.PrepKit: ALL_KITS,
    PINERY_COL.TissuePreparation: ALL_TISSUE_MATERIALS,
    PINERY_COL.LibrarySourceTemplateType: ALL_LIBRARY_DESIGNS
}


# Add shape col to RNA dataframe
RNA_DF = fill_in_shape_col(RNA_DF, initial_shape_col, shape_or_colour_values)
RNA_DF = fill_in_colour_col(RNA_DF, initial_colour_col, shape_or_colour_values)
# Do initial sort before graphing
RNA_DF = RNA_DF.sort_values(by=[initial_first_sort, initial_second_sort])
EMPTY_RNA = pd.DataFrame(columns=RNA_DF.columns)

def generate_total_reads(df, colour_by, shape_by, cutoff):
    return generate(
        "Total Reads (Passed Filter)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Total Reads (Passed Filter)"]],
        "# Reads (10^6)",
        colour_by,
        shape_by,
        "none",
        cutoff
    )


def generate_unique_reads(df, colour_by, shape_by):
    return generate(
        "Unique Reads (Passed Filter)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Uniq Reads"]],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_reads_per_start_point(df, colour_by, shape_by, cutoff):
    return generate(
        "Reads Per Start Point",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.ReadsPerStartPoint],
        "",
        colour_by,
        shape_by,
        "none",
        cutoff
    )


def generate_five_to_three(df, colour_by, shape_by):
    return generate(
        "5 to 3 Prime Bias",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.Median5Primeto3PrimeBias],
        "Ratio",
        colour_by,
        shape_by,
        "none"
    )


def generate_correct_read_strand(df, colour_by, shape_by):
    return generate(
        "% Correct Strand Reads",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Percent Correct Strand Reads"]],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_coding(df, colour_by, shape_by):
    return generate(
        "% Coding",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.ProportionCodingBases],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_rrna_contam(df, colour_by, shape_by):
    return generate(
        "% Ribosomal RNA",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[RNA_COL.rRNAContaminationreadsaligned],
        "Percent(%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_dv200(df, colour_by, shape_by):
    return generate(
        "DV200",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[PINERY_COL.DV200],
        "DV200",
        colour_by,
        shape_by,
        "none"
    )


def generate_rin(df, colour_by, shape_by):
    return generate(
        "RIN",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[PINERY_COL.RIN],
        "RIN",
        colour_by,
        shape_by,
        "none"
    )


# Layout elements
layout = core.Loading(fullscreen=True, type="cube", children=[
    html.Div(className="body", children=[
        navbar("Pre-RNA"),
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button']),
                html.Br(),
                html.Br(),
                core.Loading(type="circle", children=[
                    html.Button('Add All', id=ids["all-runs"],
                        className="inline"),
                    html.Label([
                        "Runs",
                        core.Dropdown(id=ids["run-id-list"],
                                      options=[
                                          {"label": run,
                                           "value": run} for run in ALL_RUNS
                                      ],
                                      multi=True)
                    ]),
                ]),
                core.Loading(type="circle", children=[
                    html.Button("All Instruments", id=ids["all-instruments"],
                                className="inline"),
                    html.Label([
                       "Instruments",
                        core.Dropdown(id=ids["instruments-list"],
                                      options=[
                                          {"label": instrument,
                                           "value": instrument} for instrument in
                                          ILLUMINA_INSTRUMENT_MODELS
                                      ],
                                      multi=True)
                        ]),
                ]),
                html.Br(),

                html.Label([
                    "First Sort:",
                    core.Dropdown(id=ids["first-sort"],
                                  options=[
                                      {"label": "Project",
                                       "value": PINERY_COL.StudyTitle},
                                      {"label": "Run",
                                       "value": RNA_COL.Run}
                                  ],
                                  value=initial_first_sort,
                                  searchable=True,
                                  clearable=False
                                  )
                ]),
                html.Br(),

                html.Label([
                    "Second Sort:",
                    core.Dropdown(id=ids["second-sort"],
                                  options=[
                                      {"label": "Total Reads",
                                       "value": RNA_COL.TotalReads},
                                      {"label": "% Unique Reads",
                                       "value": special_cols["Percent Uniq Reads"]},
                                      {"label": "Reads Per Start Point",
                                       "value": RNA_COL.ReadsPerStartPoint},
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
                                  ],
                                  value=initial_second_sort,
                                  searchable=True,
                                  clearable=False
                                  )
                ]),
                html.Br(),

                html.Label([
                    "Colour By:",
                    core.Dropdown(id=ids["colour-by"],
                                  options=shape_or_colour_by,
                                  value=initial_colour_col,
                                  searchable=False,
                                  clearable=False
                                  )
                ]),
                html.Br(),

                html.Label([
                    "Shape By:",
                    core.Dropdown(id=ids["shape-by"],
                                  options=shape_or_colour_by,
                                  value=initial_shape_col,
                                  searchable=False,
                                  clearable=False
                                  )
                ]),
                html.Br(),

                # TODO: add "Search Sample" input

                # TODO: add "Show Names" dropdown
                html.Label([
                    "Reads Per Start Point:",
                    core.Slider(
                        id=ids["reads-per-start-point-slider"],
                        min=0,
                        max=50,
                        step=1,
                        marks={
                            0: "0",
                            5: "5",
                            10: "10",
                            15: "15",
                            20: "20",
                            25: "25",
                            30: "30",
                            35: "35",
                            40: "40",
                            45: "45",
                            50: "50"
                        },
                        tooltip="always_visible",
                        value=initial_cutoff_rpsp
                    )
                ]),
                html.Br(),

                html.Label([
                    "Passed Filter Reads:",
                    core.Slider(
                        id=ids["passed-filter-reads-slider"],
                        min=0,
                        max=0.5,
                        step=0.025,
                        marks={
                            0: "0",
                            0.05: "0.05",
                            0.1: "0.1",
                            0.15: "0.15",
                            0.2: "0.2",
                            0.25: "0.25",
                            0.3: "0.3",
                            0.35: "0.35",
                            0.4: "0.4",
                            0.45: "0.45",
                            0.5: "0.5"
                        },
                        tooltip="always_visible",
                        value=initial_cutoff_pf_reads
                    )
                ]),
                html.Br(),
            ]),

            html.Div(className="seven columns",  children=[
                 core.Graph(
                     id=ids["total-reads"],
                     figure=generate_total_reads(EMPTY_RNA, initial_colour_col,
                                                 initial_shape_col,
                                                 initial_cutoff_pf_reads)
                 ),
                 core.Graph(
                     id=ids["unique-reads"],
                     figure=generate_unique_reads(EMPTY_RNA, initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["reads-per-start-point"],
                     figure=generate_reads_per_start_point(
                         EMPTY_RNA, initial_colour_col, initial_shape_col, initial_cutoff_rpsp)
                 ),
                 core.Graph(
                     id=ids["5-to-3-prime-bias"],
                     figure=generate_five_to_three(EMPTY_RNA,
                                                   initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["correct-read-strand"],
                     figure=generate_correct_read_strand(EMPTY_RNA,
                          initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["coding"],
                     figure=generate_coding(EMPTY_RNA, initial_colour_col, initial_shape_col)
                 ),
                core.Graph(
                    id=ids["rrna-contam"],
                    figure=generate_rrna_contam(EMPTY_RNA, initial_colour_col,
                                                initial_shape_col)
                ),
                 core.Graph(
                     id=ids["dv200"],
                     figure=generate_dv200(EMPTY_RNA, initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["rin"],
                     figure=generate_rin(EMPTY_RNA, initial_colour_col, initial_shape_col)
                 ),
             ]),

            # Add terminal output for failed samples

            # DataTable for all samples info
            html.Div(className="data-table",
                children=[
                    build_table(ids["data-table"], rnaseqqc_table_columns,
                                EMPTY_RNA, RNA_COL.TotalReads)
                ])
        ])
    ])
])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["total-reads"], "figure"),
            Output(ids["unique-reads"], "figure"),
            Output(ids["reads-per-start-point"], "figure"),
            Output(ids["5-to-3-prime-bias"], "figure"),
            Output(ids["correct-read-strand"], "figure"),
            Output(ids["coding"], "figure"),
            Output(ids["rrna-contam"], "figure"),
            Output(ids["dv200"], "figure"),
            Output(ids["rin"], "figure"),
            Output(ids["data-table"], "data"),
        ],
        [
            Input(ids["update-button"], "n_clicks")
        ],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['instruments-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['reads-per-start-point-slider'], 'value'),
            State(ids['passed-filter-reads-slider'], 'value'),
        ]
    )
    def update_pressed(click,
                       runs,
                       instruments,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       rpsp_cutoff,
                       total_reads_cutoff):
        if not runs and not instruments:
            df = EMPTY_RNA
        else:
            df = RNA_DF

        if runs:
            df = df[df[RNA_COL.Run].isin(runs)]
        if instruments:
            df = df[df[INSTRUMENT_COLS.ModelName].isin(instruments)]
        sort_by = [first_sort, second_sort]
        df = df.sort_values(by=sort_by)
        df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
        df = fill_in_colour_col(df, colour_by, shape_or_colour_values)
        dd = defaultdict(list)

        return [
            generate_total_reads(df, colour_by, shape_by, total_reads_cutoff),
            generate_unique_reads(df, colour_by, shape_by),
            generate_reads_per_start_point(df, colour_by, shape_by, rpsp_cutoff),
            generate_five_to_three(df, colour_by, shape_by),
            generate_correct_read_strand(df, colour_by, shape_by),
            generate_coding(df, colour_by, shape_by),
            generate_rrna_contam(df, colour_by, shape_by),
            generate_dv200(df, colour_by, shape_by),
            generate_rin(df, colour_by, shape_by),
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
