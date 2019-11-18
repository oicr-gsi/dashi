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
ALL_SYMBOLS = [0, 'circle', 100, 'circle-open', 200, 'circle-dot', 300,
                'circle-open-dot', 1, 'square', 101, 'square-open', 201,
                'square-dot', 301, 'square-open-dot', 2, 'diamond', 102,
                'diamond-open', 202, 'diamond-dot', 302,
                'diamond-open-dot', 3, 'cross', 103, 'cross-open', 203,
                'cross-dot', 303, 'cross-open-dot', 4, 'x', 104, 'x-open',
                204, 'x-dot', 304, 'x-open-dot', 5, 'triangle-up', 105,
                'triangle-up-open', 205, 'triangle-up-dot', 305,
                'triangle-up-open-dot', 6, 'triangle-down', 106,
                'triangle-down-open', 206, 'triangle-down-dot', 306,
                'triangle-down-open-dot', 7, 'triangle-left', 107,
                'triangle-left-open', 207, 'triangle-left-dot', 307,
                'triangle-left-open-dot', 8, 'triangle-right', 108,
                'triangle-right-open', 208, 'triangle-right-dot', 308,
                'triangle-right-open-dot', 9, 'triangle-ne', 109,
                'triangle-ne-open', 209, 'triangle-ne-dot', 309,
                'triangle-ne-open-dot', 10, 'triangle-se', 110,
                'triangle-se-open', 210, 'triangle-se-dot', 310,
                'triangle-se-open-dot', 11, 'triangle-sw', 111,
                'triangle-sw-open', 211, 'triangle-sw-dot', 311,
                'triangle-sw-open-dot', 12, 'triangle-nw', 112,
                'triangle-nw-open', 212, 'triangle-nw-dot', 312,
                'triangle-nw-open-dot', 13, 'pentagon', 113,
                'pentagon-open', 213, 'pentagon-dot', 313,
                'pentagon-open-dot', 14, 'hexagon', 114, 'hexagon-open',
                214, 'hexagon-dot', 314, 'hexagon-open-dot', 15,
                'hexagon2', 115, 'hexagon2-open', 215, 'hexagon2-dot',
                315, 'hexagon2-open-dot', 16, 'octagon', 116,
                'octagon-open', 216, 'octagon-dot', 316,
                'octagon-open-dot', 17, 'star', 117, 'star-open', 217,
                'star-dot', 317, 'star-open-dot', 18, 'hexagram', 118,
                'hexagram-open', 218, 'hexagram-dot', 318,
                'hexagram-open-dot', 19, 'star-triangle-up', 119,
                'star-triangle-up-open', 219, 'star-triangle-up-dot', 319,
                'star-triangle-up-open-dot', 20, 'star-triangle-down',
                120, 'star-triangle-down-open', 220,
                'star-triangle-down-dot', 320,
                'star-triangle-down-open-dot', 21, 'star-square', 121,
                'star-square-open', 221, 'star-square-dot', 321,
                'star-square-open-dot', 22, 'star-diamond', 122,
                'star-diamond-open', 222, 'star-diamond-dot', 322,
                'star-diamond-open-dot', 23, 'diamond-tall', 123,
                'diamond-tall-open', 223, 'diamond-tall-dot', 323,
                'diamond-tall-open-dot', 24, 'diamond-wide', 124,
                'diamond-wide-open', 224, 'diamond-wide-dot', 324,
                'diamond-wide-open-dot', 25, 'hourglass', 125,
                'hourglass-open', 26, 'bowtie', 126, 'bowtie-open', 27,
                'circle-cross', 127, 'circle-cross-open', 28, 'circle-x',
                128, 'circle-x-open', 29, 'square-cross', 129,
                'square-cross-open', 30, 'square-x', 130, 'square-x-open',
                31, 'diamond-cross', 131, 'diamond-cross-open', 32,
                'diamond-x', 132, 'diamond-x-open', 33, 'cross-thin', 133,
                'cross-thin-open', 34, 'x-thin', 134, 'x-thin-open', 35,
                'asterisk', 135, 'asterisk-open', 36, 'hash', 136,
                'hash-open', 236, 'hash-dot', 336, 'hash-open-dot', 37,
                'y-up', 137, 'y-up-open', 38, 'y-down', 138,
                'y-down-open', 39, 'y-left', 139, 'y-left-open', 40,
                'y-right', 140, 'y-right-open', 41, 'line-ew', 141,
                'line-ew-open', 42, 'line-ns', 142, 'line-ns-open', 43,
                'line-ne', 143, 'line-ne-open', 44, 'line-nw', 144,
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
        State(ids['shape-by'], 'value'), #TODO
        State(ids['search-sample'], 'value'), #TODO
        State(ids['show-names'], 'value'),
        State(ids['reads-per-start-point-slider'], 'value'),
        State(ids['insert-size-mean-slider'], 'value'),
        State(ids['passed-filter-reads-slider'], 'value')])
    def updatePressed(click, 
            runs, 
            firstsort, 
            # secondsort, 
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
            sortby = data[bamqc_cols.Sample].str[0:4] #TODO: find a sane way to split on '_'

        if colourby == 'run':
            colourby_strategy = bamqc_cols.Run
        elif colourby == 'project':
            colourby_strategy = data[bamqc_cols.Sample].str[0:4]
            
        if shapeby == 'run': #TODO: there's 1700+ runs, not gonna be enough symbols
            shapeby_strategy = bamqc_cols.Run
        elif shapeby == 'project':
            shapeby_strategy = data[bamqc_cols.Sample].str[0:4]
        
        data = data.groupby(sortby).apply(lambda x:x)

        return [generateTotalReads(data, colourby_strategy, shownames),
            generateUnmappedReads(data, colourby_strategy, shownames),
            generateNonprimaryReads(data, colourby_strategy, shownames),
            generateOnTargetReads(data, colourby_strategy, shownames),
            generateReadsPerStartPoint(data, colourby_strategy, shownames, reads),
            generateMeanInsertSize(data, colourby_strategy, shownames, insertsizemean),
            generateTerminalOutput(data, reads, insertsizemean, passedfilter),]