import gsiqcetl.bcl2fastq.parse
import gsiqcetl.bcl2fastq.utility
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep
import dash_table as dt
import pandas
import re
import plotly.graph_objs as go
import numpy as np
import urllib
from datetime import datetime

rnaseq = pandas.read_hdf('./data/rnaseqqc_cache.hd5')
rnaseq.rename(columns={'Sample Name': 'library'}, inplace=True)

bamqc = pandas.read_hdf('./data/bamqc_cache.hd5')

bcl2fastq = gsiqcetl.bcl2fastq.parse.load_cache(
    gsiqcetl.bcl2fastq.parse.CACHENAME.SAMPLES,
    './data/bcl2fastq_cache.hd5')
bcl2fastq['library'] = bcl2fastq['SampleID'].str.extract('SWID_\d+_(\w+_\d+_.*_\d+_[A-Z]{2})_')

df = bcl2fastq.merge(rnaseq, on='library', how='outer')
df = df.merge(bamqc, on='library', how='outer')
df = df.drop(columns=['Sequencer Run Name', 'Lane Number'])

runs = df['Run'].dropna().sort_values(ascending=False).unique()

# Currently using arbitrary values as threshold for visualisation
INDEX_THRESHOLD = 500000

layout = html.Div(children=[
    dcc.ConfirmDialog(
        id='warning',
        message='The selected run does not return any data. Analysis may have not been completed yet.' '''
        '''' Click either "Ok" or "Cancel" to return to the most recent run.'
    ),
    dcc.Location(
        id='report_url',
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

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    [dep.Output('select_a_run', 'value'),
     dep.Output('warning', 'displayed')],
    [dep.Input('select_a_run', 'options'),
    dep.Input('report_url', 'search')]
)
def report_url_update(run_options, search):
    print(run_options[0])
    run_value = re.search('[?]\s+=([^?]+)', search)
    print (run_value)
    if run_value:
        run_value = run_value.group(1)
    print (run_value)
    if run_value == '/' or run_value is None:
        return runs[0], False
    elif run_value not in runs:
        return runs[0], True
    else:
        return run_value, False


@app.callback(
    dep.Output('lane_select', 'options'),
    [dep.Input('select_a_run', 'value')]
)
def update_lane_options(run_alias):
    run = df[df['Run'] == run_alias]
    return [{'label': i, 'value': i} for i in run['LaneNumber'].sort_values(ascending=True).unique()]


@app.callback(
    dep.Output('lane_select', 'value'),
    [dep.Input('lane_select', 'options'),
     dep.Input('report_url', 'search')]
)
def update_lane_values(available_options, search):
    lane_value = re.search('[?]\s+=[^?]+\w.*=([0-9])', search)

    if lane_value:
        lane_value = lane_value.group(1)
    else:
        return 1

    lane_value = int(lane_value)
    if any(x['value'] == lane_value for x in available_options):
        return lane_value
    else:
        return 1



@app.callback(
    dep.Output('Title', 'children'),
    [dep.Input('lane_select', 'value'),
     dep.Input('select_a_run', 'value')]
)
def update_title(lane_value, run_value):
    return 'You have selected lane {} in run {}'.format(lane_value, run_value)


def Summary_table(run):
    run['Proportion Coding Bases'] = run['Proportion Coding Bases'] * 100
    run['Proportion Intronic Bases'] = run['Proportion Intronic Bases'] * 100
    run['Proportion Intergenic Bases'] = run['Proportion Intergenic Bases'] * 100
    run['Proportion Correct Strand Reads'] = run['Proportion Correct Strand Reads'] * 100

    run = run.round(2)
    run = run.filter(
        ['library', 'Run', 'LaneNumber', 'Index1', 'Index2', 'SampleNumberReads', 'Proportion Coding Bases',
         'Proportion Intronic Bases', 'Proportion Intergenic Bases',
         'rRNA Contamination (%reads aligned)', 'Proportion Correct Strand Reads',
         'Coverage'])
    run = run.sort_values('library')
    csv = run.to_csv(index=False)
    csv = 'data:text/csv;charset=utf-8,' + urllib.parse.quote(csv)
    run = run.drop(columns=['Run', 'LaneNumber'])

    # Append Pass/Fail and Thresholds

    columns = [{'name': i, 'id': i,
                'type': 'numeric'} for i in run.columns]

    data = run.to_dict('records')

    # highlighting datatable cells/columns/rows
    style_data_conditional = [{
        'if': {'column_id': 'library'},
        'backgroundColor': 'rgb(222, 222, 222)'
    },
        {'if': {'column_id': 'properly paired reads',
                'filter_query': '0 < {properly paired reads} and {properly paired reads} < 20'},
         'backgroundColor': 'rgb(219, 75, 75)'},
        {'if': {'column_id': 'Proportion Coding Bases',
                'filter_query': '0 < {Proportion Coding Bases} and {Proportion Coding Bases} < 20'},
         'backgroundColor': 'rgb(219, 75, 75)'},
        {'if': {'column_id': 'Proportion Intronic Bases',
                'filter_query': '0 < {Proportion Intronic Bases} and {Proportion Intronic Bases} < 20'},
         'backgroundColor': 'rgb(219, 75, 75)'},
        {'if': {'column_id': 'Proportion Intergenic Bases',
                'filter_query': '0 < {Proportion Intergenic Bases} and {Proportion Intergenic Bases} < 15'},
         'backgroundColor': 'rgb(219, 75, 75)'},
        {'if': {'column_id': 'rRNA Contamination (%reads aligned)',
                'filter_query': '0 < {rRNA Contamination (%reads aligned)} and {rRNA Contamination (%reads aligned)} < 15'},
         'backgroundColor': 'rgb(219, 75, 75)'},
    ]
    return columns, data, style_data_conditional, csv


def update_sampleindices(run):
    run = run.sort_values('library')
    num_libraries = len(run['library'])
    samples_passing_clusters = '%s/%s' % (sum(i > INDEX_THRESHOLD for i in run['SampleNumberReads']), num_libraries)

    data = []

    for inx, d in run.groupby(['library']):
        d['Threshold'] = INDEX_THRESHOLD
        d['Color'] = np.where((d['SampleNumberReads'] >= INDEX_THRESHOLD), '#ffffff', '#db4b4b')
        data.append(
            go.Bar(
                x=list(d['library']),
                y=list(d['SampleNumberReads']),
                name=inx,
                marker={'color': '#20639B',
                        'line': {
                            'width': 3,
                            'color': list(d['Color'])
                        }},
            )
        )
        data.append(
            go.Scatter(
                x=list(d['library']),
                y=list(d['Threshold']),
                mode='markers+lines',
                line={
                    'width': 3,
                    'color': 'rgb(0,0,0)',
                    'dash': 'dash',
                }, ))

    return {
        'data': data,
        'layout': {
            'title': 'Index Clusters per Sample. Passed Samples: %s Threshold: %s' % (
                samples_passing_clusters, INDEX_THRESHOLD),
            'xaxis': {'title': 'Sample', 'automargin': True},
            'yaxis': {'title': 'Clusters'},
            'showlegend': False,

        }
    }


@app.callback(
    [dep.Output('SampleIndices', 'figure'),
     dep.Output('Summary Table', 'columns'),
     dep.Output('Summary Table', 'data'),
     dep.Output('Summary Table', 'style_data_conditional'),
     dep.Output('download-link', 'href'),
     dep.Output('download-link', 'download')],
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')])
def update_graphs(run_alias, lane_alias):
    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]
    run = run[~run['library'].isna()].drop_duplicates('library')

    downloadtimedate = datetime.today().strftime('%Y-%m-%d')
    download = 'PoolQC_%s_%s_%s.csv' % (downloadtimedate, run_alias, lane_alias)

    columns, data, style_data_conditional, csv = Summary_table(run)

    return update_sampleindices(run), columns, data, style_data_conditional, csv, download


if __name__ == '__main__':
    app.run_server(debug=True)
