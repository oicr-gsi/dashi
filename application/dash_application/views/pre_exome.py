from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State
import pandas as pd
from . import navbar
from ..dash_id import init_ids
from ..plot_builder import generate, fill_in_shape_col, fill_in_colour_col
from ..table_builder import build_table
from ..utility import df_manipulation as util
from ..utility import slider_utils
from gsiqcetl import QCETLCache
from gsiqcetl.column import BamQcColumn
import pinery

page_name = 'preqc-exome'

ids = init_ids([
    # Buttons
    'update-button',
    'all-runs',

    # Sidebar controls
    'run-id-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'show-names',
    'reads-per-start-point-slider',
    'insert-size-mean-slider',
    'passed-filter-reads-slider',

    #Graphs
    'total-reads',
    'unmapped-reads',
    'non-primary-reads',
    'on-target-reads',
    'reads-per-start-point',
    'mean-insert-size',

    #Data table
    'data-table'
])

BAMQC_COL = BamQcColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {}


def get_bamqc_data():
    bamqc_df = QCETLCache().bamqc.bamqc
    bamqc_df = util.df_with_normalized_ius_columns(bamqc_df, BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes)

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

shape_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    BAMQC_COL.Run: ALL_RUNS,
}
colour_values = {
    PINERY_COL.StudyTitle: ALL_PROJECTS,
    BAMQC_COL.Run: ALL_RUNS,
}

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
initial_colour_col = BAMQC_COL.Run
initial_shape_col = PINERY_COL.StudyTitle

# Set initial points for graph cutoff lines
initial_cutoff_pf_reads = 0.01
initial_cutoff_insert_size = 150
initial_cutoff_rpsp = 5

bamqc = fill_in_shape_col(bamqc, initial_shape_col, shape_values)
bamqc = fill_in_colour_col(bamqc, initial_colour_col, colour_values)

empty_bamqc = pd.DataFrame(columns=bamqc.columns)


def generate_total_reads(current_data, colourby, shapeby, shownames,
                         cutoff_line):
    return generate(
        "Total Reads",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BAMQC_COL.TotalReads] / pow(10,6),
        "# Reads x 10^6",
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
        lambda d: slider_utils.percentage_of(d, BAMQC_COL.ReadsPerStartPoint, BAMQC_COL.TotalReads),
        "Fraction",
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
        "Fraction",
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
                html.Br(),
                html.Button('Add All', id=ids["all-runs"], className="inline"),
                html.Label([
                    "Run",
                    core.Dropdown(id=ids['run-id-list'],
                        options=[{'label': x, 'value': x} for x in ALL_RUNS],
                        multi=True
                    )
                ]), html.Br(),
                
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
                        options=[
                            {'label': 'Project', 'value': PINERY_COL.StudyTitle},
                            {'label': 'Run', 'value': BAMQC_COL.Run}
                        ],
                        value=initial_colour_col,
                        searchable=False,
                        clearable=False
                    )
                ]), html.Br(),

                html.Label([
                    "Shape by:",
                    core.Dropdown(id=ids['shape-by'],
                        options=[
                            {'label': 'Project', 'value': PINERY_COL.StudyTitle},
                            {'label': 'Run', 'value': BAMQC_COL.Run}
                        ],
                        value=initial_shape_col,
                        searchable=False,
                        clearable=False
                    )
                ]), html.Br(),

                # html.Label([
                #     "Search Sample:",
                #     core.Input(id=ids['search-sample'])
                # ]), html.Br(),
                
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
                ]), html.Br(),

                html.Label([
                    "Reads Per Start Point:",
                    core.Slider(id=ids['reads-per-start-point-slider'],
                        min=0,
                        max=20,
                        step=1,
                        marks={str(n):str(n) for n in range(0, 20, 2)},
                        value=initial_cutoff_rpsp
                    )
                ]), html.Br(),

                html.Label([
                    "Insert Size Mean:",
                    core.Slider(id=ids['insert-size-mean-slider'],
                        min=0,
                        max=500,
                        step=1,
                        marks={str(n):str(n) for n in range(0, 500, 50)},
                        value=initial_cutoff_insert_size
                    )
                ]), html.Br(),
                
                html.Label([
                    "Passed Filter Reads:",
                    core.Slider(id=ids['passed-filter-reads-slider'],
                        min=0,
                        max=0.5,
                        step=0.005,
                        marks={str(n):str(n) for n in slider_utils.frange(0, 0.5, 0.05)},
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

        html.Div(className='data-table',
            children=[
                build_table(ids["data-table"], ex_table_columns, empty_bamqc,
                            BAMQC_COL.TotalReads)
            ]),
    ])])


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids['total-reads'], 'figure'),
            Output(ids['unmapped-reads'], 'figure'),
            Output(ids['non-primary-reads'], 'figure'),
            Output(ids['on-target-reads'], 'figure'),
            Output(ids['reads-per-start-point'], 'figure'),
            Output(ids['mean-insert-size'], 'figure'),
            Output(ids['data-table'], 'data')
        ],
        [Input(ids['update-button'], 'n_clicks')],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            #State(ids['search-sample'], 'value'), #TODO?
            State(ids['show-names'], 'value'),
            State(ids['reads-per-start-point-slider'], 'value'),
            State(ids['insert-size-mean-slider'], 'value'),
            State(ids['passed-filter-reads-slider'], 'value')
        ]
    )
    def update_pressed(click,
            runs, 
            firstsort, 
            secondsort, 
            colourby,
            shapeby,
            #searchsample,
            shownames,
            readsperstartpoint,
            insertsizemean,
            passedfilter):

        # Apply get selected runs
        if not runs:
            data = pd.DataFrame(columns=empty_bamqc.columns)
        else:
            data = bamqc[bamqc[BAMQC_COL.Run].isin(runs)]
        data = fill_in_shape_col(data, shapeby, shape_values)
        data = fill_in_colour_col(data, colourby, colour_values)
        data = data.sort_values(by=[firstsort, secondsort], ascending=False)
        dd = defaultdict(list)

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
            data.to_dict('records', into=dd)
        ]

    @dash_app.callback(
        Output(ids['run-id-list'], 'value'),
        [Input(ids['all-runs'], 'n_clicks')]
    )
    def all_runs_button_clicked(click):
        return [x for x in ALL_RUNS]
