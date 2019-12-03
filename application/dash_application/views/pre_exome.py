import dash_html_components as html
import dash_core_components as core
import dash_table as tabl
from dash.dependencies import Input, Output, State
from . import navbar
from ..dash_id import init_ids
from ..plot_builder import generate
from ..utility import df_manipulation as util
import plotly.graph_objects as go
import pandas as pd
from gsiqcetl import QCETLCache
from gsiqcetl.column import BamQcColumn
import pinery

page_name = 'preexome'

ids = init_ids([
    # Buttons
    'update-button',
    'download-button',

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

    # Terminal output
    'terminal-output',

    #Data table
    'data-table'
])

BAMQC_COL = BamQcColumn
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn

special_cols = {} #TODO 

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

# TODO: move elsewhere
def frange(min, max, step):
    range = []
    i = min
    while i <= max:
        range.append(round(i, 2))
        i += step
    return range

# TODO: move elsewhere
def percentageOf(data, bamqc_column):
    return (data[bamqc_column] / data[BAMQC_COL.TotalReads]) * 100


def generateTotalReads(current_data, colourby, shownames):
    return generate(
        "Total Reads",
        current_data,
        lambda d: d[BAMQC_COL.Sample],
        lambda d: d[BAMQC_COL.TotalReads] / pow(10,6),
        "# Reads x 10^6",
        colourby,
        shownames
    )
    

def generateUnmappedReads(current_data, colourby, shownames):
    return generate(
        "Unmapped Reads (%)",
        current_data,
        lambda d: d[BAMQC_COL.Sample],
        lambda d: percentageOf(d, BAMQC_COL.UnmappedReads),
        "%",
        colourby, 
        shownames
    )

def generateNonprimaryReads(current_data, colourby, shownames):
    return generate(
        "Non-Primary Reads (%)",
        current_data,
        lambda d: d[BAMQC_COL.Sample],
        lambda d: percentageOf(d, BAMQC_COL.NonPrimaryReads),
        "%",
        colourby,
        shownames
    )

def generateOnTargetReads(current_data, colourby, shownames):
    return generate(
        "On Target Reads (%)",
        current_data,
        lambda d: d[BAMQC_COL.Sample],
        lambda d: percentageOf(d, BAMQC_COL.ReadsOnTarget),
        "%",
        colourby,
        shownames
    )

def generateReadsPerStartPoint(current_data, colourby, shownames, cutoff_line):
    return generate(
        "Reads per Start Point",
        current_data,
        lambda d: d[BAMQC_COL.Sample],
        lambda d: percentageOf(d, BAMQC_COL.ReadsPerStartPoint),
        "Fraction",
        colourby,
        shownames,
        cutoff_line
    )

def generateMeanInsertSize(current_data, colourby, shownames, cutoff_line):
    return generate(
        "Mean Insert Size",
        current_data,
        lambda d: d[BAMQC_COL.Sample],
        lambda d: d[BAMQC_COL.InsertMean],
        "Fraction",
        colourby,
        shownames,
        cutoff_line
    )

# TODO: Abstract repeated behaviour
def generateTerminalOutput(data, reads_cutoff, insert_cutoff, passed_cutoff):
    if data.empty:
        return "No data!"

    output = ""

    output += "$failed_rpsp\n"
    newline = False
    linenumber = 0
    for failed in data.loc[data[BAMQC_COL.ReadsPerStartPoint] < reads_cutoff][BAMQC_COL.Sample]:
        if not newline:
            output += "[{0}] ".format(linenumber)
        output += "\"" + failed + "\"\t\t"
        if newline:
            output += "\n"
        newline = not newline
        linenumber += 1

    output += "\n$failed_insr\n"
    newline = False
    linenumber = 0
    for failed in data.loc[data[BAMQC_COL.InsertMean] < insert_cutoff][BAMQC_COL.Sample]:
        if not newline:
            output += "[{0}] ".format(linenumber)
        output += "\"" + failed + "\"\t\t"
        if newline:
            output += "\n"
        newline = not newline
        linenumber += 1

    output += "\n$failed_ptden\n" # TODO: Not sure this is calculated correctly
    newline = False
    linenumber = 0
    for failed in data.loc[data[BAMQC_COL.TotalReads] < passed_cutoff][BAMQC_COL.Sample]:
        if not newline:
            output += "[{0}] ".format(linenumber)
        output += "\"" + failed + "\"\t\t"
        if newline:
            output += "\n"
        newline = not newline
        linenumber += 1

    return output

def generateDebugLine(click, runs, firstsort, secondsort, colourby,
                shapeby,
                searchsample,
                shownames,
                reads,
                insertsizemean,
                passedfilter,
                colourby_strategy,
                sortby,
                data):
    return "".join(v for k, v in locals().items())

layout = core.Loading(fullscreen=True, type="cube", children=[html.Div(className='body',
    children=[
        navbar("Pre-Exome"),
        html.Div(className='row flex-container',
                 children=[
                     html.Div(className='sidebar four columns',
            children=[
                # As far as I can tell, there's no named attribute for button text
                # It's always positional
                html.Button('Update', id=ids['update-button']),
                html.Button('Download', id=ids['download-button']),
                html.Br(),


                html.Label([
                    "Run ID", 
                    core.Dropdown(id=ids['run-id-list'],
                        options = [
                            {'label': x, 'value': x} for x in bamqc[BAMQC_COL.Run].unique()
                        ],
                        value=[x for x in bamqc[BAMQC_COL.Run].unique()],
                        multi=True
                    )
                ]), html.Br(),
                
                html.Label([
                    "Sort:",
                    core.Dropdown(id=ids['first-sort'],
                        options = [
                            {'label': 'Project', 'value': 'project'},
                            {'label': 'Run', 'value': 'run'}
                        ],
                        value = 'project',
                        searchable = False,
                        clearable = False
                    )
                ]), html.Br(),

                html.Label([
                    "2nd Sort:",
                    core.Dropdown(id=ids['second-sort'],
                        options = [
                            # TODO: Friendlier names
                            {'label': 'BAMQC_TOTALREADS', 'value': 'BAMQC_TOTALREADS'},
                            {'label': 'BAMQC_INSERTMEAN', 'value': 'BAMQC_INSERTMEAN'},
                            {'label': 'BAMQC_INSERTSD', 'value': 'BAMQC_INSERTSD'},
                            {'label': 'BAMQC_READSPERSTARTPOINT', 'value': 'BAMQC_READSPERSTARTPOINT'}
                        ],
                        value = 'BAMQC_TOTALREADS',
                        searchable = False,
                        clearable = False
                    )
                ]), html.Br(),

                html.Label([
                    "Colour/Shape by:",
                    core.Dropdown(id=ids['colour-by'],
                        options = [
                            {'label': 'Project', 'value': 'project'},
                            {'label': 'Run', 'value': 'run'}
                        ],
                        value = 'project',
                        searchable = False,
                        clearable = False
                    )
                ]), html.Br(),

                # html.Label([
                #     "Shape by:",
                #     core.Dropdown(id=ids['shape-by'],
                #         options = [
                #             {'label': 'Project', 'value': 'project'},
                #             {'label': 'Run', 'value': 'run'}
                #         ],
                #         value = 'project',
                #         searchable = False,
                #         clearable = False
                #     )
                # ]), html.Br(),

                # html.Label([
                #     "Search Sample:",
                #     core.Input(id=ids['search-sample'])
                # ]), html.Br(),
                
                html.Label([
                    "Show Names:",
                    core.Dropdown(id=ids['show-names'],
                        options = [
                            {'label': 'Sample', 'value': 'sample'},
                            {'label': 'groupID', 'value': 'group-id'},
                            {'label': 'None', 'value': 'none'}
                        ],
                        value = 'none',
                        searchable = False,
                        clearable = False
                    )
                ]), html.Br(),

                html.Label([
                    "Reads Per Start Point:",
                    core.Slider(id=ids['reads-per-start-point-slider'],
                        min = 0,
                        max = 20,
                        step = 1,
                        marks = {str(n):str(n) for n in range(0, 20, 2)},
                        value = 5
                    )
                ]), html.Br(),

                html.Label([
                    "Insert Size Mean:",
                    core.Slider(id=ids['insert-size-mean-slider'],
                        min = 0,
                        max = 500,
                        step = 1,
                        marks = {str(n):str(n) for n in range(0, 500, 50)},
                        value = 150
                    )
                ]), html.Br(),
                
                html.Label([
                    "Passed Filter Reads:",
                    core.Slider(id=ids['passed-filter-reads-slider'],
                        min = 0,
                        max = 0.5,
                        step = 0.005,
                        marks = {str(n):str(n) for n in frange(0, 0.5, 0.05)},
                        value = 0.01
                    )
                ]), html.Br()
            ]),
        html.Div(className='seven columns',
            children=[
                core.Graph(id=ids['total-reads'],
                    figure=generateTotalReads(bamqc, bamqc[PINERY_COL.StudyTitle], 'none')
                ),
                core.Graph(id=ids['unmapped-reads'],
                    figure=generateUnmappedReads(bamqc, bamqc[PINERY_COL.StudyTitle], 'none')
                ),
                core.Graph(id=ids['non-primary-reads'],
                    figure=generateNonprimaryReads(bamqc, bamqc[PINERY_COL.StudyTitle], 'none')
                ),
                core.Graph(id=ids['on-target-reads'],
                    figure=generateOnTargetReads(bamqc, bamqc[PINERY_COL.StudyTitle], 'none')
                ),
                core.Graph(id=ids['reads-per-start-point'],
                    figure=generateReadsPerStartPoint(bamqc, bamqc[PINERY_COL.StudyTitle], 'none', 5)
                ),
                core.Graph(id=ids['mean-insert-size'],
                    figure=generateMeanInsertSize(bamqc, bamqc[PINERY_COL.StudyTitle], 'none', 150)
                )
            ]),
                     ]),
        html.Div(className='terminal-output',
            children=[
                html.Pre(generateTerminalOutput(bamqc, 5, 150, 0.01),  # TODO: magic numbers!! make constants
                         id=ids['terminal-output'],
                )
            ]),
        html.Div(className='data-table',
            children=[
                tabl.DataTable(id=ids['data-table'],
                    columns=[{"name": i, "id": i} for i in bamqc.columns],
                    data=bamqc.to_dict('records'),
                    export_format="csv"
                )
            ]),
    ])])

def init_callbacks(dash_app):
    @dash_app.callback(
        [Output(ids['total-reads'], 'figure'),
        Output(ids['unmapped-reads'], 'figure'),
        Output(ids['non-primary-reads'], 'figure'),
        Output(ids['on-target-reads'], 'figure'),
        Output(ids['reads-per-start-point'], 'figure'),
        Output(ids['mean-insert-size'], 'figure'),
        Output(ids['terminal-output'], 'value'),
        Output(ids['data-table'], 'data')],
        [Input(ids['update-button'], 'n_clicks')],
        [State(ids['run-id-list'], 'value'),
        State(ids['first-sort'], 'value'),
        State(ids['second-sort'], 'value'),
        State(ids['colour-by'], 'value'),
        # State(ids['shape-by'], 'value'), #TODO?
        # State(ids['search-sample'], 'value'), #TODO?
        State(ids['show-names'], 'value'),
        State(ids['reads-per-start-point-slider'], 'value'),
        State(ids['insert-size-mean-slider'], 'value'),
        State(ids['passed-filter-reads-slider'], 'value')])
    def updatePressed(click, 
            runs, 
            firstsort, 
            secondsort, 
            colourby,
            # shapeby,
            # searchsample,
            shownames,
            reads,
            insertsizemean,
            passedfilter):

        # Apply get selected runs
        data = bamqc[bamqc[BAMQC_COL.Run].isin(runs)]

        # Group by 1st and 2nd sort
        # TODO: this does not appear to work
        # TODO: 2nd sort
        if firstsort == 'run':
            sortby = [BAMQC_COL.Run]
        elif firstsort == 'project':
            #TODO: Actually sort on Project
            sortby = [BAMQC_COL.Sample]

        if secondsort == 'BAMQC_TOTALREADS':
            sortby.append(BAMQC_COL.TotalReads)
        elif secondsort == 'BAMQC_INSERTMEAN':
            sortby.append(BAMQC_COL.InsertMean)
        elif secondsort == 'BAMQC_INSERTSD':
            sortby.append(BAMQC_COL.InsertSD)
        elif secondsort == 'BAMQC_READSPERSTARTPOINT':
            sortby.append(BAMQC_COL.ReadsPerStartPoint)

        if colourby == 'run':
            colourby_strategy = BAMQC_COL.Run
        elif colourby == 'project':
            colourby_strategy = data[PINERY_COL.StudyTitle]
            
        # if shapeby == 'run': 
        #     shapeby_strategy = BAMQC_COL.Run
        # elif shapeby == 'project':
        #     shapeby_strategy = data[PINERY_COL.StudyTitle]
        data = data.sort_values(by=sortby, ascending=False)

        return [generateTotalReads(data, colourby_strategy, shownames),
            generateUnmappedReads(data, colourby_strategy, shownames),
            generateNonprimaryReads(data, colourby_strategy, shownames),
            generateOnTargetReads(data, colourby_strategy, shownames),
            generateReadsPerStartPoint(data, colourby_strategy, shownames, reads),
            generateMeanInsertSize(data, colourby_strategy, shownames, insertsizemean),
            generateTerminalOutput(data, reads, insertsizemean, passedfilter),
            data.to_dict('records')]
