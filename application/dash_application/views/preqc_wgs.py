from collections import defaultdict

import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd

import gsiqcetl.column
import pinery
from gsiqcetl import QCETLCache
from . import navbar
from ..dash_id import init_ids
from ..plot_builder import terminal_output, fill_in_shape_col, fill_in_colour_col, generate
from ..table_builder import build_table
from ..utility import df_manipulation as util

""" Set up elements needed for page """
page_name = "preqc-wgs"

ids = init_ids([
    # Buttons
    "update-button",
    "all-runs",

    # Sidebar controls
    "run-id-list",
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "reads-per-start-point-slider",
    "insert-mean-slider",
    "passed-filter-reads-slider",

    # Graphs
    "total-reads",
    "mean-insert",
    "reads-per-start-point",
    "duplication",
    "purity",
    "ploidy",
    "unmapped-reads",
    "non-primary-reads",
    "on-target-reads",

    "terminal-output",
    "data-table",
])

BAMQC_COL = gsiqcetl.column.BamQc3Column
ICHOR_COL = gsiqcetl.column.IchorCnaColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "total_reads_pf",
    "Unmapped Reads": "unmapped_reads_pct",
    "Non-Primary Reads": "non_primary_reads_pct",
    "On-target Reads": "on_target_reads_pct",
    "Purity": "purity_pct",
    "Project": "project",
    "shape": "shape",
}

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
    special_cols["Total Reads (Passed Filter)"],
    special_cols["Unmapped Reads"],
    special_cols["Non-Primary Reads"],
    special_cols["On-target Reads"],
    special_cols["Purity"]
]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.ExternalName,
    PINERY_COL.GroupID, PINERY_COL.TissueOrigin, PINERY_COL.TissueType,
    PINERY_COL.Institute, INSTRUMENT_COLS.ModelName
]
wgs_table_columns = [*first_col_set, *BAMQC_COL.values(), *ICHOR_COL.values(), *later_col_set]

# Set initial values for dropdown menus
initial_first_sort = PINERY_COL.StudyTitle
initial_second_sort = BAMQC_COL.TotalReads
initial_colour_col = PINERY_COL.StudyTitle
initial_shape_col = PINERY_COL.PrepKit
initial_cutoff_pf_reads = 0.01
initial_cutoff_insert_mean = 150
initial_cutoff_rpsp = 5

shape_or_colour_by = [
    {"label": "Project", "value": PINERY_COL.StudyTitle},
    {"label": "Run", "value": PINERY_COL.SequencerRunName},
    {"label": "Kit", "value": PINERY_COL.PrepKit},
    {"label": "Tissue Prep", "value": PINERY_COL.TissuePreparation},
]


def get_wgs_data():
    """
    Join together all the dataframes needed for graphing:
      * BamQC (where most of the graphed QC data comes from)
      * Pinery (sample information)
      * Instruments (to allow filtering by instrument model)
      * Runs (needed to join Pinery to Instruments)
    """
    # Get the BamQC data
    cache = QCETLCache()

    ichorcna_df = cache.ichorcna.ichorcna[[ICHOR_COL.Run, ICHOR_COL.Lane, ICHOR_COL.Barcodes, ICHOR_COL.Ploidy, ICHOR_COL.TumorFraction]]
    bamqc_df = cache.bamqc3.bamqc3
    wgs_df = bamqc_df.merge(ichorcna_df,
                                       how="left",
                                       left_on=[BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes],
                                       right_on=[ICHOR_COL.Run, ICHOR_COL.Lane, ICHOR_COL.Barcodes])
    # Cast the primary key/join columns to explicit types
    wgs_df = util.df_with_normalized_ius_columns(
        wgs_df, BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes)

    # Calculate percent uniq reads column
    wgs_df[special_cols["Total Reads (Passed Filter)"]] = round(
        wgs_df[BAMQC_COL.TotalReads] / 1e6, 3)
    wgs_df[special_cols["Purity"]] = round(
        wgs_df[ICHOR_COL.TumorFraction] * 100.0, 3)
    wgs_df[special_cols["Unmapped Reads"]] = round(
        wgs_df[BAMQC_COL.UnmappedReads] * 100.0 /
        wgs_df[BAMQC_COL.TotalReads], 3)
    wgs_df[special_cols["Non-Primary Reads"]] = round(
        wgs_df[BAMQC_COL.NonPrimaryReads] * 100.0 /
        wgs_df[BAMQC_COL.TotalReads], 3)
    wgs_df[special_cols["On-target Reads"]] = round(
        wgs_df[BAMQC_COL.ReadsOnTarget] * 100.0 /
        wgs_df[BAMQC_COL.TotalReads], 3)

    # Pull in sample metadata from Pinery.
    pinery_samples = util.get_pinery_samples_from_active_projects()
    # Filter the Pinery samples for only WG samples.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   ["WG"])

    # Join BamQC and Pinery data
    wgs_df = util.df_with_pinery_samples(wgs_df, pinery_samples,
                                         util.bamqc_ius_columns)

    # Join BamQc and instrument model
    wgs_df = util.df_with_instrument_model(wgs_df, PINERY_COL.SequencerRunName)

    return wgs_df


# Make the WGS dataframe
WGS_DF = get_wgs_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = WGS_DF[PINERY_COL.StudyTitle].sort_values().unique()
ALL_KITS = WGS_DF[PINERY_COL.PrepKit].sort_values().unique()
ALL_INSTRUMENT_MODELS = WGS_DF[INSTRUMENT_COLS.ModelName].sort_values(
).unique()
ALL_TISSUE_MATERIALS = WGS_DF[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = WGS_DF[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ALL_RUNS = WGS_DF[BAMQC_COL.Run].sort_values().unique()[
           ::-1]  # reverse the list

shape_or_colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    PINERY_COL.SequencerRunName: ALL_RUNS,
    PINERY_COL.PrepKit: ALL_KITS,
    PINERY_COL.TissuePreparation: ALL_TISSUE_MATERIALS,
    PINERY_COL.LibrarySourceTemplateType: ALL_LIBRARY_DESIGNS
}

# Add shape col to WG dataframe
WGS_DF = fill_in_shape_col(WGS_DF, initial_shape_col, shape_or_colour_values)
WGS_DF = fill_in_colour_col(WGS_DF, initial_colour_col, shape_or_colour_values)

EMPTY_WGS = pd.DataFrame(columns=WGS_DF.columns)

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


def generate_mean_insert_size(df, colour_by, shape_by, cutoff):
    return generate(
        "Insert Mean",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.InsertMean],
        "Base Pairs",
        colour_by,
        shape_by,
        "none",
        cutoff
    )


def generate_reads_per_start_point(df, colour_by, shape_by, cutoff):
    return generate("Reads per Start Point",
                    df, lambda d: d[PINERY_COL.SampleName],
                    lambda d: d[BAMQC_COL.ReadsPerStartPoint],
                    "Reads", colour_by, shape_by, "none", cutoff)


def generate_duplication(df, colour_by, shape_by):
    return generate(
        "Duplication",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_unmapped_reads(df, colour_by, shape_by):
    return generate(
        "Unmapped Reads",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Unmapped Reads"]],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_non_primary(df, colour_by, shape_by):
    return generate(
        "Non-Primary Reads",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Non-Primary Reads"]],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_on_target_reads(df, colour_by, shape_by):
    return generate(
        "On-target Reads",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["On-target Reads"]],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_purity(df, colour_by, shape_by):
    return generate(
        "Purity",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Purity"]],
        "Percent (%)",
        colour_by,
        shape_by,
        "none"
    )


def generate_ploidy(df, colour_by, shape_by):
    return generate(
        "Ploidy",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[ICHOR_COL.Ploidy],
        "",
        colour_by,
        shape_by,
        "none"
    )


def generate_terminal_output(data, initial_cutoff_rpsp, initial_cutoff_insert_mean, initial_cutoff_pf_reads):
    return terminal_output(data, [
        ('rpsp', BAMQC_COL.ReadsPerStartPoint, initial_cutoff_rpsp),
        ('insert_mean', BAMQC_COL.InsertMean, initial_cutoff_insert_mean),
        ('reads_pf', special_cols["Total Reads (Passed Filter)"], initial_cutoff_pf_reads),
    ])


# Layout elements
layout = core.Loading(fullscreen=True, type="cube", children=[
    html.Div(className="body", children=[
        navbar("Pre-WGS"),
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button']),
                html.Br(),
                html.Br(),
                html.Button('Add All', id=ids["all-runs"], className="inline"),
                html.Label([
                    "Run",
                    core.Dropdown(id=ids["run-id-list"],
                                  options=[
                                      {"label": run,
                                       "value": run} for run in ALL_RUNS
                    ],
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
                                       "value": BAMQC_COL.Run}
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
                                       "value": BAMQC_COL.TotalReads},
                                      {"label": "Duplication",
                                       "value": BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION},
                                      {"label": "Unmapped Reads",
                                       "value": special_cols["Unmapped Reads"]},
                                      {"label": "Non-Primary Reads",
                                       "value": special_cols["Non-Primary Reads"]},
                                      {"label": "On-target Reads",
                                       "value": special_cols["On-target Reads"]},
                                      {"label": "Purity",
                                       "value": special_cols["Purity"]},
                                      {"label": "Ploidy",
                                       "value": ICHOR_COL.Ploidy},
                                      {"label": "Mean Insert Size",
                                       "value": BAMQC_COL.InsertMean}
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
                    "Insert Mean:",
                    core.Slider(
                        id=ids["insert-mean-slider"],
                        min=0,
                        max=500,
                        step=10,
                        marks={
                            0: "0",
                            50: "50",
                            100: "100",
                            150: "150",
                            200: "200",
                            250: "250",
                            300: "300",
                            350: "350",
                            400: "400",
                            450: "450",
                            500: "500"
                        },
                        tooltip="always_visible",
                        value=initial_cutoff_insert_mean
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

            html.Div(className="seven columns", children=[
                core.Graph(
                    id=ids["total-reads"],
                    figure=generate_total_reads(EMPTY_WGS, initial_colour_col,
                                                initial_shape_col, initial_cutoff_pf_reads)
                ),
                core.Graph(
                    id=ids["mean-insert"],
                    figure=generate_mean_insert_size(
                        EMPTY_WGS, initial_colour_col, initial_shape_col, initial_cutoff_insert_mean)
                ),
                core.Graph(
                    id=ids["reads-per-start-point"],
                    figure=generate_reads_per_start_point(
                        EMPTY_WGS, initial_colour_col, initial_shape_col, initial_cutoff_rpsp)
                ),
                core.Graph(
                    id=ids["duplication"],
                    figure=generate_duplication(
                        EMPTY_WGS, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["purity"],
                    figure=generate_purity(EMPTY_WGS,
                                           initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["ploidy"],
                    figure=generate_ploidy(EMPTY_WGS,
                                           initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["unmapped-reads"],
                    figure=generate_unmapped_reads(
                        EMPTY_WGS, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["non-primary-reads"],
                    figure=generate_non_primary(
                        EMPTY_WGS, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["on-target-reads"],
                    figure=generate_on_target_reads(
                        EMPTY_WGS, initial_colour_col, initial_shape_col)
                ),
            ]),
            html.Div(className='terminal-output',
                     children=[
                         html.Pre(generate_terminal_output(EMPTY_WGS, initial_cutoff_rpsp, initial_cutoff_insert_mean,
                                                           initial_cutoff_pf_reads),
                                  id=ids['terminal-output'],
                                  )
                     ]),
            html.Div(className='data-table',
                     children=[
                    build_table(ids["data-table"], wgs_table_columns, WGS_DF,
                                BAMQC_COL.TotalReads)
                     ]),
        ])
    ])
])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["total-reads"], "figure"),
            Output(ids["mean-insert"], "figure"),
            Output(ids["reads-per-start-point"], "figure"),
            Output(ids["duplication"], "figure"),
            Output(ids["purity"], "figure"),
            Output(ids["ploidy"], "figure"),
            Output(ids["unmapped-reads"], "figure"),
            Output(ids["non-primary-reads"], "figure"),
            Output(ids["on-target-reads"], "figure"),
            Output(ids["terminal-output"], "value"),
            Output(ids["data-table"], "data"),
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
            State(ids["reads-per-start-point-slider"], 'value'),
            State(ids["insert-mean-slider"], 'value'),
            State(ids["passed-filter-reads-slider"], 'value'),
        ]
    )
    def update_pressed(click,
                       runs,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by, total_reads_cutoff, insert_mean_cutoff, rpsp_cutoff):
        if not runs:
            df = pd.DataFrame(columns=WGS_DF.columns)
        else:
            df = WGS_DF[WGS_DF[BAMQC_COL.Run].isin(runs)]
        sort_by = [first_sort, second_sort]
        df = df.sort_values(by=sort_by)
        df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
        df = fill_in_colour_col(df, colour_by, shape_or_colour_values)
        dd = defaultdict(list)

        return [
            generate_total_reads(df, colour_by, shape_by, total_reads_cutoff),
            generate_mean_insert_size(df, colour_by, shape_by, insert_mean_cutoff),
            generate_reads_per_start_point(df, colour_by, shape_by, rpsp_cutoff),
            generate_duplication(df, colour_by, shape_by),
            generate_purity(df, colour_by, shape_by),
            generate_ploidy(df, colour_by, shape_by),
            generate_unmapped_reads(df, colour_by, shape_by),
            generate_non_primary(df, colour_by, shape_by),
            generate_on_target_reads(df, colour_by, shape_by),
            generate_terminal_output(df, rpsp_cutoff, insert_mean_cutoff, total_reads_cutoff),
            df.to_dict('records', into=dd),
        ]
