from collections import defaultdict

import dash_core_components as core
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas as pd

import gsiqcetl.column
import pinery
from ..dash_id import init_ids
from ..plot_builder import fill_in_shape_col, fill_in_colour_col, \
    fill_in_size_col, generate, generate_total_reads
from ..table_builder import table_tabs, cutoff_table_data
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
import logging
import json

logger = logging.getLogger(__name__)

""" Set up elements needed for page """
page_name = "preqc-wgs"
title = "Pre-WGS"

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
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "search-sample",
    "insert-mean-cutoff",
    "passed-filter-reads-cutoff",
    "date-range",
    "show-names",

    # Graphs
    "total-reads",
    "mean-insert",
    "duplication",
    "purity",
    "ploidy",
    "unmapped-reads",
    "non-primary-reads",
    "on-target-reads",

    "failed-samples",
    "data-table",
])

BAMQC_COL = gsiqcetl.column.BamQc3Column
ICHOR_COL = gsiqcetl.column.IchorCnaColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "total reads passed filter",
    "Unmapped Reads": "percent unmapped reads",
    "Non-Primary Reads": "percent non-primary reads",
    "On-target Reads": "percent on-target reads",
    "Purity": "percent purity",
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
initial_shownames_val = 'none'
initial_cutoff_pf_reads = 0.01
initial_cutoff_insert_mean = 150

shape_or_colour_by = [
    {"label": "Project", "value": PINERY_COL.StudyTitle},
    {"label": "Run", "value": PINERY_COL.SequencerRunName},
    {"label": "Kit", "value": PINERY_COL.PrepKit},
    {"label": "Tissue Prep", "value": PINERY_COL.TissuePreparation}
]


def get_wgs_data():
    """
    Join together all the dataframes needed for graphing:
      * BamQC (where most of the graphed QC data comes from)
      * ichorCNA (where the remainder of the graphed QC data comes from)
      * Pinery (sample information)
      * Instruments (to allow filtering by instrument model)
      * Runs (needed to join Pinery to Instruments)
    """
    # Pull in sample metadata from Pinery.
    pinery_samples = util.get_pinery_samples_from_active_projects()
    # Filter the Pinery samples for only WG samples.
    pinery_samples = util.filter_by_library_design(pinery_samples,
                                                   ["WG"])

    ichorcna_df = util.get_ichorcna()
    ichorcna_df = ichorcna_df[[ICHOR_COL.Run,
                               ICHOR_COL.Lane,
                               ICHOR_COL.Barcodes,
                               ICHOR_COL.Ploidy,
                               ICHOR_COL.TumorFraction]]

    bamqc_df = util.get_bamqc3()

    # Cast the primary key/join columns to explicit types
    bamqc_df = util.df_with_normalized_ius_columns(
        bamqc_df, BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes)
    ichorcna_df = util.df_with_normalized_ius_columns(
        ichorcna_df, ICHOR_COL.Run, ICHOR_COL.Lane, ICHOR_COL.Barcodes)

    # Calculate percent uniq reads column
    bamqc_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc_df[BAMQC_COL.TotalReads] / 1e6, 3)
    bamqc_df[special_cols["Unmapped Reads"]] = round(
        bamqc_df[BAMQC_COL.UnmappedReads] * 100.0 /
        bamqc_df[BAMQC_COL.TotalReads], 3)
    bamqc_df[special_cols["Non-Primary Reads"]] = round(
        bamqc_df[BAMQC_COL.NonPrimaryReads] * 100.0 /
        bamqc_df[BAMQC_COL.TotalReads], 3)
    bamqc_df[special_cols["On-target Reads"]] = round(
        bamqc_df[BAMQC_COL.ReadsOnTarget] * 100.0 /
        bamqc_df[BAMQC_COL.TotalReads], 3)
    ichorcna_df[special_cols["Purity"]] = round(
        ichorcna_df[ICHOR_COL.TumorFraction] * 100.0, 3)

    # Join BamQC and Pinery data
    wgs_df = util.df_with_pinery_samples(bamqc_df, pinery_samples,
                                         util.bamqc_ius_columns)

    # Join ichorCNA and BamQC+Pinery data
    wgs_df = wgs_df.merge(
        ichorcna_df, how = "left",
        left_on=util.pinery_ius_columns,
        right_on=util.ichorcna_ius_columns)

    # Join df and instrument model
    wgs_df = util.df_with_instrument_model(wgs_df, PINERY_COL.SequencerRunName)

    # Filter the dataframe to only include Illumina data
    illumina_models = util.get_illumina_instruments(wgs_df)
    wgs_df = wgs_df[wgs_df[INSTRUMENT_COLS.ModelName].isin(illumina_models)]

    return wgs_df


# Make the WGS dataframe
WGS_DF = get_wgs_data()

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = WGS_DF[PINERY_COL.StudyTitle].sort_values().unique()
ALL_KITS = WGS_DF[PINERY_COL.PrepKit].sort_values().unique()
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(WGS_DF)
ALL_TISSUE_MATERIALS = WGS_DF[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = WGS_DF[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ALL_RUNS = WGS_DF[PINERY_COL.SequencerRunName].sort_values().unique()[
    ::-1]  # reverse the list
ALL_SAMPLES = WGS_DF[PINERY_COL.SampleName].sort_values().unique()

shape_or_colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    PINERY_COL.SequencerRunName: ALL_RUNS,
    PINERY_COL.PrepKit: ALL_KITS,
    PINERY_COL.TissuePreparation: ALL_TISSUE_MATERIALS
}

# Add shape col to WG dataframe
WGS_DF = fill_in_shape_col(WGS_DF, initial_shape_col, shape_or_colour_values)
WGS_DF = fill_in_colour_col(WGS_DF, initial_colour_col, shape_or_colour_values)
WGS_DF = fill_in_size_col(WGS_DF)

EMPTY_WGS = pd.DataFrame(columns=WGS_DF.columns)


def generate_mean_insert_size(df, colour_by, shape_by, shownames, cutoff):
    return generate(
        "Mean Insert Size",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.InsertMean],
        "Base Pairs",
        colour_by,
        shape_by,
        shownames,
        cutoff
    )


def generate_duplication(df, colour_by, shape_by, shownames):
    return generate(
        "Duplication (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.MarkDuplicates_PERCENT_DUPLICATION],
        "%",
        colour_by,
        shape_by,
        shownames
    )


def generate_unmapped_reads(df, colour_by, shape_by, shownames):
    return generate(
        "Unmapped Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Unmapped Reads"]],
        "%",
        colour_by,
        shape_by,
        shownames
    )


def generate_non_primary(df, colour_by, shape_by, shownames):
    return generate(
        "Non-Primary Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Non-Primary Reads"]],
        "%",
        colour_by,
        shape_by,
        shownames
    )


def generate_on_target_reads(df, colour_by, shape_by, shownames):
    return generate(
        "On Target Reads (%)",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["On-target Reads"]],
        "%",
        colour_by,
        shape_by,
        shownames
    )


def generate_purity(df, colour_by, shape_by, shownames):
    return generate(
        "Purity",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Purity"]],
        "%",
        colour_by,
        shape_by,
        shownames
    )


def generate_ploidy(df, colour_by, shape_by, shownames):
    return generate(
        "Ploidy",
        df,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[ICHOR_COL.Ploidy],
        "",
        colour_by,
        shape_by,
        shownames
    )


# Layout elements
def layout(query_string):
    requested_start, requested_end = sidebar_utils.parse_run_date_range(query_string)

    return core.Loading(fullscreen=True, type="dot", children=[
    html.Div(className="body", children=[
        html.Div(className="row flex-container", children=[
            html.Div(className="sidebar four columns", children=[
                html.Button("Update", id=ids['update-button']),
                html.Br(),
                html.Br(),

                # Filters
                sidebar_utils.select_runs(ids["all-runs"],
                                          ids["run-id-list"], ALL_RUNS),

                sidebar_utils.run_range_input(ids["date-range"], requested_start, requested_end),

                sidebar_utils.hr(),

                sidebar_utils.select_projects(ids["all-projects"],
                                              ids["projects-list"],
                                              ALL_PROJECTS),

                sidebar_utils.select_kits(ids["all-kits"], ids["kits-list"],
                                          ALL_KITS),

                sidebar_utils.select_instruments(ids["all-instruments"],
                                                 ids["instruments-list"],
                                                 ILLUMINA_INSTRUMENT_MODELS),

                sidebar_utils.hr(),

                # Sort, colour, and shape
                sidebar_utils.select_first_sort(ids['first-sort'],
                                                initial_first_sort),

                sidebar_utils.select_second_sort(
                    ids["second-sort"],
                    initial_second_sort,
                    [
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
                    ]
                ),

                sidebar_utils.select_colour_by(ids['colour-by'],
                                              shape_or_colour_by,
                                              initial_colour_col),

                sidebar_utils.select_shape_by(ids['shape-by'],
                                             shape_or_colour_by,
                                             initial_shape_col),

                sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                      ALL_SAMPLES),

                sidebar_utils.show_names_input(ids['show-names'],
                                               initial_shownames_val),

                sidebar_utils.hr(),

                # Cutoffs
                sidebar_utils.total_reads_cutoff_input(
                    ids["passed-filter-reads-cutoff"], initial_cutoff_pf_reads),
                sidebar_utils.insert_mean_cutoff(
                    ids["insert-mean-cutoff"], initial_cutoff_insert_mean),
            ]),

            html.Div(className="seven columns", children=[
                core.Graph(
                    id=ids["total-reads"],
                    figure=generate_total_reads(
                        EMPTY_WGS,
                        PINERY_COL.SampleName,
                        special_cols["Total Reads (Passed Filter)"],
                        initial_colour_col,
                        initial_shape_col,
                        initial_shownames_val,
                        initial_cutoff_pf_reads)
                ),
                core.Graph(
                    id=ids["mean-insert"],
                    figure=generate_mean_insert_size(
                        EMPTY_WGS, initial_colour_col, initial_shape_col,
                        initial_shownames_val, initial_cutoff_insert_mean)
                ),
                core.Graph(
                    id=ids["duplication"],
                    figure=generate_duplication(
                        EMPTY_WGS, initial_colour_col, initial_shape_col,
                        initial_shownames_val)
                ),
                core.Graph(
                    id=ids["purity"],
                    figure=generate_purity(EMPTY_WGS,
                                           initial_colour_col,
                                           initial_shape_col,
                                           initial_shownames_val)
                ),
                core.Graph(
                    id=ids["ploidy"],
                    figure=generate_ploidy(EMPTY_WGS,
                                           initial_colour_col,
                                           initial_shape_col,
                                           initial_shownames_val)
                ),
                core.Graph(
                    id=ids["unmapped-reads"],
                    figure=generate_unmapped_reads(
                        EMPTY_WGS, initial_colour_col, initial_shape_col,
                        initial_shownames_val)
                ),
                core.Graph(
                    id=ids["non-primary-reads"],
                    figure=generate_non_primary(
                        EMPTY_WGS, initial_colour_col, initial_shape_col,
                        initial_shownames_val)
                ),
                core.Graph(
                    id=ids["on-target-reads"],
                    figure=generate_on_target_reads(
                        EMPTY_WGS, initial_colour_col, initial_shape_col,
                        initial_shownames_val)
                ),
            ]),
        ]),
        table_tabs(
            ids["failed-samples"],
            ids["data-table"],
            EMPTY_WGS,
            wgs_table_columns,
            BAMQC_COL.TotalReads,
            [
                ('Insert Mean Cutoff', BAMQC_COL.InsertMean,
                 initial_cutoff_insert_mean, True),
                ('Total Reads Cutoff',
                 special_cols["Total Reads (Passed Filter)"],
                 initial_cutoff_pf_reads, True),
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
            Output(ids["on-target-reads"], "figure"),
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
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['search-sample'], 'value'),
            State(ids['show-names'], 'value'),
            State(ids["insert-mean-cutoff"], 'value'),
            State(ids["passed-filter-reads-cutoff"], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date')
        ]
    )
    def update_pressed(click,
                       runs,
                       instruments,
                       projects,
                       kits,
                       first_sort,
                       second_sort,
                       colour_by,
                       shape_by,
                       searchsample,
                       show_names,
                       total_reads_cutoff,
                       insert_mean_cutoff,
                       start_date,
                       end_date):
        params = locals()
        del params['click']
        logger.info(json.dumps(params))

        if not runs and not instruments and not projects and not kits:
            df = pd.DataFrame(columns=WGS_DF.columns)
        else:
            df = WGS_DF

        if runs:
            df = df[df[PINERY_COL.SequencerRunName].isin(runs)]
        if instruments:
            df = df[df[INSTRUMENT_COLS.ModelName].isin(instruments)]
        if projects:
            df = df[df[PINERY_COL.StudyTitle].isin(projects)]
        if kits:
            df = df[df[PINERY_COL.PrepKit].isin(kits)]
        df = df[df[PINERY_COL.SequencerRunName].isin(sidebar_utils.runs_in_range(start_date, end_date))]
        sort_by = [first_sort, second_sort]
        df = df.sort_values(by=sort_by)
        df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
        df = fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample)
        df = fill_in_size_col(df, searchsample)
        dd = defaultdict(list)
        (failure_df, failure_columns) = cutoff_table_data(df, [
            ('Insert Mean Cutoff', BAMQC_COL.InsertMean, insert_mean_cutoff, True),
            ('Total Reads Cutoff', special_cols["Total Reads (Passed Filter)"], total_reads_cutoff, True),
        ])

        return [
            generate_total_reads(
                df, PINERY_COL.SampleName,
                special_cols["Total Reads (Passed Filter)"], colour_by,
                shape_by, show_names, total_reads_cutoff),
            generate_mean_insert_size(df, colour_by, shape_by, show_names,
                                      insert_mean_cutoff),
            generate_duplication(df, colour_by, shape_by, show_names),
            generate_purity(df, colour_by, shape_by, show_names),
            generate_ploidy(df, colour_by, shape_by, show_names),
            generate_unmapped_reads(df, colour_by, shape_by, show_names),
            generate_non_primary(df, colour_by, shape_by, show_names),
            generate_on_target_reads(df, colour_by, shape_by, show_names),
            failure_columns,
            failure_df.to_dict('records'),
            df.to_dict('records', into=dd),
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
