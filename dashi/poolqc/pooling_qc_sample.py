import gsiqcetl.bcl2fastq.parse
import gsiqcetl.bcl2fastq.utility
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
import dash
>>>>>>> 0673ad8... Update of Layout:
=======
import dash
import dash_bootstrap_components as dbc
>>>>>>> 82eb00e... intermediate file
=======
>>>>>>> 64ed902... Moved code files into dashi folder to allow for setup.py implementation
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep
import dash_table as dt
import pandas
import plotly.graph_objs as go
import numpy as np
import urllib
from datetime import datetime
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
=======
import sd_material_ui as sd

>>>>>>> 0673ad8... Update of Layout:
=======
import sd_material_ui as sd
>>>>>>> d0a2e74... intermediate commit
=======
>>>>>>> 64ed902... Moved code files into dashi folder to allow for setup.py implementation

pandas.options.mode.chained_assignment = None

rnaseq = pandas.read_hdf('./data/rnaseqqc_cache.hd5')
rnaseq.rename(columns={'Sample Name': 'library'}, inplace=True)

bamqc = pandas.read_hdf('./data/bamqc_cache.hd5')

bcl2fastq = gsiqcetl.bcl2fastq.parse.load_cache(
    gsiqcetl.bcl2fastq.parse.CACHENAME.SAMPLES,
    './data/bcl2fastq_cache.hd5')
bcl2fastq['library'] = bcl2fastq['SampleID'].str.extract('SWID_\d+_(\w+_\d+_.*_\d+_[A-Z]{2})_')

df = bcl2fastq.merge(rnaseq, on='library', how='outer')
df = df.merge(bamqc, on='library', how='outer')
<<<<<<< HEAD
<<<<<<< HEAD

df['properly paired reads'] = np.where(df['properly paired reads'].isnull(),
                                       df['rRNA Contamination (%reads properly paired)'], df['properly paired reads'])

<<<<<<< HEAD
<<<<<<< HEAD
# Currently using arbitrary values as threshold for visualisation
INDEX_THRESHOLD = 500000

layout = html.Div(children=[
    dcc.ConfirmDialog(
        id='warning',
        message='The selected run does not return any data. Analysis may have not been completed yet.' '''
=======
layout = html.Div(children=[
    sd.Drawer(id='Filter_drawer',
              width='35%',
              docked=False,
              children=[
                  html.Div([dcc.Dropdown(
                      id='select_a_run',
                      options=[{'label': r, 'value': r} for r in runs],
                      value=runs[0],
                      clearable=False
                  ),
                      html.Div(
                          dcc.Dropdown(
                              id='lane_select'
                          )
                      )
                  ])]
              ),
    sd.FlatButton(id='filters',
                  label='Report Filters'),
    html.Div(children=[
        dcc.ConfirmDialog(
            id='warning',
            message='The selected run does not return any data. Analysis may have not been completed yet.' '''
>>>>>>> 0673ad8... Update of Layout:
        '''' Click either "Ok" or "Cancel" to return to the most recent run.'
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
        dcc.Graph(id='SampleIndices'),
    ),
    html.A(
        'Download Data',
        id='download-link',
        download='rawdata.csv',
        href='',
        target='_blank'
    ),
    html.Div(
        dt.DataTable(
            id='Summary Table',
            style_cell={
                'minWidth': '150px',
                'textAlign': 'center'
            },
            style_table={
                'maxHeight': '1000px',
                'maxWidth': '100%',
                'overflowY': 'scroll',
                'overflowX': 'scroll'
            },
            style_header={'backgroundColor': 'rgb(222,222,222)',
                          'fontSize': 16,
                          'fontWeight': 'bold'},

        )),
]
)
=======
=======
>>>>>>> d0a2e74... intermediate commit
=======

>>>>>>> 64ed902... Moved code files into dashi folder to allow for setup.py implementation
df = df.drop(columns=['Sequencer Run Name', 'Lane Number'])

runs = df['Run'].sort_values(ascending=False).unique()
runs = [x for x in runs if str(x) != 'nan']

<<<<<<< HEAD
<<<<<<< HEAD
layout = html.Div(
    [html.Div(id='header',
              className='row flex_display',
              style={'margin-bottom': '25px'})
        [html.H3('Pool Balancing QC Report',
                 style={'margin-bottom':'0px'})],
     [html.Div([
            html.P('Filter by Run, Lane Number, and DNA/RNA', className='control_label'),
            dcc.Dropdown(
                id='select_a_run',
                options=[{'label': r, 'value': r} for r in runs],
                value=runs[0],
                clearable=False,
                className='dcc_control')],
            className="pretty_container four columns",
            id="cross-filter-options"),
        html.Div(children=[
            dcc.ConfirmDialog(
                id='warning',
                message='The selected run does not return any data. Analysis may have not been completed yet.' '''
>>>>>>> c73391b... Intermediate commit

=======
=======
navbar = dbc.NavbarSimple(
    [html.Div(children=
    dbc.DropdownMenu(children=
        dcc.Dropdown(
            id='select_a_run',
            options=[{'label': r, 'value': r} for r in runs],
            value=runs[0],
            clearable=False
        ),
        nav=True, )),
        dbc.DropdownMenu(
            nav=True,
            in_navbar=True,
            label='Menu',
            children=[
                dbc.DropdownMenuItem('Entry 1'),
                dbc.DropdownMenuItem('Entry 2'),
                dbc.DropdownMenuItem(divider=True),
                dbc.DropdownMenuItem('Entry 3'),
            ],
        ),
    ],
    brand='Report Filters',
    sticky='top',
    expand= 'lg'
)
>>>>>>> 82eb00e... intermediate file
layout = html.Div(children=[
<<<<<<< HEAD
<<<<<<< HEAD
    dcc.ConfirmDialog(
        id='warning',
        message='The selected run does not return any data. Analysis may have not been completed yet.' '''
<<<<<<< HEAD
>>>>>>> 13b9c85... intermediate commit
=======
=======
    sd.Drawer(id='Filter_drawer',
              width='35%',
              docked=False,
              children=[
                  html.Div([dcc.Dropdown(
                      id='select_a_run',
                      options=[{'label': r, 'value': r} for r in runs],
                      value=runs[0],
                      clearable=False
                  ),
                      html.Div(
                          dcc.Dropdown(
                              id='lane_select'
                          )
                      )
                  ])]
              ),
    sd.FlatButton(id='filters',
                  label='Report Filters'),
    html.Div(children=[
        dcc.ConfirmDialog(
            id='warning',
            message='The selected run does not return any data. Analysis may have not been completed yet.' '''
>>>>>>> d0a2e74... intermediate commit

>>>>>>> 82eb00e... intermediate file
        '''' Click either "Ok" or "Cancel" to return to the most recent run.'
        ),
        dcc.Location(
            id='run_url',
            refresh=False
        ),
        html.Div(id='Title', style={'fontSize': 25, 'textAlign': 'center', 'padding': 30}),
        html.Div(children=''),
        html.Div(
            dcc.Graph(id='SampleIndices'),
        ),
        html.A(
            'Download Data',
            id='download-link',
            download='rawdata.csv',
            href='',
            target='_blank'
        ),
        html.Div(
            dt.DataTable(
                id='Summary Table',
                style_cell={
                    'minWidth': '150px',
                    'textAlign': 'center'
                },
                style_table={
                    'maxHeight': '1000px',
                    'maxWidth': '100%',
                    'overflowY': 'scroll',
                    'overflowX': 'scroll'
                },
                style_header={'backgroundColor': 'rgb(222,222,222)',
                              'fontSize': 16,
                              'fontWeight': 'bold'},
=======
    dcc.ConfirmDialog(
        id='warning',
        message='The selected run does not return any data. Analysis may have not been completed yet.' '''
>>>>>>> 64ed902... Moved code files into dashi folder to allow for setup.py implementation

        '''' Click either "Ok" or "Cancel" to return to the most recent run.'
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
    html.A(
        'Download Data',
        id='download-link',
        download='rawdata.csv',
        href='',
        target='_blank'
    ),
    html.Div(
        dt.DataTable(
            id='Summary Table',
            editable=True,
            row_selectable='multi',
            selected_rows=[],
            style_cell={
                'minWidth': '150px',
                'textAlign': 'center'
            },
            style_table={
                'maxHeight': '1000px',
                'maxWidth': '100%',
                'overflowY': 'scroll',
                'overflowX': 'scroll'
            },
            style_header={'backgroundColor': 'rgb(222,222,222)',
                          'fontSize': 16,
                          'fontWeight': 'bold'},

        )),
    html.Div(
        dcc.Graph(id='SampleIndices'),
    ),
    html.Div(
        dcc.Graph(id='map_code')
    )
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
    elif value[1:-2] not in runs:
        return runs[0], True
    else:
        return value[1:-2], False


@app.callback(
    dep.Output('lane_select', 'options'),
    [dep.Input('select_a_run', 'value')]
)
def update_lane_options(run_alias):
    run = df[df['Run'] == run_alias]
    run = run[~run['Run'].isna()]
    return [{'label': i, 'value': i} for i in run['LaneNumber'].sort_values(ascending=True).unique()]


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
    [dep.Output('Summary Table', 'columns'),
     dep.Output('Summary Table', 'data'),
     dep.Output('Summary Table', 'style_data_conditional'),
     dep.Output('download-link', 'href'),
     dep.Output('download-link', 'download')],
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def Summary_table(run_alias, lane_alias):
    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]
    run = run[~run['Run'].isna()].drop_duplicates('library')
    run = run[~run['library'].isna()]
    run['% Mapped to Coding'] = run['Coding Bases'] / run['Passed Filter Aligned Bases'] * 100
    run['% Mapped to Intronic'] = run['Intronic Bases'] / run['Passed Filter Aligned Bases'] * 100
    run['% Mapped to Intergenic'] = run['Intergenic Bases'] / run['Passed Filter Aligned Bases'] * 100
    run['rRNA Contamination (%reads aligned)'] = run['rRNA Contamination (%reads aligned)']

    run = run.round(2)
    run = run.filter(
        ['library', 'Run', 'LaneNumber', 'Index1', 'Index2', 'YieldQ30', '% Mapped to Coding', '% Mapped to Intronic',
         '% Mapped to Intergenic',
         'rRNA Contamination (%reads aligned)', 'Proportion Correct Strand Reads', 'Coverage'])

    csv = run.to_csv(index=False)
    csv = 'data:text/csv;charset=utf-8,' + urllib.parse.quote(csv)
    run = run.drop(columns=['Run', 'LaneNumber'])

    columns = [{'name': i, 'id': i,
                'type': 'numeric'} for i in run.columns]

    data = run.to_dict('records')

    style_data_conditional = [{
        'if': {'column_id': 'library'},
        'backgroundColor': 'rgb(222, 222, 222)'
    },
        {'if': {'column_id': '% Mapped to Coding',
                'filter_query': '0 < {% Mapped to Coding} < 20'},
         'backgroundColor': 'rgb(219, 75, 75)'},
        {'if': {'column_id': '% Mapped to Intronic',
                'filter_query': '0 < {% Mapped to Coding} < 20'},
         'backgroundColor': 'rgb(219, 75, 75)'},
        {'if': {'column_id': '% Mapped to Intergenic',
                'filter_query': '0 < {% Mapped to Intergenic} < 15'},
         'backgroundColor': 'rgb(219, 75, 75)'},
    ]
    downloadtimedate = datetime.today().strftime('%Y-%m-%d')
    download = 'PoolQC_%s_%s_%s.csv' % (downloadtimedate, run_alias, lane_alias)

    return columns, data, style_data_conditional, csv, download


def update_sampleindices(run, rows, derived_virtual_selected_rows, colors):
    data = []

    for inx, d in run.groupby(['index']):
        data.append(
            go.Bar(
                x=list(d['library']),
                y=list(d['SampleNumberReads']),
                name=inx,
                marker={'color': colors},
            )
        )

    return {
        'data': data,
        'layout': {
            'title': 'Index Clusters per Sample ',
            'xaxis': {'title': 'Sample', 'automargin': True},
            'yaxis': {'title': 'Clusters'},

        }
    }


def update_percent_mapped_to_code(run, rows, derived_virtual_selected_rows, colors):
    run = run[~run['rRNA Contamination (%reads aligned)'].isna()]
    run = run.sort_values(by='Result', ascending=False)
    data = []

    for inx, d in run.groupby(['LaneNumber']):
        d['Threshold'] = 20
        d['Color'] = np.where((d['Result'] >= d['Threshold']), '#ffffff', '#db4b4b')
        data.append(
            go.Bar(
                y=list(d['library']),
                x=list(d['Result']),
                orientation='h',
                name=inx,
                marker={'color': colors,
                        'line': {
                            'width': 3,
                            'color': list(d['Color'])
                        }},
            )
        )
        data.append(
            go.Scatter(
                y=list(d['library']),
                x=list(d['Threshold']),
                orientation='h',
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
            'title': 'Per Cent Mapped to Coding (RNA) ',
            'yaxis': {'title': 'Sample', 'automargin': True},
            'xaxis': {'title': 'Per Cent', 'range': [0, 100]},
            'showlegend': False,
            'height': (len(run) * 30) + 150
        }
    }


@app.callback(
    [dep.Output('map_code', 'figure'),
     dep.Output('SampleIndices', 'figure')],
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value'),
     dep.Input('Summary Table', 'derived_virtual_data'),
     dep.Input('Summary Table', 'derived_virtual_selected_rows')])
def update_all_graphs(run_alias, lane_alias, rows, derived_virtual_selected_rows):
    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]
    run = run[~run['Run'].isna()].drop_duplicates('library')
    run['Result'] = run['Coding Bases'] / run['Passed Filter Aligned Bases'] * 100
    run['index'] = run['Index1'].str.cat(
        run['Index2'].fillna(''), sep=' ')

    if derived_virtual_selected_rows is None:
        derived_virtual_selected_rows = []

    dff = run if rows is None else pandas.DataFrame(rows)

    colors = ['#d9c76c' if i in derived_virtual_selected_rows else '#99b2c2'
              for i in range(len(dff))]

    return update_percent_mapped_to_code(run, rows, derived_virtual_selected_rows, colors), update_sampleindices(run,
                                                                                                                 rows,
                                                                                                                 derived_virtual_selected_rows,
                                                                                                                 colors)


if __name__ == '__main__':
    app.run_server(debug=True)
