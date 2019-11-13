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

def generateTotalReads(current_data):
    return go.Figure(
        data=[go.Scattergl(
            x=current_data[bamqc_cols.Sample],
            y=current_data[bamqc_cols.TotalReads] / pow(10,6),
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
        )],
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

def generateUnmappedReads(current_data):
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

def generateNonprimaryReads(current_data):
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

def generateOnTargetReads(current_data):
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

def generateReadsPerStartPoint(current_data):
    return go.Figure(
        data=[go.Scattergl(
            x=current_data[bamqc_cols.Sample],
            y=percentageOf(current_data, bamqc_cols.ReadsPerStartPoint),
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
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

def generateMeanInsertSize(current_data):
    return go.Figure(
        data=[go.Scattergl(
            x=current_data[bamqc_cols.Sample],
            y=current_data[bamqc_cols.InsertMean],
            mode='markers',
            marker={
                'size': 1,
                'line': {'width': 0.5, 'color': 'red'}
            }
    )],
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
                        #TODO: needs to have all selected by default
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

                html.Label([
                    "Reads Per Start Point:",
                    core.Slider(id=ids['reads-per-start-point-slider'])
                ]), html.Br(),

                html.Label([
                    "Insert Size Mean:",
                    core.Slider(id=ids['insert-size-mean-slider'])
                ]), html.Br(),
                
                html.Label([
                    "Passed Filter Reads:",
                    core.Slider(id=ids['passed-filter-reads-slider'])
                ]), html.Br()
            ]),
        html.Div(className='graphs',
            children=[
                core.Graph(id=ids['total-reads'],
                    figure=generateTotalReads(bamqc)
                ),
                core.Graph(id=ids['unmapped-reads'],
                    figure=generateUnmappedReads(bamqc)
                ),
                core.Graph(id=ids['non-primary-reads'],
                    figure=generateNonprimaryReads(bamqc)
                ),
                core.Graph(id=ids['on-target-reads'],
                    figure=generateOnTargetReads(bamqc)
                ),
                core.Graph(id=ids['reads-per-start-point'],
                    figure=generateReadsPerStartPoint(bamqc)
                ),
                core.Graph(id=ids['mean-insert-size'],
                    figure=generateMeanInsertSize(bamqc)
                )
            ]),
        html.Div(className='terminal-output',
            children=[
                core.Textarea(id=ids['terminal-output'],
                    readOnly=True,
                    value='$'
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
        Output(ids['mean-insert-size'], 'figure')],
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
        # TODO: idk how to actually do this
        if firstsort == 'run':
            data = data.groupby(bamqc_cols.Run).apply(lambda x:x)

        return [generateTotalReads(data),
            generateUnmappedReads(data),
            generateNonprimaryReads(data),
            generateOnTargetReads(data),
            generateReadsPerStartPoint(data),
            generateMeanInsertSize(data)]

