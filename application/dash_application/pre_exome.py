import dash_html_components as html
import dash_core_components as core
import dash_table as tabl
from dash.dependencies import Input, Output
from .dash_id import init_ids
import plotly.graph_objects as go
import gsiqcetl.load
# TODO: develop against gsiqcetl@master rather than v0.5.0 once bamqc is available

bamqc = gsiqcetl.load.bamqc('v1')
bamqc_cols = gsiqcetl.load.bamqc_columns('v1')

# TODO: make this a function
bamqc['Percent-Unmapped'] = (bamqc[bamqc_cols.UnmappedReads] / bamqc[bamqc_cols.TotalReads]) * 100

bamqc['Percent-On-Target'] = (bamqc[bamqc_cols.ReadsOnTarget] / bamqc[bamqc_cols.TotalReads]) * 100

bamqc['Percent-Non-Primary'] = (bamqc[bamqc_cols.NonPrimaryReads] / bamqc[bamqc_cols.TotalReads]) * 100

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

def generateTotalReads():
    return go.Figure(
        data=[go.Scattergl(
            x=bamqc[bamqc_cols.Sample],
            y=bamqc[bamqc_cols.TotalReads] / pow(10,6),
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

def generateUnmappedReads():
    return go.Figure(
        data=[go.Scattergl(
            x=bamqc[bamqc_cols.Sample],
            y=bamqc['Percent-Unmapped'],
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

def generateNonprimaryReads():
    return go.Figure(
        data=[go.Scattergl(
            x=bamqc[bamqc_cols.Sample],
            y=bamqc['Percent-Non-Primary'],
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

def generateOnTargetReads():
    return go.Figure(
        data=[go.Scattergl(
            x=bamqc[bamqc_cols.Sample],
            y=bamqc['Percent-On-Target'],
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

def generateReadsPerStartPoint():
    return go.Figure(
        data=[go.Scattergl(
            x=bamqc[bamqc_cols.Sample],
            y=bamqc[bamqc_cols.ReadsPerStartPoint],
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

def generateMeanInsertSize():
    return go.Figure(
        data=[go.Scattergl(
            x=bamqc[bamqc_cols.Sample],
            y=bamqc[bamqc_cols.InsertMean],
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
                    core.Checklist(id=ids['run-id-list'])
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
                    figure=generateTotalReads()
                ),
                core.Graph(id=ids['unmapped-reads'],
                    figure=generateUnmappedReads()
                ),
                core.Graph(id=ids['non-primary-reads'],
                    figure=generateNonprimaryReads()
                ),
                core.Graph(id=ids['on-target-reads'],
                    figure=generateOnTargetReads()
                ),
                core.Graph(id=ids['reads-per-start-point'],
                    figure=generateReadsPerStartPoint()
                ),
                core.Graph(id=ids['mean-insert-size'],
                    figure=generateMeanInsertSize()
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
        Output(ids['total-reads'], 'figure'),
        [Input(ids['reads-per-start-point-slider'], 'value')])
    def test_1(value):
        return generateTotalReads();

    @dash_app.callback(
        Output(ids['unmapped-reads'], 'figure'),
        [Input(ids['reads-per-start-point-slider'], 'value')])
    def test_2(value):
        return generateUnmappedReads();

    @dash_app.callback(
        Output(ids['non-primary-reads'], 'figure'),
        [Input(ids['reads-per-start-point-slider'], 'value')])
    def test_3(value):
        return generateNonprimaryReads();

    @dash_app.callback(
        Output(ids['on-target-reads'], 'figure'),
        [Input(ids['reads-per-start-point-slider'], 'value')])
    def test_4(value):
        return generateOnTargetReads();

    @dash_app.callback(
        Output(ids['reads-per-start-point'], 'figure'),
        [Input(ids['reads-per-start-point-slider'], 'value')])
    def test_5(value):
        return generateReadsPerStartPoint();

    @dash_app.callback(
        Output(ids['mean-insert-size'], 'figure'),
        [Input(ids['reads-per-start-point-slider'], 'value')])
    def test_6(value):
        return generateMeanInsertSize();

