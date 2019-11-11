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
    'reads-per-start-point',
    'insert-size-mean',
    'passed-filter-reads',

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

layout = html.Div(className='body',
    children=[
        html.Div(className='sidebar',
            children=[
                html.Button(id=ids['update-button']),
                html.Button(id=ids['download-button']),
                core.Checklist(id=ids['run-id-list']),
                core.Dropdown(id=ids['first-sort']),
                core.Dropdown(id=ids['second-sort']),
                core.Dropdown(id=ids['colour-by']),
                core.Dropdown(id=ids['shape-by']),
                core.Dropdown(id=ids['first-sort']),
                core.Input(id=ids['search-sample']),
                core.Dropdown(id=ids['show-names']),
                core.Slider(id=ids['on-target-reads']),
                core.Slider(id=ids['reads-per-start-point']),
                core.Slider(id=ids['mean-insert-size'])
            ]),
        html.Div(className='graphs',
            children=[
                core.Graph(id=ids['total-reads'],
                    figure=go.Figure(
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
                )),

                core.Graph(id=ids['unmapped-reads'],
                    figure=go.Figure(
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
                )),

                core.Graph(id=ids['non-primary-reads'],
                    figure=go.Figure(
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
                )),
                
                core.Graph(id=ids['on-target-reads'],
                    figure=go.Figure(
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
                )),

                core.Graph(id=ids['reads-per-start-point'],
                    figure=go.Figure(
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
                )),
                
                core.Graph(id=ids['mean-insert-size'],
                    figure=go.Figure(
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
                ))
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
    # @dash_app.callback(
    #     Output(),
    #     [Input()])
    # def placeholder_callback(value):
        return

