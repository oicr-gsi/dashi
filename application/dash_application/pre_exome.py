import dash_html_components as html
import dash_core_components as core
import dash_table as tabl
from dash.dependencies import Input, Output, State
from .dash_id import init_ids
import plotly.graph_objects as go
import pandas as pd
import gsiqcetl.load
# TODO: develop against gsiqcetl@master rather than v0.5.0 once bamqc is available

# TODO: if this remains necessary i'll be mad
ALL_SYMBOLS = ['circle', 'circle-open', 'circle-dot',
                'circle-open-dot', 'square', 'square-open', 
                'square-dot', 'square-open-dot', 'diamond',
                'diamond-open', 'diamond-dot',
                'diamond-open-dot', 'cross', 'cross-open',
                'cross-dot', 'cross-open-dot', 'x', 'x-open',
                'x-dot', 'x-open-dot', 'triangle-up',
                'triangle-up-open', 'triangle-up-dot',
                'triangle-up-open-dot', 'triangle-down',
                'triangle-down-open', 'triangle-down-dot',
                'triangle-down-open-dot', 'triangle-left',
                'triangle-left-open', 'triangle-left-dot',
                'triangle-left-open-dot', 'triangle-right',
                'triangle-right-open', 'triangle-right-dot',
                'triangle-right-open-dot', 'triangle-ne', 
                'triangle-ne-open', 'triangle-ne-dot',
                'triangle-ne-open-dot', 'triangle-se',
                'triangle-se-open', 'triangle-se-dot',
                'triangle-se-open-dot', 'triangle-sw',
                'triangle-sw-open', 'triangle-sw-dot',
                'triangle-sw-open-dot', 'triangle-nw',
                'triangle-nw-open', 'triangle-nw-dot',
                'triangle-nw-open-dot', 'pentagon', 
                'pentagon-open', 'pentagon-dot',
                'pentagon-open-dot', 'hexagon', 'hexagon-open',
                'hexagon-dot', 'hexagon-open-dot',
                'hexagon2', 'hexagon2-open', 'hexagon2-dot',
                'hexagon2-open-dot', 'octagon', 
                'octagon-open', 'octagon-dot', 
                'octagon-open-dot', 'star',  'star-open',
                'star-dot', 'star-open-dot', 'hexagram',
                'hexagram-open', 'hexagram-dot',
                'hexagram-open-dot', 'star-triangle-up', 
                'star-triangle-up-open', 'star-triangle-up-dot',
                'star-triangle-up-open-dot', 'star-triangle-down',
                'star-triangle-down-open',
                'star-triangle-down-dot',
                'star-triangle-down-open-dot', 'star-square', 
                'star-square-open','star-square-dot',
                'star-square-open-dot', 'star-diamond', 
                'star-diamond-open', 'star-diamond-dot',
                'star-diamond-open-dot', 'diamond-tall',
                'diamond-tall-open', 'diamond-tall-dot',
                'diamond-tall-open-dot', 'diamond-wide', 
                'diamond-wide-open', 'diamond-wide-dot',
                'diamond-wide-open-dot', 'hourglass', 
                'hourglass-open', 'bowtie', 'bowtie-open',
                'circle-cross', 'circle-cross-open', 'circle-x',
                'circle-x-open', 'square-cross', 
                'square-cross-open', 'square-x', 'square-x-open',
                'diamond-cross', 'diamond-cross-open', 
                'diamond-x', 'diamond-x-open', 'cross-thin', 
                'cross-thin-open', 'x-thin', 'x-thin-open', 
                'asterisk', 'asterisk-open', 'hash', 
                'hash-open', 'hash-dot', 'hash-open-dot', 
                'y-up', 'y-up-open', 'y-down', 
                'y-down-open', 'y-left', 'y-left-open',
                'y-right', 'y-right-open', 'line-ew', 
                'line-ew-open', 'line-ns', 'line-ns-open',
                'line-ne', 'line-ne-open', 'line-nw', 
                'line-nw-open']

bamqc = gsiqcetl.load.bamqc('v1')
bamqc_cols = gsiqcetl.load.bamqc_columns('v1')

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

def frange(min, max, step):
    range = []
    i = min
    while i <= max:
        range.append(round(i, 2))
        i += step
    return range


def percentageOf(data, bamqc_column):
    return (data[bamqc_column] / data[bamqc_cols.TotalReads]) * 100

def generateTotalReads(current_data, colourby, shownames):
    traces = []
    current_data[bamqc_cols.GroupID] = current_data[bamqc_cols.GroupID].fillna("")
    i = 0
    if shownames == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in current_data.groupby(colourby):
        if shownames == 'sample':
            text_content = data[bamqc_cols.Sample]
        elif shownames == 'group-id':
            text_content = data[bamqc_cols.GroupID]
        else:
            text_content = None
    for name, data in current_data.groupby(colourby):
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = data[bamqc_cols.TotalReads] / pow(10,6),
            name = name,
            mode = marker_mode,
            text = text_content,
            textposition = "top right",
            marker={
                "symbol": ALL_SYMBOLS[i]
            }
        )
        if i == len(ALL_SYMBOLS):
            i = 0
        else:
            i += 1
        traces.append(graph)
    return go.Figure(
        data = traces,
        layout = go.Layout(
            title="Total Reads", #TODO: what does 'passed filter' mean
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

def generateUnmappedReads(current_data, colourby, shownames):
    traces = []
    current_data[bamqc_cols.GroupID] = current_data[bamqc_cols.GroupID].fillna("")
    if shownames == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in current_data.groupby(colourby):
        if shownames == 'sample':
            text_content = data[bamqc_cols.Sample]
        elif shownames == 'group-id':
            text_content = data[bamqc_cols.GroupID]
        else:
            text_content = None
    for name, data in current_data.groupby(colourby):
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = percentageOf(data, bamqc_cols.UnmappedReads),
            name = name,
            mode = marker_mode,
            text = text_content,
            textposition = "top right"
        )
        traces.append(graph)
    return go.Figure(
        data=traces,
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

def generateNonprimaryReads(current_data, colourby, shownames):
    traces = []
    current_data[bamqc_cols.GroupID] = current_data[bamqc_cols.GroupID].fillna("")
    if shownames == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in current_data.groupby(colourby):
        if shownames == 'sample':
            text_content = data[bamqc_cols.Sample]
        elif shownames == 'group-id':
            text_content = data[bamqc_cols.GroupID]
        else:
            text_content = None
    for name, data in current_data.groupby(colourby):
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = percentageOf(data, bamqc_cols.NonPrimaryReads),
            name = name,
            mode = marker_mode,
            text = text_content,
            textposition = "top right"
        )
        traces.append(graph)
    return go.Figure(
        data=traces,
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

def generateOnTargetReads(current_data, colourby, shownames):
    traces = []
    current_data[bamqc_cols.GroupID] = current_data[bamqc_cols.GroupID].fillna("")
    if shownames == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in current_data.groupby(colourby):
        if shownames == 'sample':
            text_content = data[bamqc_cols.Sample]
        elif shownames == 'group-id':
            text_content = data[bamqc_cols.GroupID]
        else:
            text_content = None
    for name, data in current_data.groupby(colourby):
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = data[bamqc_cols.TotalReads] / pow(10,6),
            name = name,
            mode = marker_mode,
            text = text_content,
            textposition = "top right"
        )
        traces.append(graph)
    return go.Figure(
        data=traces,
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

#TODO: Could i abstract out the cutoff line behaviour? also the show names behaviour. Everything really
#TODO: generalize x values for both graphs
def generateReadsPerStartPoint(current_data, colourby, shownames, cutoff_line):
    traces = []
    current_data[bamqc_cols.GroupID] = current_data[bamqc_cols.GroupID].fillna("")
    if shownames == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in current_data.groupby(colourby):
        if shownames == 'sample':
            text_content = data[bamqc_cols.Sample]
        elif shownames == 'group-id':
            text_content = data[bamqc_cols.GroupID]
        else:
            text_content = None
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = percentageOf(data, bamqc_cols.ReadsPerStartPoint),
            mode = marker_mode,
            textposition="top right",
            text = text_content,
            name = name
        )
        traces.append(graph)
    traces.append(go.Scattergl( # Cutoff line
        x=current_data[bamqc_cols.Sample],
        y=[cutoff_line] * len(current_data),
        mode="lines",
        line={"width": 3, "color": "black", "dash": "dash"}
    ))
    return go.Figure(
        data=traces,
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

def generateMeanInsertSize(current_data, colourby, shownames, cutoff_line):
    traces = []
    current_data[bamqc_cols.GroupID] = current_data[bamqc_cols.GroupID].fillna("")
    if shownames == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in current_data.groupby(colourby):
        if shownames == 'sample':
            text_content = data[bamqc_cols.Sample]
        elif shownames == 'group-id':
            text_content = data[bamqc_cols.GroupID]
        else:
            text_content = None
    for name, data in current_data.groupby(colourby):
        graph = go.Scattergl(
            x = data[bamqc_cols.Sample],
            y = data[bamqc_cols.InsertMean],
            name = name,
            mode = marker_mode,
            text = text_content,
            textposition = "top right"
        )
        traces.append(graph)
    traces.append(go.Scattergl( # Cutoff line
        x=current_data[bamqc_cols.Sample],
        y=[cutoff_line] * len(current_data),
        mode="lines",
        line={"width": 3, "color":"black", "dash":"dash"}
    ))
    return go.Figure(
        data=traces,
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

                # html.Label([
                #     "2nd Sort:",
                #     core.Dropdown(id=ids['second-sort'],
                #         options = [
                #             # TODO: Friendlier names
                #             {'label': 'BAMQC_TOTALREADS', 'value': 'BAMQC_TOTALREADS'},
                #             {'label': 'BAMQC_INSERTMEAN', 'value': 'BAMQC_INSERTMEAN'},
                #             {'label': 'BAMQC_INSERTSD', 'value': 'BAMQC_INSERTSD'},
                #             {'label': 'BAMQC_READSPERSTARTPOINT', 'value': 'BAMQC_READSPERSTARTPOINT'}
                #         ],
                #         value = 'BAMQC_TOTALREADS',
                #         searchable = False,
                #         clearable = False
                #     )
                # ]), html.Br(),

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

                # TODO: there's no range() for floats
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
        html.Div(className='graphs',
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
            ]),
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
        # State(ids['second-sort'], 'value'),
        State(ids['colour-by'], 'value'),
        # State(ids['shape-by'], 'value'), #TODO
        # State(ids['search-sample'], 'value'), #TODO
        State(ids['show-names'], 'value'),
        State(ids['reads-per-start-point-slider'], 'value'),
        State(ids['insert-size-mean-slider'], 'value'),
        State(ids['passed-filter-reads-slider'], 'value')])
    def updatePressed(click, 
            runs, 
            firstsort, 
            # secondsort, 
            colourby,
            # shapeby,
            # searchsample,
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
            sortby = data[bamqc_cols.Sample].str[0:4] #TODO: find a sane way to split on '_'

        if colourby == 'run':
            colourby_strategy = bamqc_cols.Run
        elif colourby == 'project':
            colourby_strategy = data[bamqc_cols.Sample].str[0:4]
            
        # if shapeby == 'run': #TODO: there's 1700+ runs, not gonna be enough symbols
        #     shapeby_strategy = bamqc_cols.Run
        # elif shapeby == 'project':
        #     shapeby_strategy = data[bamqc_cols.Sample].str[0:4]
        
        data = data.groupby(sortby).apply(lambda x:x)

        return [generateTotalReads(data, colourby_strategy, shownames),
            generateUnmappedReads(data, colourby_strategy, shownames),
            generateNonprimaryReads(data, colourby_strategy, shownames),
            generateOnTargetReads(data, colourby_strategy, shownames),
            generateReadsPerStartPoint(data, colourby_strategy, shownames, reads),
            generateMeanInsertSize(data, colourby_strategy, shownames, insertsizemean),
            generateTerminalOutput(data, reads, insertsizemean, passedfilter),]