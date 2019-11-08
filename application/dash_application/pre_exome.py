import dash_html_components as html
import dash_core_components as core
import dash_table as tabl
from dash.dependencies import Input, Output
from .dash_id import init_ids

# TODO: develop against gsiqcetl@master rather than v0.5.0 once bamqc is available



# This is a great candidate for using ScatterGL


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
    'secondary-reads',
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
                core.Graph(id=ids['total-reads']),
                core.Graph(id=ids['unmapped-reads']),
                core.Graph(id=ids['secondary-reads']),
                core.Graph(id=ids['reads-per-start-point']),
                core.Graph(id=ids['mean-insert-size'])
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
