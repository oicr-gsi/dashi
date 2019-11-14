import dash_html_components as html
import dash_core_components as core
import dash_table as tabl
from dash.dependencies import Input, Output, State
from .dash_id import init_ids
import plotly.graph_objects as go
import pandas as pd
import gsiqcetl.load
# TODO: develop against gsiqcetl@master rather than v0.5.0 once bamqc is available

bamqc = gsiqcetl.load.bamqc('v1')
bamqc_cols = gsiqcetl.load.bamqc_columns('v1')
# TODO: group by project

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

def percentageOf(data, bamqc_column):
    return (data[bamqc_column] / data[bamqc_cols.TotalReads]) * 100

def generateTotalReads(current_data, colourby):
    traces = []
    for name, data in current_data.groupby(colourby):
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = data[bamqc_cols.TotalReads] / pow(10,6),
            name = name,
            mode = 'markers'
        )
        traces.append(graph)
    return go.Figure(
        data = traces,
        # data=[for name, data in current_data.groupby(colourby):
        #     go.Scattergl(
        #     x=data[bamqc_cols.Sample],
        #     y=data[bamqc_cols.TotalReads] / pow(10,6),
        #     name=name,
        #     mode='markers',
        #     marker={
        #         'size': 1,
        #         'line': {'width': 0.5}
        #     }
        # )],
        layout = go.Layout(
            title="Total Reads", #what does 'passed filter' mean
            xaxis={'visible': False,
                'rangemode': 'normal',
                'autorange': True},
            yaxis={
                'title': {
                    'text': '# Reads x 10^6'
                }
            }
        )
    )

def generateUnmappedReads(current_data, colourby):
    return go.Figure(
        data=[go.Scattergl(
            x=current_data[bamqc_cols.Sample],
            y=percentageOf(current_data, bamqc_cols.UnmappedReads),
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
        )],
        layout = go.Layout(
            title="Unmapped Reads (%)",
            xaxis={'visible': False},
            yaxis={
                'title': {
                    'text': '%'
                }
            }
        )
    )

def generateNonprimaryReads(current_data, colourby):
    return go.Figure(
        data=[go.Scattergl(
            x=current_data[bamqc_cols.Sample],
            y=percentageOf(current_data, bamqc_cols.NonPrimaryReads),
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
        )],
        layout = go.Layout(
            title="Non-Primary Reads (%)",
            xaxis={'visible': False},
            yaxis={
                'title':{
                    'text': '%'
                }
            }
        )
    )

def generateOnTargetReads(current_data, colourby):
    return go.Figure(
        data=[go.Scattergl(
            x=current_data[bamqc_cols.Sample],
            y=percentageOf(current_data, bamqc_cols.ReadsOnTarget),
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
        )],
        layout = go.Layout(
            title="On Target Reads (%)",
            xaxis={'visible': False},
            yaxis={
                'title':{
                    'text': '%'
                }
            }
        )
    )

#TODO: Could i abstract out the cutoff line behaviour?
#TODO: generalize x values for both graphs
def generateReadsPerStartPoint(current_data, colourby, cutoff_line):
    return go.Figure(
        data=[go.Scattergl( # Actual data
            x=current_data[bamqc_cols.Sample],
            y=percentageOf(current_data, bamqc_cols.ReadsPerStartPoint),
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
        ), go.Scattergl( # Cutoff line
            x=current_data[bamqc_cols.Sample],
            y=[cutoff_line] * len(current_data),
            mode="markers+lines", #TODO: ???
            line={"width": 3, "color": "black", "dash": "dash"}
        )],
        layout = go.Layout(
            title="Reads per Start Point",
            xaxis={'visible': False},
            yaxis={
                'title':{
                    'text': 'Fraction'
                }
            }
        )
    )

def generateMeanInsertSize(current_data, colourby, cutoff_line):
    return go.Figure(
        data=[go.Scattergl( # Actual Data
            x=current_data[bamqc_cols.Sample],
            y=current_data[bamqc_cols.InsertMean],
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
        ), go.Scattergl( # Cutoff line
            x=current_data[bamqc_cols.Sample],
            y=[cutoff_line] * len(current_data),
            mode="markers+lines",
            line={"width": 3, "color":"black", "dash":"dash"}
        )
    ],
    layout = go.Layout(
        title="Mean Insert Size",
        xaxis={'visible': False},
            yaxis={
                'title':{
                    'text': 'Fraction'
                }
            }
        )
    )

# TODO: Abstract repeated behaviour
def generateTerminalOutput(data, reads_cutoff, insert_cutoff, passed_cutoff):
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

layout = html.Div(className='body',
    children=[
        html.Div(className='sidebar',
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
                    "1st Sort:",
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
                    "Colour by:",
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

                html.Label([
                    "Shape by:",
                    core.Dropdown(id=ids['shape-by'],
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
                    "Search Sample:",
                    core.Input(id=ids['search-sample'])
                ]), html.Br(),
                
                html.Label([
                    "Show Names:",
                    core.Dropdown(id=ids['show-names'],
                        options = [
                            {'label': 'Sample', 'value': 'sample'},
                            {'label': 'groupID', 'value': 'groupID'},
                            {'label': 'None', 'value': 'none'}
                        ],
                        value = 'none',
                        searchable = False,
                        clearable = False
                    )
                ]), html.Br(),

                # TODO: there's no range() for floats
                html.Label([
                    "Reads Per Start Point:",
                    core.Slider(id=ids['reads-per-start-point-slider'],
                        min = 0,
                        max = 20,
                        step = 1,
                        #marks = {str(n):str(n) for n in range(0, 20, 2)},
                        value = 5
                    )
                ]), html.Br(),

                html.Label([
                    "Insert Size Mean:",
                    core.Slider(id=ids['insert-size-mean-slider'],
                        min = 0,
                        max = 500,
                        step = 1,
                        #marks = {str(n):str(n) for n in range(0, 500, 50)},
                        value = 150
                    )
                ]), html.Br(),
                
                html.Label([
                    "Passed Filter Reads:",
                    core.Slider(id=ids['passed-filter-reads-slider'],
                        min = 0,
                        max = 0.5,
                        step = 0.005,
                        #marks = {str(n):str(n) for n in range(0, 0.5, 0.05)},
                        value = 0.01
                    )
                ]), html.Br()
            ]),
        html.Div(className='graphs',
            children=[
                core.Graph(id=ids['total-reads'],
                    figure=generateTotalReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4])
                ),
                core.Graph(id=ids['unmapped-reads'],
                    figure=generateUnmappedReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4])
                ),
                core.Graph(id=ids['non-primary-reads'],
                    figure=generateNonprimaryReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4])
                ),
                core.Graph(id=ids['on-target-reads'],
                    figure=generateOnTargetReads(bamqc, bamqc[bamqc_cols.Sample].str[0:4])
                ),
                core.Graph(id=ids['reads-per-start-point'],
                    figure=generateReadsPerStartPoint(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 5)
                ),
                core.Graph(id=ids['mean-insert-size'],
                    figure=generateMeanInsertSize(bamqc, bamqc[bamqc_cols.Sample].str[0:4], 150)
                )
            ]),
        html.Div(className='terminal-output',
            children=[
                core.Textarea(id=ids['terminal-output'],
                    readOnly=True,
                    value=generateTerminalOutput(bamqc, 5, 150, 0.01) # TODO: magic numbers!! make constants
                )
            ]),
        html.Div(className='data-table',
            children=[
                tabl.DataTable(id=ids['data-table'])
            ])
    ]) 

def init_callbacks(dash_app):
    @dash_app.callback(
        [Output(ids['total-reads'], 'figure'),
        Output(ids['unmapped-reads'], 'figure'),
        Output(ids['non-primary-reads'], 'figure'),
        Output(ids['on-target-reads'], 'figure'),
        Output(ids['reads-per-start-point'], 'figure'),
        Output(ids['mean-insert-size'], 'figure'),
        Output(ids['terminal-output'], 'value')],
        [Input(ids['update-button'], 'n_clicks')],
        [State(ids['run-id-list'], 'value'),
        State(ids['first-sort'], 'value'),
        State(ids['second-sort'], 'value'),
        State(ids['colour-by'], 'value'),
        State(ids['shape-by'], 'value'),
        State(ids['search-sample'], 'value'),
        State(ids['show-names'], 'value'),
        State(ids['reads-per-start-point-slider'], 'value'),
        State(ids['insert-size-mean-slider'], 'value'),
        State(ids['passed-filter-reads-slider'], 'value')])
    def updatePressed(click, 
            runs, 
            firstsort, 
            secondsort, 
            colourby,
            shapeby,
            searchsample,
            shownames,
            reads,
            insertsizemean,
            passedfilter):

        # Apply get selected runs
        data = bamqc[bamqc[bamqc_cols.Run].isin(runs)]

        # Group by 1st and 2nd sort
        # TODO: this does not appear to work
        # TODO: 2nd sort
        if firstsort == 'run':
            sortby = bamqc_cols.Run
        elif firstsort == 'project':
            sortby = data[bamqc_cols.Sample].str[0:4]

        if colourby == 'run':
            colourby_strategy = bamqc_cols.Run
        elif colourby == 'project':
            colourby_strategy = data[bamqc_cols.Sample].str[0:4]
            
        data = data.groupby(sortby).apply(lambda x:x)

        return [generateTotalReads(data, colourby_strategy),
            generateUnmappedReads(data, colourby_strategy),
            generateNonprimaryReads(data, colourby_strategy),
            generateOnTargetReads(data, colourby_strategy),
            generateReadsPerStartPoint(data, colourby_strategy, reads),
            generateMeanInsertSize(data, colourby_strategy, insertsizemean),
            generateTerminalOutput(data, reads, insertsizemean, passedfilter)]

