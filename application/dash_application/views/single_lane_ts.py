from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State
import pandas as pd
from ..dash_id import init_ids
from ..plot_builder import generate, fill_in_shape_col, fill_in_colour_col, \
    fill_in_size_col, generate_total_reads
from ..table_builder import table_tabs, cutoff_table_data
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from gsiqcetl.column import BamQcColumn
import pinery
import logging
import json
import datetime

logger = logging.getLogger(__name__)

page_name = 'single-lane-ts'
title = "Single-Lane Targeted Sequencing"

ids = init_ids([
    # Buttons
    'update-button',

    # Sidebar controls
    'all-runs',
    'run-id-list',
    'all-instruments',
    'instruments-list',
    'all-projects',
    'projects-list',
    'all-kits',
    'kits-list',
    'all-library-designs',
    'library-designs-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'show-names',
    'insert-size-mean-cutoff',
    'passed-filter-reads-cutoff',
    "date-range",

    #Graphs
    'total-reads',
    'unmapped-reads',
    'non-primary-reads',
    'on-target-reads',
    'mean-insert-size',

    #Data table
    'failed-samples',
    'data-table'
])

BAMQC_COL = BamQcColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {
    "Total Reads (Passed Filter)": "Total Reads PassedFilter",
}

shape_or_colour_by = [
    {"label": "Project", "value": PINERY_COL.StudyTitle},
    {"label": "Run", "value": PINERY_COL.SequencerRunName},
    {"label": "Kit", "value": PINERY_COL.PrepKit},
    {"label": "Tissue Prep", "value": PINERY_COL.TissuePreparation},
    {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
]

def get_bamqc_data():
    bamqc_df = util.get_bamqc()
    bamqc_df = util.df_with_normalized_ius_columns(bamqc_df, BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes)
    bamqc_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc_df[BAMQC_COL.TotalReads] / 1e6, 3)

    pinery_samples = util.get_pinery_samples_from_active_projects()
    # TODO filter??

    bamqc_df = util.df_with_pinery_samples(bamqc_df, pinery_samples, util.bamqc_ius_columns)

    bamqc_df = util.df_with_instrument_model(bamqc_df, PINERY_COL.SequencerRunName)

    bamqc_df = util.filter_by_library_design(bamqc_df, ["EX", "TS"])

    return bamqc_df, util.cache.versions(["bamqc"])


(bamqc, DATAVERSION) = get_bamqc_data()


# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = bamqc[PINERY_COL.StudyTitle].sort_values().unique()
ALL_RUNS = bamqc[BAMQC_COL.Run].sort_values().unique()[::-1] # reverse order
ALL_KITS = bamqc[PINERY_COL.PrepKit].sort_values().unique()
ALL_TISSUE_MATERIALS = bamqc[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = bamqc[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(bamqc)
ALL_SAMPLES = bamqc[PINERY_COL.SampleName].sort_values().unique()


# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
]
most_bamqc_cols = [*BAMQC_COL.values()]
most_bamqc_cols.remove(BAMQC_COL.BamFile)
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.ExternalName,
    PINERY_COL.GroupID, PINERY_COL.TissueOrigin, PINERY_COL.TissueType,
    PINERY_COL.TargetedResequencing, PINERY_COL.Institute,
    INSTRUMENT_COLS.ModelName
]
ex_table_columns = [*first_col_set, *most_bamqc_cols, *later_col_set]

# Set initial values for dropdown menus
initial_first_sort = PINERY_COL.StudyTitle
initial_second_sort = BAMQC_COL.TotalReads
initial_colour_col = PINERY_COL.StudyTitle
initial_shape_col = PINERY_COL.SequencerRunName
initial_shownames_val = 'none'

# Set initial points for graph cutoff lines
initial_cutoff_pf_reads = 0.01
initial_cutoff_insert_size = 150

shape_or_colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    PINERY_COL.SequencerRunName: ALL_RUNS,
    PINERY_COL.PrepKit: ALL_KITS,
    PINERY_COL.TissuePreparation: ALL_TISSUE_MATERIALS,
    PINERY_COL.LibrarySourceTemplateType: ALL_LIBRARY_DESIGNS
}

bamqc = fill_in_shape_col(bamqc, initial_shape_col, shape_or_colour_values)
bamqc = fill_in_colour_col(bamqc, initial_colour_col, shape_or_colour_values)
bamqc = fill_in_size_col(bamqc)

empty_bamqc = pd.DataFrame(columns=bamqc.columns)


def generate_unmapped_reads(current_data, colourby, shapeby, shownames):
    return generate(
        "Unmapped Reads (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: sidebar_utils.percentage_of(d, BAMQC_COL.UnmappedReads, BAMQC_COL.TotalReads),
        "%",
        colourby,
        shapeby,
        shownames
    )


def generate_nonprimary_reads(current_data, colourby, shapeby, shownames):
    return generate(
        "Non-Primary Reads (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: sidebar_utils.percentage_of(d, BAMQC_COL.NonPrimaryReads, BAMQC_COL.TotalReads),
        "%",
        colourby,
        shapeby,
        shownames
    )


def generate_on_target_reads(current_data, colourby, shapeby, shownames):
    return generate(
        "On Target Reads (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: sidebar_utils.percentage_of(d, BAMQC_COL.ReadsOnTarget, BAMQC_COL.TotalReads),
        "%",
        colourby,
        shapeby,
        shownames
    )


def generate_mean_insert_size(current_data, colourby, shapeby, shownames,
                           cutoff_line):
    return generate(
        "Mean Insert Size",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.InsertMean],
        "Base Pairs",
        colourby,
        shapeby,
        shownames,
        cutoff_line
    )


def dataversion():
    return DATAVERSION


def layout(query_string):
    requested_start, requested_end = sidebar_utils.parse_run_date_range(query_string)

    return core.Loading(fullscreen=True, type="dot", children=[html.Div(className='body',
    children=[
        html.Div(className='row flex-container',
                 children=[
                     html.Div(className='sidebar four columns',
            children=[
                html.Button('Update', id=ids['update-button']),
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

                sidebar_utils.select_library_designs(
                    ids["all-library-designs"], ids["library-designs-list"],
                    ALL_LIBRARY_DESIGNS),

                sidebar_utils.hr(),

                # Sort, colour, and shape
                sidebar_utils.select_first_sort(ids['first-sort'],
                                                initial_first_sort),

                sidebar_utils.select_second_sort(
                    ids['second-sort'],
                    initial_second_sort,
                    [
                            {"label": "Total Reads",
                             "value": BAMQC_COL.TotalReads},
                            {"label": "Unmapped Reads",
                             "value": BAMQC_COL.UnmappedReads},
                            {"label": "Non-primary Reads",
                             "value": BAMQC_COL.NonPrimaryReads},
                            {"label": "On-target Reads",
                             "value": BAMQC_COL.ReadsOnTarget},
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
                    ids['passed-filter-reads-cutoff'], initial_cutoff_pf_reads),
                sidebar_utils.insert_mean_cutoff(
                    ids['insert-size-mean-cutoff'], initial_cutoff_insert_size),
            ]),

            # Graphs
            html.Div(className='seven columns',
                children=[
                    core.Graph(id=ids['total-reads'],
                        figure=generate_total_reads(
                            empty_bamqc,
                            PINERY_COL.SampleName,
                            special_cols["Total Reads (Passed Filter)"],
                            initial_colour_col,
                            initial_shape_col,
                            initial_shownames_val,
                            initial_cutoff_pf_reads)
                    ),
                    core.Graph(id=ids['unmapped-reads'],
                        figure=generate_unmapped_reads(empty_bamqc,
                                                       initial_colour_col,
                                                       initial_shape_col,
                                                       initial_shownames_val)
                    ),
                    core.Graph(id=ids['non-primary-reads'],
                        figure=generate_nonprimary_reads(empty_bamqc,
                                                         initial_colour_col,
                                                         initial_shape_col,
                                                         initial_shownames_val)
                    ),
                    core.Graph(id=ids['on-target-reads'],
                        figure=generate_on_target_reads(empty_bamqc,
                                                        initial_colour_col,
                                                        initial_shape_col,
                                                        initial_shownames_val)
                    ),
                    core.Graph(id=ids['mean-insert-size'],
                        figure=generate_mean_insert_size(empty_bamqc,
                                                         initial_colour_col,
                                                         initial_shape_col,
                                                         initial_shownames_val,
                                                         initial_cutoff_insert_size)
                    )
                ]),
            ]),

            # Tables
            table_tabs(
                ids["failed-samples"],
                ids["data-table"],
                empty_bamqc,
                ex_table_columns,
                BAMQC_COL.TotalReads,
                [
                    ('Insert Mean Cutoff', BAMQC_COL.InsertMean,
                     initial_cutoff_insert_size, True),
                    ('Total Reads Cutoff',
                     special_cols["Total Reads (Passed Filter)"],
                     initial_cutoff_pf_reads, True),
                ]
            )
    ]),
])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids['total-reads'], 'figure'),
            Output(ids['unmapped-reads'], 'figure'),
            Output(ids['non-primary-reads'], 'figure'),
            Output(ids['on-target-reads'], 'figure'),
            Output(ids['mean-insert-size'], 'figure'),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids['data-table'], 'data')
        ],
        [Input(ids['update-button'], 'n_clicks')],
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
            State(ids['insert-size-mean-cutoff'], 'value'),
            State(ids['passed-filter-reads-cutoff'], 'value'),
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
            firstsort, 
            secondsort, 
            colourby,
            shapeby,
            searchsample,
            shownames,
            insertsizemean,
            passedfilter,
            start_date,
            end_date,
            search_query):
        log_utils.log_filters(locals(), logger)

        # Apply get selected runs
        if not runs and not instruments and not projects and not kits and not library_designs:
            data = pd.DataFrame(columns=empty_bamqc.columns)
        else:
            data = bamqc

        if runs:
            data = data[data[BAMQC_COL.Run].isin(runs)]
        if instruments:
            data = data[data[INSTRUMENT_COLS.ModelName].isin(instruments)]
        if projects:
            data = data[data[PINERY_COL.StudyTitle].isin(projects)]
        if kits:
            data = data[data[PINERY_COL.PrepKit].isin(kits)]
        if library_designs:
            data = data[data[PINERY_COL.LibrarySourceTemplateType].isin(
                library_designs)]
        data = data[data[BAMQC_COL.Run].isin(sidebar_utils.runs_in_range(start_date, end_date))]
        data = fill_in_shape_col(data, shapeby, shape_or_colour_values)
        data = fill_in_colour_col(data, colourby, shape_or_colour_values,
                                  searchsample)

        data = fill_in_size_col(data, searchsample)

        data = data.sort_values(by=[firstsort, secondsort], ascending=False)
        dd = defaultdict(list)
        (failure_df, failure_columns ) =cutoff_table_data(data, [
                ('Insert Mean Cutoff', BAMQC_COL.InsertMean, insertsizemean,
                 True),
                ('Total Reads Cutoff', special_cols["Total Reads (Passed "
                                                    "Filter)"], passedfilter,
                 True),
            ])
        return [
            generate_total_reads(
                data, PINERY_COL.SampleName,
                special_cols["Total Reads (Passed Filter)"], colourby,
                shapeby, shownames, passedfilter),
            generate_unmapped_reads(data, colourby, shapeby, shownames),
            generate_nonprimary_reads(data, colourby, shapeby, shownames),
            generate_on_target_reads(data, colourby, shapeby, shownames),
            generate_mean_insert_size(data, colourby, shapeby, shownames,
                                   insertsizemean),
            failure_columns,
            failure_df.to_dict('records'),
            data.to_dict('records', into=dd)
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
