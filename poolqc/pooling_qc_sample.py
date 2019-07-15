import dash_core_components as dcc
import dash_table.FormatTemplate as FormatTemplate
import dash_html_components as html
import dash.dependencies as dep
import dash_table as dt
import pandas
import plotly.plotly as plotly
import plotly.graph_objs as go
import numpy as np

pandas.options.mode.chained_assignment = None
df = pandas.read_hdf('./data/rnaseqqc_cache.hd5')

runs = df['Sequencer Run Name'].sort_values(ascending=False).unique()
runs = [x for x in runs if str(x) != 'nan']

layout = html.Div(children=[
    dcc.ConfirmDialog(
        id='warning',
        message='The selected run does not return any data. Analysis may have not been completed yet.' '''

        '''' Click either "Ok" or "Cancel" to return to the most run.'
    ),
    dcc.Location(
        id='run_url',
        refresh=False
    ),
    html.Div(children=
    dcc.Dropdown(
        id='select_a_run',
        options=[{'label': r, 'value': r} for r in runs],
        value=runs[0],
        clearable=False
    )),
    html.Div(
        dcc.Dropdown(
            id='lane_select'
        )),
    html.Div(id='Title', style={'fontSize': 25, 'textAlign': 'center', 'padding': 30}),
    html.Div(children=''),
    html.Div(
        dt.DataTable(
            id='Summary Table',
            style_cell={
                'minWidth': '150px',
                'maxWidth': '150px',
                'textAlign': 'center'
            },
            n_fixed_rows=True,
            style_table={
                'maxHeight': '500px',
                'overflowY': 'scroll'
            },
            style_header={'backgroundColor': 'rgb(222,222,222)',
                          'fontSize': 16,
                          'fontWeight': 'bold'}

        )),
    html.Div(
        dcc.Graph(
            id='map_code'
        )),
    html.Div(
        dcc.Graph(
            id='Intronic Graph',
        )),
    html.Div(
        dcc.Graph(
            id='Intergenic Graph'
        )),
    html.Div(
        dcc.Graph(
            id='rRNA Contamination'
        )),
    html.Div(
        dcc.Graph(
            id='Strand Correct'
        ))

]
)

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    [dep.Output('select_a_run', 'value'),
     dep.Output('warning', 'displayed')],
    [dep.Input('run_url', 'pathname')]
)
def run_URL_update(value):
    if value == '/' or value is None:
        return runs[0], False
    elif value[1:] not in runs:
        return runs[0], True
    else:
        return value[1:], False


@app.callback(
    dep.Output('lane_select', 'options'),
    [dep.Input('select_a_run', 'value')]
)
def update_lane_options(run_alias):
    run = df[df['Sequencer Run Name'] == run_alias]
    run = run[~run['Sequencer Run Name'].isna()]
    return [{'label': i, 'value': i} for i in run['Lane Number'].sort_values(ascending=True).unique()]


@app.callback(
    dep.Output('lane_select', 'value'),
    [dep.Input('lane_select', 'options')]
)
def update_lane_values(available_options):
    return available_options[0]['value']


@app.callback(
    dep.Output('Title', 'children'),
    [dep.Input('lane_select', 'value'),
     dep.Input('select_a_run', 'value')]
)
def update_title(lane_value, run_value):
    return 'You have selected lane {} in run {}'.format(lane_value, run_value)


@app.callback(
    dep.Output('map_code', 'figure'),
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def Mapped_to_Coding(run_alias, lane_alias):
    run = df[(df['Sequencer Run Name'] == run_alias) & (df['Lane Number'] == lane_alias)]
    run = run[~run['Sequencer Run Name'].isna()]
    data = []
    for inx, d in run.groupby(['Lane Number']):
        d['Result'] = d['Coding Bases'] / d['Passed Filter Aligned Bases'] * 100
        d['Threshold'] = 60
        d['Color'] = np.where((d['Result'] >= d['Threshold']), 'rgb(174,205,173)', 'rgb(238,153,159)')
        data.append(
            go.Bar(
                x=list(d['Sample Name']),
                y=list(d['Result']),
                name=inx,
                marker={'color': list(d['Color'])},

            )
        )
        data.append(
            go.Scatter(
                x=list(d['Sample Name']),
                y=list(d['Threshold']),
                name=inx,
                line={
                    'width': 3,
                    'color': 'rgb(204,0,0)',
                    'dash': 'dash',
                },
                mode='lines'))

    return {
        'data': data,
        'layout': {
            'title': 'Per Cent Mapped to Coding ',
            'xaxis': {'title': 'Sample Name ', 'automargin': True},
            'yaxis': {'title': 'Per Cent'},
            'showlegend': False
        }
    }


@app.callback(
    dep.Output('Intergenic Graph', 'figure'),
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def mapped_to_intergenic(run_alias, lane_alias):
    run = df[(df['Sequencer Run Name'] == run_alias) & (df['Lane Number'] == lane_alias)]
    run = run[~run['Sequencer Run Name'].isna()]
    data = []
    for inx, d in run.groupby(['Lane Number']):
        d['Result'] = d['Intergenic Bases'] / d['Passed Filter Aligned Bases'] * 100
        d['Threshold'] = 5
        d['Color'] = np.where((d['Result'] >= d['Threshold']), 'rgb(174,205,173)', 'rgb(238,153,159)')

        data.append(
            go.Bar(
                y=list(d['Sample Name']),
                x=list(d['Result']),
                orientation='h',
                name=inx,
                marker={'color': list(d['Color'])}
            )
        )
        data.append(
            go.Scatter(
                y=list(d['Sample Name']),
                x=list(d['Threshold']),
                mode='lines',
                name=inx,
                line={
                    'width': 5,
                    'color': 'rgb(204,0,0)',
                    'dash': 'dash',
                })
        )

    return {
        'data': data,
        'layout': {
            'title': 'Per Cent Mapped to Intergenic ',
            'yaxis': {'title': 'Sample Name ', 'automargin': True},
            'xaxis': {'title': 'Per Cent'},
            'showlegend': False
        }
    }


@app.callback(
    dep.Output('Intronic Graph', 'figure'),
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def mapped_to_intronic(run_alias, lane_alias):
    run = df[(df['Sequencer Run Name'] == run_alias) & (df['Lane Number'] == lane_alias)]
    run = run[~run['Sequencer Run Name'].isna()]
    data = []
    for inx, d in run.groupby(['Lane Number']):
        d['Result'] = d['Intronic Bases'] / d['Passed Filter Aligned Bases'] * 100
        d['Threshold'] = 5
        d['Color'] = np.where((d['Result'] >= d['Threshold']), 'rgb(174,205,173)', 'rgb(238,153,159)')

        data.append(
            go.Bar(
                y=list(d['Sample Name']),
                x=list(d['Result']),
                orientation='h',
                name=inx,
                marker={'color': list(d['Color'])}
            )
        )
        data.append(
            go.Scatter(
                y=list(d['Sample Name']),
                x=list(d['Threshold']),
                mode='lines',
                name=inx,

                line={
                    'width': 5,
                    'color': 'rgb(204,0,0)',
                    'dash': 'dash',
                })
        )
    return {
        'data': data,
        'layout': {
            'title': 'Per Cent Mapped to Intronic  ',
            'yaxis': {'title': 'Sample Name ', 'automargin': True},
            'xaxis': {'title': 'Per Cent'},
            'showlegend': False
        }
    }


@app.callback(
    dep.Output('rRNA Contamination', 'figure'),
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def rRna_Contamination(run_alias, lane_alias):
    run = df[(df['Sequencer Run Name'] == run_alias) & (df['Lane Number'] == lane_alias)]
    run = run[~run['Sequencer Run Name'].isna()]
    data = []
    for inx, d in run.groupby(['Lane Number']):
        d['Threshold'] = 5
        d['Color'] = np.where((run['rRNA Contamination (%reads aligned)'] >= d['Threshold']), '#abd9e9', '#fdae61')

        data.append(
            go.Bar(
                y=list(d['Sample Name']),
                x=list(run['rRNA Contamination (%reads aligned)']),
                orientation='h',
                name=inx,
                marker={'color': list(d['Color'])}
            )
        )
        data.append(
            go.Scatter(
                y=list(d['Sample Name']),
                x=list(d['Threshold']),
                mode='lines',
                name=inx,
                line={
                    'width': 5,
                    'color': 'rgb(204,0,0)',
                    'dash': 'dash',
                })
        )

    return {
        'data': data,
        'layout': {
            'title': 'Per Cent rRNA Contamination (%reads aligned)',
            'yaxis': {'title': 'Sample Name ', 'automargin': True},
            'xaxis': {'title': 'Per Cent'},
            'showlegend': False
        }
    }


@app.callback(
    dep.Output('Strand Correct', 'figure'),
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def correct_strand_reads(run_alias, lane_alias):
    run = df[(df['Sequencer Run Name'] == run_alias) & (df['Lane Number'] == lane_alias)]
    run = run[~run['Sequencer Run Name'].isna()]
    data = []
    for inx, d in run.groupby(['Lane Number']):
        d['Threshold'] = 15
        d['Color'] = np.where(((run['Proportion Correct Strand Reads'] * 100) >= d['Threshold']), '#abd9e9', '#fdae61')

        data.append(
            go.Bar(
                y=list(d['Sample Name']),
                x=list(run['Proportion Correct Strand Reads'] * 100),
                orientation='h',
                name=inx,
                marker={'color': list(d['Color'])}
            )
        )
        data.append(
            go.Scatter(
                y=list(d['Sample Name']),
                x=list(d['Threshold']),
                mode='lines',
                name=inx,
                line={
                    'width': 5,
                    'color': 'rgb(204,0,0)',
                    'dash': 'dash',
                })
        )

    return {
        'data': data,
        'layout': {
            'title': 'Proportion Correct Strand Reads',
            'yaxis': {'title': 'Sample Name ', 'automargin': True},
            'xaxis': {'title': 'Per Cent'},
            'showlegend': False
        }
    }


@app.callback(
    [dep.Output('Summary Table', 'columns'),
     dep.Output('Summary Table', 'data'),
     dep.Output('Summary Table', 'style_data_conditional')],
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def Summary_table(run_alias, lane_alias):
    run = df[(df['Sequencer Run Name'] == run_alias) & (df['Lane Number'] == lane_alias)]
    run = run[~run['Sequencer Run Name'].isna()]
    run['% Mapped to Coding'] = run['Coding Bases'] / run['Passed Filter Aligned Bases']
    run['% Mapped to Intronic'] = run['Intronic Bases'] / run['Passed Filter Aligned Bases']
    run['% Mapped to Intergenic'] = run['Intergenic Bases'] / run['Passed Filter Aligned Bases']
    run['rRNA Contamination (%reads aligned)'] = run['rRNA Contamination (%reads aligned)'] / 100
    run = run.filter(['Sample Name', '% Mapped to Coding', '% Mapped to Intronic', '% Mapped to Intergenic',
                      'rRNA Contamination (%reads aligned)', 'Proportion Correct Strand Reads'])
    columns = [{'name': i, 'id': i,
                'type': 'numeric',
                'format': FormatTemplate.percentage(2)} for i in run.columns]
    data = run.to_dict('records')
    style_data_conditional = [{
        'if': {'column_id': 'Sample Name'},
        'backgroundColor': 'rgb(222, 222, 222)'
    },
        {'if': {'column_id': '% Mapped to Coding',
                'filter': '{% Mapped to Coding} < 60'},
         'backgroundColor': 'rgb(238,153,159)'},

        {'if': {'column_id': '% Mapped to Intronic',
                'filter': '{% Mapped to Intronic} < 5'},
         'backgroundColor': 'rgb(238,153,159)'},

        {'if': {'column_id': '% Mapped to Intergenic',
                'filter': '{% Mapped to Intergenic} < 5'},
         'backgroundColor': 'rgb(238,153,159)'},
    ]

    return columns, data, style_data_conditional


if __name__ == '__main__':
    app.run_server(debug=True)
