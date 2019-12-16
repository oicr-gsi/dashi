from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State
import pandas as pd
from . import navbar
from ..dash_id import init_ids
from ..plot_builder import generate, fill_in_shape_col, fill_in_colour_col, fill_in_size_col
from ..table_builder import build_table, table_tabs, cutoff_table_data
from ..utility import df_manipulation as util
from ..utility import slider_utils
from gsiqcetl.column import BamQcColumn
import pinery

page_name = 'preqc-exome'

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
    'reads-per-start-point-slider',
    'insert-size-mean-slider',
    'passed-filter-reads-slider',
    "date-range",

    #Graphs
    'total-reads',
    'unmapped-reads',
    'non-primary-reads',
    'on-target-reads',
    'reads-per-start-point',
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

    return bamqc_df


bamqc = get_bamqc_data()


# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = bamqc[PINERY_COL.StudyTitle].sort_values().unique()
ALL_RUNS = bamqc[BAMQC_COL.Run].sort_values().unique()[::-1] # reverse order
ALL_KITS = bamqc[PINERY_COL.PrepKit].sort_values().unique()
ALL_TISSUE_MATERIALS = bamqc[
    PINERY_COL.TissuePreparation].sort_values().unique()
ALL_LIBRARY_DESIGNS = bamqc[
    PINERY_COL.LibrarySourceTemplateType].sort_values().unique()
ILLUMINA_INSTRUMENT_MODELS = bamqc[bamqc[
    INSTRUMENT_COLS.Platform] == 'ILLUMINA'][
    INSTRUMENT_COLS.ModelName].sort_values().unique()
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

# Set initial points for graph cutoff lines
initial_cutoff_pf_reads = 0.01
initial_cutoff_insert_size = 150
initial_cutoff_rpsp = 5

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


def generate_total_reads(current_data, colourby, shapeby, shownames,
                         cutoff_line):
    return generate(
        "Passed Filter Reads",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[special_cols["Total Reads (Passed Filter)"]],
        "# PF Reads x 10^6",
        colourby,
        shapeby,
        shownames,
        cutoff_line
    )
    

def generate_unmapped_reads(current_data, colourby, shapeby, shownames):
    return generate(
        "Unmapped Reads (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: slider_utils.percentage_of(d, BAMQC_COL.UnmappedReads, BAMQC_COL.TotalReads),
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
        lambda d: slider_utils.percentage_of(d, BAMQC_COL.NonPrimaryReads, BAMQC_COL.TotalReads),
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
        lambda d: slider_utils.percentage_of(d, BAMQC_COL.ReadsOnTarget, BAMQC_COL.TotalReads),
        "%",
        colourby,
        shapeby,
        shownames
    )


def generate_reads_per_start_point(current_data, colourby, shapeby, shownames,
                               cutoff_line):
    return generate(
        "Reads per Start Point",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.ReadsPerStartPoint],
        None,
        colourby,
        shapeby,
        shownames,
        cutoff_line
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


layout = core.Loading(fullscreen=True, type="cube", children=[html.Div(className='body',
    children=[
        navbar("Pre-Exome"),
        html.Div(className='row flex-container',
                 children=[
                     html.Div(className='sidebar four columns',
            children=[
                html.Button('Update', id=ids['update-button']),
                html.Br(),
                html.Div(id="debug"),
                html.Br(),
                core.Loading(type="circle", children=[
                    html.Button('Add All', id=ids["all-runs"], className="inline"),
                    html.Label([
                        "Run",
                        core.Dropdown(id=ids['run-id-list'],
                            options=[{'label': x, 'value': x} for x in ALL_RUNS],
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
                core.Loading(type="circle", children=[
                    html.Button("All Projects", id=ids["all-projects"],
                                className="inline"),
                    html.Label([
                        "Projects",
                        core.Dropdown(id=ids["projects-list"],
                                      options=[
                                          {"label": project,
                                           "value": project} for project
                                          in ALL_PROJECTS
                                      ],
                                      multi=True)
                    ]),
                ]),
                core.Loading(type="circle", children=[
                    html.Button("All Kits", id=ids["all-kits"],
                                className="inline"),
                    html.Label([
                       "Kits",
                        core.Dropdown(id=ids["kits-list"],
                                      options=[
                                          {"label": kit,
                                           "value": kit} for kit in ALL_KITS
                                      ],
                                      multi=True)
                        ]),
                ]),
                core.Loading(type="circle", children=[
                    html.Button("All Library Designs", id=ids[
                        "all-library-designs"],
                                className="inline"),
                    html.Label([
                        "Library Designs",
                        core.Dropdown(id=ids["library-designs-list"],
                                      options=[
                                          {"label": ld,
                                           "value": ld} for ld
                                          in ALL_LIBRARY_DESIGNS
                                      ],
                                      multi=True)
                    ]),
                ]),
                html.Br(),
                
                html.Label([
                    "Sort:",
                    core.Dropdown(id=ids['first-sort'],
                        options = [
                            {'label': 'Project', 'value': PINERY_COL.StudyTitle},
                            {'label': 'Run', 'value': BAMQC_COL.Run}
                        ],
                        value=initial_first_sort,
                        searchable=False,
                        clearable=False
                    )
                ]), html.Br(),

                html.Label([
                    "Second Sort:",
                    core.Dropdown(id=ids['second-sort'],
                        options=[
                            {"label": "Total Reads",
                             "value": BAMQC_COL.TotalReads},
                            {"label": "Unmapped Reads",
                             "value": BAMQC_COL.UnmappedReads},
                            {"label": "Non-primary Reads",
                             "value": BAMQC_COL.NonPrimaryReads},
                            {"label": "On-target Reads",
                             "value": BAMQC_COL.ReadsOnTarget},
                            {"label": "Reads per Start Point",
                             "value": BAMQC_COL.ReadsPerStartPoint},
                            {"label": "Mean Insert Size",
                             "value": BAMQC_COL.InsertMean}
                        ],
                        value=initial_second_sort,
                        searchable=False,
                        clearable=False
                    )
                ]), html.Br(),

                html.Label([
                    "Colour by:",
                    core.Dropdown(id=ids['colour-by'],
                        options=shape_or_colour_by,
                        value=initial_colour_col,
                        searchable=False,
                        clearable=False
                    )
                ]), html.Br(),

                html.Label([
                    "Shape by:",
                    core.Dropdown(id=ids['shape-by'],
                        options=shape_or_colour_by,
                        value=initial_shape_col,
                        searchable=False,
                        clearable=False
                    )
                ]), html.Br(),

                html.Label([
                    "Highlight Samples:",
                    core.Dropdown(id=ids['search-sample'],
                        options = [{'label': x, 'value': x} for x in ALL_SAMPLES],
                        multi = True
                    )
                ]), html.Br(),
                
                html.Label([
                    "Show Names:",
                    core.Dropdown(id=ids['show-names'],
                        options=[
                            {'label': 'Sample', 'value': PINERY_COL.SampleName},
                            {'label': 'Group ID', 'value': PINERY_COL.GroupID},
                            {'label': 'None', 'value': 'none'}
                        ],
                        value='none',
                        searchable=False,
                        clearable=False
                    )
                ]),
                html.Br(),

                util.run_range(ids["date-range"]),
                html.Label([
                    "Reads Per Start Point:",
                    core.Slider(id=ids['reads-per-start-point-slider'],
                        min=0,
                        max=20,
                        step=1,
                        marks={str(n): str(n) for n in range(0, 21, 2)},
                        tooltip="always_visible",
                        value=initial_cutoff_rpsp
                    )
                ]), html.Br(),

                html.Label([
                    "Insert Size Mean:",
                    core.Slider(id=ids['insert-size-mean-slider'],
                        min=0,
                        max=500,
                        step=1,
                        marks={str(n): str(n) for n in range(0, 501, 50)},
                        tooltip="always_visible",
                        value=initial_cutoff_insert_size
                    )
                ]), html.Br(),
                
                html.Label([
                    "Total Reads (Passed Filter) * 10^6:",
                    core.Slider(id=ids['passed-filter-reads-slider'],
                        min=0,
                        max=0.5,
                        step=0.005,
                        marks={str(n): str(n)
                               for n in slider_utils.frange(0, 0.51, 0.05)},
                        tooltip="always_visible",
                        value=initial_cutoff_pf_reads
                    )
                ]), html.Br()
            ]),
            html.Div(className='seven columns',
                children=[
                    core.Graph(id=ids['total-reads'],
                        figure=generate_total_reads(empty_bamqc, initial_colour_col,
                                                    initial_shape_col, 'none',
                                                    initial_cutoff_pf_reads)
                    ),
                    core.Graph(id=ids['unmapped-reads'],
                        figure=generate_unmapped_reads(empty_bamqc, initial_colour_col,
                                                     initial_shape_col, 'none')
                    ),
                    core.Graph(id=ids['non-primary-reads'],
                        figure=generate_nonprimary_reads(empty_bamqc, initial_colour_col,
                                                       initial_shape_col, 'none')
                    ),
                    core.Graph(id=ids['on-target-reads'],
                        figure=generate_on_target_reads(empty_bamqc, initial_colour_col,
                                                     initial_shape_col, 'none')
                    ),
                    core.Graph(id=ids['reads-per-start-point'],
                        figure=generate_reads_per_start_point(empty_bamqc,
                                                          initial_colour_col,
                                                          initial_shape_col,
                                                          'none', initial_cutoff_rpsp)
                    ),
                    core.Graph(id=ids['mean-insert-size'],
                        figure=generate_mean_insert_size(empty_bamqc, initial_colour_col,
                               initial_shape_col, 'none',
                                                      initial_cutoff_insert_size)
                    )
                ]),
            ]),
            table_tabs(
                ids["failed-samples"],
                ids["data-table"],
                empty_bamqc,
                ex_table_columns,
                BAMQC_COL.TotalReads,
                [
                    ('Reads per Start Point Cutoff',
                     BAMQC_COL.ReadsPerStartPoint, initial_cutoff_rpsp, False),
                    ('Insert Mean Cutoff', BAMQC_COL.InsertMean,
                     initial_cutoff_insert_size, True),
                    ('Total Reads Cutoff',
                     special_cols["Total Reads (Passed Filter)"],
                     initial_cutoff_pf_reads, True),
                ]
            )
    ])
])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids['total-reads'], 'figure'),
            Output(ids['unmapped-reads'], 'figure'),
            Output(ids['non-primary-reads'], 'figure'),
            Output(ids['on-target-reads'], 'figure'),
            Output(ids['reads-per-start-point'], 'figure'),
            Output(ids['mean-insert-size'], 'figure'),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids['data-table'], 'data'),
            Output("debug", "children")
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
            State(ids['reads-per-start-point-slider'], 'value'),
            State(ids['insert-size-mean-slider'], 'value'),
            State(ids['passed-filter-reads-slider'], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date'),
        ]
    )
    #@dash_app.server.cache.cached(timeout=60)
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
            readsperstartpoint,
            insertsizemean,
            passedfilter,
            start_date,
            end_date):

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
        data = data[data[BAMQC_COL.Run].isin(util.runs_in_range(start_date, end_date))]
        data = fill_in_shape_col(data, shapeby, shape_or_colour_values)
        data = fill_in_colour_col(data, colourby, shape_or_colour_values,
                                  searchsample)

        data = fill_in_size_col(data, searchsample)

        data = data.sort_values(by=[firstsort, secondsort], ascending=False)
        dd = defaultdict(list)
        (failure_df, failure_columns ) =cutoff_table_data(data, [
                ('Reads per Start Point Cutoff',
                 BAMQC_COL.ReadsPerStartPoint, readsperstartpoint, False),
                ('Insert Mean Cutoff', BAMQC_COL.InsertMean, insertsizemean,
                 True),
                ('Total Reads Cutoff', special_cols["Total Reads (Passed "
                                                    "Filter)"], passedfilter,
                 True),
            ])
        return [
            generate_total_reads(data, colourby, shapeby, shownames,
                                 passedfilter),
            generate_unmapped_reads(data, colourby, shapeby, shownames),
            generate_nonprimary_reads(data, colourby, shapeby, shownames),
            generate_on_target_reads(data, colourby, shapeby, shownames),
            generate_reads_per_start_point(data, colourby, shapeby, shownames,
                                       readsperstartpoint),
            generate_mean_insert_size(data, colourby, shapeby, shownames,
                                   insertsizemean),
            failure_columns,
            failure_df.to_dict('records'),
            data.to_dict('records', into=dd),
            click
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
