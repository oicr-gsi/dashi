import dash_core_components as core
import dash_html_components as html
import numpy
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State

import gsiqcetl.column
import pinery
from gsiqcetl import QCETLCache
from . import navbar
from ..dash_id import init_ids
from ..plot_builder import get_shapes_for_values, fill_in_shape_col
from ..utility import df_manipulation as util

""" Set up elements needed for page """
page_name = "preqc-wgs"

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
    "passed-filter-reads-slider",

    # Graphs
    "total-reads",
    "mean-insert",
    "duplication",
    "purity",
    "ploidy",
    "unmapped-reads",
    "non-primary-reads",
    "on-target-reads"
])

BAMQC_COL = gsiqcetl.column.BamQcColumn
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

# Set points for graph cutoffs
graph_cutoffs = {
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
    if True:  # DELETE(amasella): once IchorCNA data is available
        wgs_df = cache.bamqc.bamqc
        wgs_df[ICHOR_COL.Ploidy] = numpy.NaN
        wgs_df[ICHOR_COL.TumorFraction] = numpy.NaN
        # This doesn't seem to exist even though it should
        wgs_df[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION] = numpy.NaN
    else:
        wgs_df = cache.bamqc.bamqc.merge(cache.ichorcna.ichorcna[[ICHOR_COL.Ploidy, ICHOR_COL.TumorFraction]],
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


def generate_mean_insert_size(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        BAMQC_COL.InsertMean,
        "Insert Mean", "Base Pairs")


def generate_duplication(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION,
        "Duplication", "Percent (%)")


def generate_unmapped_reads(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        special_cols["Unmapped Reads"],
        "Unmapped Reads", "Percent (%)")


def generate_non_primary(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        special_cols["Non-Primary Reads"], "Non-Primary Reads",
        "Percent (%)")


def generate_on_target_reads(df, colour_by, shape_by):
    return scatter_graph(
        df, colour_by, shape_by, PINERY_COL.SampleName,
        special_cols["On-target Reads"],
        "On-target Reads", "Percent (%)")


def generate_purity(df, colour_by, shape_by):
    return scatter_graph(df, colour_by, shape_by, PINERY_COL.SampleName,
                         special_cols["Purity"],
                         "Purity", "Percent (%)")


def generate_ploidy(df, colour_by, shape_by):
    return scatter_graph(df, colour_by, shape_by, PINERY_COL.SampleName,
                         ICHOR_COL.Ploidy, "Ploidy", "")


# Layout elements
layout = core.Loading(fullscreen=True, type="cube", children=[
    html.Div(className="body", children=[
        navbar("Pre-WGS"),
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
                                       "value": BAMQC_COL.Run}
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
                # TODO: add cut-off sliders

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

            html.Div(className="seven columns", children=[
                core.Graph(
                     id=ids["total-reads"],
                     figure=generate_total_reads(WGS_DF, initial_colour_col,
                                                 initial_shape_col)
                     ),
                core.Graph(
                    id=ids["mean-insert"],
                    figure=generate_mean_insert_size(
                        WGS_DF, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["duplication"],
                    figure=generate_duplication(
                        WGS_DF, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["purity"],
                    figure=generate_purity(WGS_DF,
                                           initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["ploidy"],
                    figure=generate_ploidy(WGS_DF,
                                           initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["unmapped-reads"],
                    figure=generate_unmapped_reads(
                        WGS_DF, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["non-primary-reads"],
                    figure=generate_non_primary(
                        WGS_DF, initial_colour_col, initial_shape_col)
                ),
                core.Graph(
                    id=ids["on-target-reads"],
                    figure=generate_on_target_reads(
                        WGS_DF, initial_colour_col, initial_shape_col)
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
            Output(ids["mean-insert"], "figure"),
            Output(ids["duplication"], "figure"),
            Output(ids["purity"], "figure"),
            Output(ids["ploidy"], "figure"),
            Output(ids["unmapped-reads"], "figure"),
            Output(ids["non-primary-reads"], "figure"),
            Output(ids["on-target-reads"], "figure")
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
        df = WGS_DF[WGS_DF[BAMQC_COL.Run].isin(runs)]
        sort_by = [first_sort, second_sort]
        df = df.sort_values(by=sort_by)
        df = fill_in_shape_col(df, shape_by, shape_or_colour_values)

        return [
            generate_total_reads(df, colour_by, shape_by),
            generate_mean_insert_size(df, colour_by, shape_by),
            generate_duplication(df, colour_by, shape_by),
            generate_purity(df, colour_by, shape_by),
            generate_ploidy(df, colour_by, shape_by),
            generate_non_primary(df, colour_by, shape_by),
            generate_on_target_reads(df, colour_by, shape_by),
        ]