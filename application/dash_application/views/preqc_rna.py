import dash_html_components as html
import dash_core_components as core
import pandas as pd
from dash.dependencies import Input, Output, State
from pandas import DataFrame

from . import navbar
from ..dash_id import init_ids
from ..utility import df_manipulation as util
from ..plot_builder import get_shapes_for_values
import plotly.graph_objects as go
from gsiqcetl import QCETLCache
from gsiqcetl.column import RnaSeqQcColumn as RnaColumn
import pinery

""" Set up elements needed for page """
page_name = "preqc-rna"

ids = init_ids([
    # Buttons
    "update-button",
    "download-button",

    # Sidebar controls
    "run-id-list",
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
    "dv200",
    "rin"
])

RNA_COL = RnaColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "total_reads_pf",
    "Percent Uniq Reads": "pct_uniq_reads",
    "Project": "project",
    "Percent Correct Strand Reads": "pct_correct_strand_reads",
    "shape": "shape",
}

# Set points for graph cutoffs
graph_cutoffs = {
    "reads_per_start_point": 5,
    "rrna_contamination": 50,
    "pf_reads": 0.01
}


initial_colour_col = PINERY_COL.StudyTitle
initial_shape_col = PINERY_COL.PrepKit
initial_shapes = get_shapes_for_values(initial_shape_col)


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
    rna_df = QCETLCache().rnaseqqc.rnaseqqc
    # Cast the primary key/join columns to explicit types
    rna_df = util.df_with_normalized_ius_columns(rna_df, RNA_COL.Run,
                                                 RNA_COL.Lane, RNA_COL.Barcodes)

    # Calculate percent uniq reads column
    rna_df[special_cols["Percent Uniq Reads"]] = round(
        (rna_df[RNA_COL.UniqReads] / rna_df[RNA_COL.TotalReads]) * 100, 1)
    rna_df[special_cols["Total Reads (Passed Filter)"]] = round(
        rna_df[RNA_COL.TotalReads] / pow(10, 6), 3)
    rna_df[special_cols["Percent Correct Strand Reads"]] = round(
        rna_df[RNA_COL.CorrectStrandReads] * 100
    )

    # Pull in sample metadata from Pinery. Keep only the columns we care about
    pinery_samples = util.get_pinery_samples_from_active_projects()
    pinery_samples = pinery_samples[
        [
            "DV200", # FIXME
            PINERY_COL.IUSTag,
            PINERY_COL.LaneNumber,
            PINERY_COL.LibrarySourceTemplateType,
            PINERY_COL.PrepKit,
            "RIN", # FIXME
            PINERY_COL.SampleName,
            PINERY_COL.SequencerRunName,
            PINERY_COL.StudyTitle,
            PINERY_COL.TissueOrigin,
            PINERY_COL.TissuePreparation,
            PINERY_COL.TissueType,
            PINERY_COL.GroupID,
        ]
    ]
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
ALL_INSTRUMENT_MODELS = RNA_DF[INSTRUMENT_COLS.ModelName].sort_values().unique()
ALL_TISSUE_MATERIALS = RNA_DF[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = RNA_DF[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ALL_RUNS = RNA_DF[RNA_COL.Run].sort_values().unique()[::-1]  # reverse the list

shape_or_colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    PINERY_COL.SequencerRunName: ALL_RUNS,
    PINERY_COL.PrepKit: ALL_KITS,
    PINERY_COL.TissuePreparation: ALL_TISSUE_MATERIALS,
    PINERY_COL.LibrarySourceTemplateType: ALL_LIBRARY_DESIGNS
}


def fill_in_shape_col(df: DataFrame, shape_col: str):
    all_shapes = get_shapes_for_values(shape_or_colour_values[
                                           shape_col].tolist())
    # for each row,
    df[special_cols['shape']] = df.apply(lambda row: all_shapes.get(row[
        shape_col]), axis=1)
    return df


# Add shape col to RNA dataframe
RNA_DF = fill_in_shape_col(RNA_DF, initial_shape_col)


def scattergl(x_col, y_col, data, colour_val):
    return go.Scattergl(
        x=data[x_col],
        y=data[y_col],
        name="{} {}".format(colour_val[0], colour_val[1]),
        mode="markers",
        marker={
            "symbol": data[special_cols["shape"]]
        }
    )


def go_figure(traces, graph_title, y_title, xaxis=None, yaxis=None):
    x_axis = xaxis if xaxis else {
        "visible": False,
        "rangemode": "normal",
        "autorange": True
    }
    y_axis = yaxis if yaxis else {
        "title": {
            "text": y_title
        }
    }
    return go.Figure(
        data=traces,
        layout=go.Layout(
            title=graph_title,
            xaxis=x_axis,
            yaxis=y_axis
        )
    )


# Standard graph
def scatter_graph(df, colour_by, shape_by, x_col, y_col, graph_title, y_title):
    traces = []
    for colour_val, data in df.groupby([colour_by, shape_by]):
        traces.append(scattergl(x_col, y_col, data, colour_val))

    return go_figure(traces, graph_title, y_title)


def generate_total_reads(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        special_cols["Total Reads (Passed Filter)"],
        "Total Reads (Passed Filter)", "# Reads (10^6)")


def generate_unique_reads(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        special_cols["Percent Uniq Reads"],
        "Unique Reads (Passed Filter)", "Percent (%)")


def generate_reads_per_start_point(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        RNA_COL.ReadsPerStartPoint,
        "Reads Per Start Point", "")


def generate_five_to_three(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        RNA_COL.Median5Primeto3PrimeBias,
        "5 to 3 Prime Bias", "Ratio")


def generate_correct_read_strand(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        special_cols["Percent Correct Strand Reads"], "% Correct Strand Reads",
        "Percent (%)")


def generate_coding(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,  \
                           RNA_COL.ProportionCodingBases,
        "% Coding", "Percent (%)")


def generate_dv200(df, colour_by, shape_by):
    return scatter_graph(df, colour_by, shape_by, PINERY_COL.SampleName,
                         "DV200",
           "DV200", "DV200")


def generate_rin(df, colour_by, shape_by):
    return scatter_graph(df, colour_by, shape_by, PINERY_COL.SampleName,
                         "RIN", "RIN", "RIN")


# Layout elements
layout = core.Loading(fullscreen=True, type="cube", children=[
    html.Div(className="body", children=[
        navbar("Pre-RNA"),
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button']),
                html.Button('Download', id=ids['download-button']),
                html.Br(),

                html.Label([
                    "Run",
                    core.Dropdown(id=ids["run-id-list"],
                                  options=[
                                      {"label": run,
                                       "value": run} for run in ALL_RUNS
                                  ],
                                  value=[run for run in ALL_RUNS],
                                  multi=True
                                  )
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
                                  value=PINERY_COL.StudyTitle,
                                  searchable=True,
                                  clearable=False
                                  )
                ]),
                html.Br(),

                html.Label([
                    "Second Sort:",
                    core.Dropdown(id=ids["second-sort"],
                                  options=[
                                      {"label": "Project",
                                       "value": PINERY_COL.StudyTitle},
                                      {"label": "Run",
                                       "value": PINERY_COL.SequencerRunName},
                                      {"label": "Kit",
                                       "value": PINERY_COL.PrepKit},
                                      {"label": "Tissue Prep",
                                       "value": PINERY_COL.TissuePreparation},
                                      {
                                          "label": "Library Design",
                                          "value": PINERY_COL.LibrarySourceTemplateType},
                                  ],
                                  value=PINERY_COL.PrepKit,
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
                        value=graph_cutoffs[
                            "reads_per_start_point"]
                    )
                ]),
                html.Br(),

                html.Label([
                    "Ribosomal rRNA Contamination (%)",
                    core.Slider(
                        id=ids["rrna-contamination-slider"],
                        min=0,
                        max=100,
                        step=1,
                        marks={
                            0: "0",
                            10: "10",
                            20: "20",
                            30: "30",
                            40: "40",
                            50: "50",
                            60: "60",
                            70: "70",
                            80: "80",
                            90: "90",
                            100: "100"
                        },
                        tooltip="always_visible",
                        value=graph_cutoffs[
                            "rrna_contamination"]
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
                        value=graph_cutoffs["pf_reads"]
                    )
                ]),
                html.Br(),
            ]),

            html.Div(className="seven columns",  children=[
                 core.Graph(
                     id=ids["total-reads"],
                     figure=generate_total_reads(RNA_DF, initial_colour_col,
                                                 initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["unique-reads"],
                     figure=generate_unique_reads(RNA_DF, initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["reads-per-start-point"],
                     figure=generate_reads_per_start_point(
                         RNA_DF, initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["5-to-3-prime-bias"],
                     figure=generate_five_to_three(RNA_DF,
                                                   initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["correct-read-strand"],
                     figure=generate_correct_read_strand(RNA_DF,
                          initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["coding"],
                     figure=generate_coding(RNA_DF, initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["dv200"],
                     figure=generate_dv200(RNA_DF, initial_colour_col, initial_shape_col)
                 ),
                 core.Graph(
                     id=ids["rin"],
                     figure=generate_rin(RNA_DF, initial_colour_col, initial_shape_col)
                 ),
             ])

            # Add terminal output for failed samples

            # Add DataTable for all samples info
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
            Output(ids["dv200"], "figure"),
            Output(ids["rin"], "figure")
        ],
        [
            Input(ids["update-button"], "n_clicks")
        ],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
        ]
    )
    def update_pressed(click,
                       runs,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by):
        print("App initiated")  # TODO: delete me
        df = RNA_DF[RNA_DF[RNA_COL.Run].isin(runs)]
        sort_by = [first_sort, second_sort]
        df = df.sort_values(by=sort_by)
        df = fill_in_shape_col(df, shape_by)

        return [
            generate_total_reads(df, colour_by, shape_by),
            generate_unique_reads(df, colour_by, shape_by),
            generate_reads_per_start_point(df, colour_by, shape_by),
            generate_five_to_three(df, colour_by, shape_by),
            generate_correct_read_strand(df, colour_by, shape_by),
            generate_coding(df, colour_by, shape_by),
            generate_dv200(df, colour_by, shape_by),
            generate_rin(df, colour_by, shape_by),
        ]