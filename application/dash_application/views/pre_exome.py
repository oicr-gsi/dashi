import dash_html_components as html
import dash_core_components as core
import dash_table as tabl
from dash.dependencies import Input, Output, State
from . import navbar
from ..dash_id import init_ids
from ..plot_builder import generate
import plotly.graph_objects as go
import pandas as pd
import gsiqcetl.load

# TODO filter down to MiSeq runs only?
bamqc_cols = gsiqcetl.load.bamqc_columns('v1')
bamqc = gsiqcetl.load.bamqc('v1').sort_values(by=[bamqc_cols.Sample, bamqc_cols.TotalReads], ascending=False)


page_name = 'preqc-exome'

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
    return (data[bamqc_column] / data[bamqc_cols.TotalReads]) * 100


def generateTotalReads(current_data, colourby, shownames):
    return generate(
        "Total Reads",
        current_data,
        lambda d: d[bamqc_cols.Sample],
        lambda d: d[bamqc_cols.TotalReads] / pow(10,6),
        "# Reads x 10^6",
        colourby,
        shownames
    )
    

def generateUnmappedReads(current_data, colourby, shownames):
    return generate(
        "Unmapped Reads (%)",
        current_data,
        lambda d: d[bamqc_cols.Sample],
        lambda d: percentageOf(d, bamqc_cols.UnmappedReads),
        "%",
        colourby, 
        shownames
    )

def generateNonprimaryReads(current_data, colourby, shownames):
    return generate(
        "Non-Primary Reads (%)",
        current_data,
        lambda d: d[bamqc_cols.Sample],
        lambda d: percentageOf(d, bamqc_cols.NonPrimaryReads),
        "%",
        colourby,
        shownames
    )

def generateOnTargetReads(current_data, colourby, shownames):
    return generate(
        "On Target Reads (%)",
        current_data,
        lambda d: d[bamqc_cols.Sample],
        lambda d: percentageOf(d, bamqc_cols.ReadsOnTarget),
        "%",
        colourby,
        shownames
    )

def generateReadsPerStartPoint(current_data, colourby, shownames, cutoff_line):
    return generate(
        "Reads per Start Point",
        current_data,
        lambda d: d[bamqc_cols.Sample],
        lambda d: percentageOf(d, bamqc_cols.ReadsPerStartPoint),
        "Fraction",
        colourby,
        shownames,
        cutoff_line
    )

def generateMeanInsertSize(current_data, colourby, shownames, cutoff_line):
    return generate(
        "Mean Insert Size",
        current_data,
        lambda d: d[bamqc_cols.Sample],
        lambda d: d[bamqc_cols.InsertMean],
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
    for failed in data.loc[data[bamqc_cols.ReadsPerStartPoint] < reads_cutoff][bamqc_cols.Sample]:
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
    for failed in data.loc[data[bamqc_cols.InsertMean] < insert_cutoff][bamqc_cols.Sample]:
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
    for failed in data.loc[data[bamqc_cols.TotalReads] < passed_cutoff][bamqc_cols.Sample]:
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
                            {'label': x, 'value': x} for x in bamqc[bamqc_cols.Run].unique()
                        ],
                        value=[x for x in bamqc[bamqc_cols.Run].unique()],
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
                    figure=generateTotalReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 'none')
                ),
                core.Graph(id=ids['unmapped-reads'],
                    figure=generateUnmappedReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 'none')
                ),
                core.Graph(id=ids['non-primary-reads'],
                    figure=generateNonprimaryReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 'none')
                ),
                core.Graph(id=ids['on-target-reads'],
                    figure=generateOnTargetReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 'none')
                ),
                core.Graph(id=ids['reads-per-start-point'],
                    figure=generateReadsPerStartPoint(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 'none', 5)
                ),
                core.Graph(id=ids['mean-insert-size'],
                    figure=generateMeanInsertSize(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 'none', 150)
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
        data = bamqc[bamqc[bamqc_cols.Run].isin(runs)]
        data[bamqc_cols.GroupID] = data[bamqc_cols.GroupID].fillna("")

        # Group by 1st and 2nd sort
        # TODO: this does not appear to work
        # TODO: 2nd sort
        if firstsort == 'run':
            sortby = [bamqc_cols.Run]
        elif firstsort == 'project':
            #TODO: Actually sort on Project
            sortby = [bamqc_cols.Sample]

        if secondsort == 'BAMQC_TOTALREADS':
            sortby.append(bamqc_cols.TotalReads)
        elif secondsort == 'BAMQC_INSERTMEAN':
            sortby.append(bamqc_cols.InsertMean)
        elif secondsort == 'BAMQC_INSERTSD':
            sortby.append(bamqc_cols.InsertSD)
        elif secondsort == 'BAMQC_READSPERSTARTPOINT':
            sortby.append(bamqc_cols.ReadsPerStartPoint)

        if colourby == 'run':
            colourby_strategy = bamqc_cols.Run
        elif colourby == 'project':
            colourby_strategy = data[bamqc_cols.Sample].str[0:4]
            
        # if shapeby == 'run': 
        #     shapeby_strategy = bamqc_cols.Run
        # elif shapeby == 'project':
        #     shapeby_strategy = data[bamqc_cols.Sample].str[0:4]
        data = data.sort_values(by=sortby, ascending=False)

        return [generateTotalReads(data, colourby_strategy, shownames),
            generateUnmappedReads(data, colourby_strategy, shownames),
            generateNonprimaryReads(data, colourby_strategy, shownames),
            generateOnTargetReads(data, colourby_strategy, shownames),
            generateReadsPerStartPoint(data, colourby_strategy, shownames, reads),
            generateMeanInsertSize(data, colourby_strategy, shownames, insertsizemean),
            generateTerminalOutput(data, reads, insertsizemean, passedfilter),
            data.to_dict('records')]
