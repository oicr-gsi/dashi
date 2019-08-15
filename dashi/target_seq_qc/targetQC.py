import gsiqcetl.bcl2fastq.parse
import gsiqcetl.bcl2fastq.utility
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep
import dash_table as dt
import pandas
import plotly.graph_objs as go
import numpy as np
import urllib
from datetime import datetime
import sd_material_ui as sd

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
df = df.drop(columns=['Sequencer Run Name', 'Lane Number'])

runs = df['Run'].sort_values(ascending=False).unique()
runs = [x for x in runs if str(x) != 'nan']

layout = html.Div(children=[

    sd.Drawer(id='TSQCFilter_drawer',
              width='40%',
              docked=False,
              children=[
                  html.Div([html.P(children='Report Filters', style={'font-size': '30px', 'padding-top': '10px',
                                                                     'text-align': 'center'}),
                            sd.Divider(),
                            html.P(children='Select a Run', style={'padding-left': '5px', 'font-weight': 'bold'}),
                            dcc.Dropdown(
                                id='TSQCselect_a_run',
                                options=[{'label': r, 'value': r} for r in runs],
                                value=runs[0],
                                clearable=False
                            ),
                            html.Br(),
                            html.P(children='Select a Lane', style={'padding-left': '5px', 'font-weight': 'bold'}),
                            html.Div(
                                dcc.RadioItems(
                                    id='TSQClane_select',
                                    labelStyle={'display': 'inline-block', 'padding-left': '30px', }
                                )
                            ),
                            html.Br(),
                            html.P(children='Enter a Threshold Value for the Index Clusters',
                                   style={'padding-left': '5px', 'font-weight': 'bold'}),
                            html.Div(
                                dcc.Input(
                                    id='TSQCindex_threshold',
                                    placeholder='Press "Enter" when complete',
                                    debounce=True,
                                    type='number',
                                    value='0'
                                )
                            ),
                            html.Br(),
                            html.P(children='Select Which Type of Sample to View',
                                   style={'padding-left': '5px', 'font-weight': 'bold'}),
                            html.Div(
                                dcc.Checklist(
                                    id='TSQCpass/fail',
                                    options=[
                                        {'label': 'Passed Samples', 'value': 'Pass'},
                                        {'label': 'Failed Samples', 'value': 'Fail'},
                                    ],
                                    value=['Pass', 'Fail'],
                                    labelStyle={'paddingLeft': 30}

                                ),
                            ),
                            html.Div([
                                html.P(children='Select a Sample Type',
                                       style={'padding-left': '5px', 'font-weight': 'bold'}),
                                dcc.Dropdown(
                                    id='TSQCsample_type',
                                    options=[{'label': 'DNA: WG', 'value': 'WG'},
                                             {'label': 'DNA: EX', 'value': 'EX'},
                                             {'label': 'DNA: TS', 'value': 'TS'},
                                             {'label': 'RNA: MR', 'value': 'MR'},
                                             {'label': 'RNA: SM', 'value': 'SM'},
                                             {'label': 'RNA: WT', 'value': 'WT'},
                                             {'label': 'RNA: TR', 'value': 'TR'}],
                                    value=['WG', 'EX', 'TS', 'MR', 'SM', 'WT', 'TR'],
                                    clearable=False,
                                    multi=True
                                )])
                            ])]
              ),
    sd.FlatButton(id='TSQCfilters',
                  label='Report Filters'),
    html.Div(children=[
        dcc.ConfirmDialog(
            id='TSQCwarning',
            message='The selected run does not return any data. Analysis may have not been completed yet.' '''

        '''' Click either "Ok" or "Cancel" to return to the most recent run.'
        ),
        dcc.Location(
            id='TSQCrun_url',
            refresh=False
        ),
        html.P(children='Target Seq QC (Post-capture) Report',
               style={'fontSize': 35, 'textAlign': 'center', 'fontWeight': '900', 'fontFamily': 'sans serif'}),
        html.Div(id='TSQCTitle',
                 style={'fontSize': 20, 'fontFamily': 'sans serif', 'textAlign': 'center', 'padding': 30}),
        html.Br(),

        html.Div(sd.Paper(html.Div(id='TSQCobject_threshold', style={'fontSize': 20, 'fontWeight': 'bold'}),
                          style={'padding': 50, 'background-color': 'rgb(222,222,222)'}),
                 style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center', }),
        html.Div(sd.Paper(html.Div(id='TSQCobject_passed_samples', style={'fontSize': 20, 'fontWeight': 'bold'}),
                          style={'padding': 50, 'background-color': 'rgb(222,222,222)'}),
                 style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center', 'padding': 50}),
        html.Div(sd.Paper(html.Div(id='TSQCobject_option3', style={'fontSize': 20, 'fontWeight': 'bold'}),
                          style={'padding': 50, 'background-color': 'rgb(222,222,222)'}),
                 style={'width': '30%', 'display': 'inline-block', 'textAlign': 'center'}, ),
        html.Br(),
        html.Div([
            sd.Paper(
                dcc.Graph(id='TSQCSampleIndices'),
            ),
            sd.Paper(
                dcc.Graph(id='TSQCPer Cent Difference')
            )
        ],
            style={'padding-bottom': 30}),
        html.Br(),
        html.Div([
            'Global Kills',
            html.Br(),
            sd.Paper([
                dcc.Graph(id='TSQCReads on Target'),

            ], )
        ], style={'font-size': 30, 'fontFamily': 'sans serif', 'text-align': 'center'}),
        html.A(
            'Download Data',
            id='TSQCdownload-link',
            download='rawdata.csv',
            href='',
            target='_blank'
        ),
        html.Div(
            dt.DataTable(
                id='TSQCSummary Table',
                style_cell={
                    'minWidth': '150px',
                    'textAlign': 'center'
                },
                style_table={
                    'maxHeight': '1000px',
                    'maxWidth': '100%',
                    'overflowY': 'scroll',
                    'overflowX': 'scroll',

                },
                style_header={'backgroundColor': 'rgb(222,222,222)',
                              'fontSize': 16,
                              'fontWeight': 'bold'},
            )
        ),
    ],
        style={'padding-left': 100, 'paddingRight': 100})
])

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    [dep.Output('TSQCselect_a_run', 'value'),
     dep.Output('TSQCwarning', 'displayed')],
    [dep.Input('TSQCrun_url', 'pathname')]
)
def TSQCrun_URL_update(value):
    if value == '/' or value is None:
        return runs[0], False
    elif value[1:-2] not in runs:
        return runs[0], True
    else:
        return value[1:-2], False


@app.callback(
    dep.Output('TSQClane_select', 'options'),
    [dep.Input('TSQCselect_a_run', 'value')]
)
def TSQCupdate_lane_options(run_alias):
    run = df[df['Run'] == run_alias]
    run = run[~run['Run'].isna()]
    return [{'label': i, 'value': i} for i in run['LaneNumber'].sort_values(ascending=True).unique()]


@app.callback(
    dep.Output('TSQClane_select', 'value'),
    [dep.Input('TSQClane_select', 'options')]
)
def TSQCupdate_lane_values(available_options):
    return available_options[0]['value']


@app.callback(
    dep.Output('TSQCTitle', 'children'),
    [dep.Input('TSQClane_select', 'value'),
     dep.Input('TSQCselect_a_run', 'value')]
)
def TSQCupdate_title(lane_value, run_value):
    return 'You have selected lane {} in run {}'.format(lane_value, run_value)


@app.callback(
    dep.Output('TSQCFilter_drawer', 'open'),
    [dep.Input('TSQCfilters', 'n_clicks')]
)
def TSQCopen_project_drawer(n_clicks):
    return n_clicks is not None


@app.callback(
    dep.Output('TSQCindex_threshold', 'value'),
    [dep.Input('TSQCselect_a_run', 'value'),
     dep.Input('TSQClane_select', 'value')])
def TSQCinitial_threshold_value(run_alias, lane_alias):
    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]
    run = run[~run['Run'].isna()].drop_duplicates('library')
    run = run[~run['library'].isna()]

    index_threshold = sum(run['SampleNumberReads']) / len(run['library'])
    return index_threshold


def TSQCSummary_table(run):
    run = run.round(2)
    run = run.filter(
        ['library', 'Run', 'LaneNumber', 'Index1', 'Index2', 'SampleNumberReads', 'reads on target',
         'insert size stdev'])
    run = run.sort_values('library')

    csv = run.to_csv(index=False)
    csv = 'data:text/csv;charset=utf-8,' + urllib.parse.quote(csv)

    run = run.drop(columns=['Run', 'LaneNumber'])
    run = run.dropna(axis=1, how='all', thresh=None, subset=None, inplace=False)

    columns = [{'name': i, 'id': i,
                'type': 'numeric'} for i in run.columns]

    data = run.to_dict('records')

    return columns, data, csv


def TSQCupdate_sampleindices(run, index_threshold):
    run = run.sort_values('library')

    data = []

    for inx, d in run.groupby(['library']):
        d['Threshold'] = index_threshold
        d['Color'] = np.where((d['SampleNumberReads'] >= index_threshold), '#20639B', '#db4b4b')
        data.append(
            go.Bar(
                x=list(d['library']),
                y=list(d['SampleNumberReads']),
                name=inx,
                marker={'color': list(d['Color'])},
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
            'title': 'Index Clusters per Sample',
            'xaxis': {'title': 'Sample', 'automargin': True},
            'yaxis': {'title': 'Clusters'},
            'showlegend': False,
            'barmode': 'group',

        }
    }


def TSQCpercent_difference(run, index_threshold):
    run = run.sort_values('library')

    data = []

    for inx, d in run.groupby('library'):
        d['Per Cent Difference'] = (d['SampleNumberReads'] - index_threshold) / index_threshold * 100
        data.append(
            go.Bar(
                x=list(d['library']),
                y=list(d['Per Cent Difference']),
                name=inx,
                marker={'color': '#20639B'},
            )
        )
    return {
        'data': data,
        'layout': {
            'title': 'Per Cent Difference of Index Clusters',
            'xaxis': {'title': 'Sample', 'automargin': True},
            'yaxis': {'title': 'Per Cent', 'range': [-100, 100]},
            'showlegend': False,
        }
    }


def TSQCReads_on_Target(run):
    run = run.sort_values(by='reads on target', ascending=False)
    run = run.dropna(subset=['reads on target'])

    try:
        reads_threshold = sum(run['reads on target']) / len(run['library'])
    except ZeroDivisionError:
        reads_threshold = 0

    num_libraries = len(run['library'])
    samples_passing_clusters = '%s/%s' % (sum(i > reads_threshold for i in run['reads on target']), num_libraries)

    data = []

    for inx, d in run.groupby(['library']):
        d['reads on target Threshold'] = reads_threshold
        d['Color'] = np.where((d['reads on target'] >= d['reads on target Threshold']), '#20639B', '#db4b4b')
        data.append(
            go.Bar(
                x=list(d['library']),
                y=list(d['reads on target']),
                name=inx,
                marker={'color': list(d['Color'])},
            )
        )
        data.append(
            go.Scatter(
                x=list(d['library']),
                y=list(d['reads on target Threshold']),
                line={
                    'width': 3,
                    'color': 'rgb(0,0,0)',
                    'dash': 'dash'
                },
                mode='markers+lines'))

    if len(run['reads on target']) is 0:
        reads_target_hidden = {'display': 'none'}
    else:
        reads_target_hidden = {'display': 'block'}

    return {
               'data': data,
               'layout': {
                   'title': 'Reads on Target Threshold: %s, Passed Samples: %s' % (
                       reads_threshold, samples_passing_clusters),
                   'xaxis': {'title': 'Sample', 'automargin': True},
                   'yaxis': {'title': 'Clusters'},
                   'showlegend': False,
               }
           }, reads_target_hidden


@app.callback(
    [dep.Output('TSQCSampleIndices', 'figure'),
     dep.Output('TSQCPer Cent Difference', 'figure'),
     dep.Output('TSQCReads on Target', 'figure'),
     dep.Output('TSQCReads on Target', 'style'),
     dep.Output('TSQCSummary Table', 'columns'),
     dep.Output('TSQCSummary Table', 'data'),
     dep.Output('TSQCdownload-link', 'href'),
     dep.Output('TSQCdownload-link', 'download'),
     dep.Output('TSQCobject_threshold', 'children'),
     dep.Output('TSQCobject_passed_samples', 'children'),
     dep.Output('TSQCobject_option3', 'children')],
    [dep.Input('TSQCselect_a_run', 'value'),
     dep.Input('TSQClane_select', 'value'),
     dep.Input('TSQCindex_threshold', 'value'),
     dep.Input('TSQCpass/fail', 'value'),
     dep.Input('TSQCsample_type', 'value')])
def TSQCupdate_graphs(run_alias, lane_alias, threshold, PassOrFail, sample_type):
    index_threshold = int(threshold)

    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]
    run = run[~run['Run'].isna()].drop_duplicates('library')
    run = run[~run['library'].isna()]

    num_libraries = len(run['library'])
    samples_passing_clusters = '%s/%s' % (sum(i > index_threshold for i in run['SampleNumberReads']), num_libraries)

    pass_or_fail = []
    for row in run['SampleNumberReads']:
        if row >= index_threshold:
            pass_or_fail.append('Pass')
        if row < index_threshold:
            pass_or_fail.append('Fail')
    run['Pass/Fail'] = pass_or_fail
    run = run[run['Pass/Fail'].isin(PassOrFail)]

    run['Sample Type'] = run['library'].str[-2:]
    run = run[run['Sample Type'].isin(sample_type)]

    downloadtimedate = datetime.today().strftime('%Y-%m-%d')
    download = 'PoolQC_%s_%s_%s.csv' % (downloadtimedate, run_alias, lane_alias)

    columns, data, csv = TSQCSummary_table(run)
    reads_target_figure, reads_target_display = TSQCReads_on_Target(run)
    return TSQCupdate_sampleindices(run, index_threshold), TSQCpercent_difference(run,
                                                                                  index_threshold), reads_target_figure, reads_target_display, columns, data, csv, download, (
                   'Threshold: ' + str(index_threshold)), (
                   'Passed Samples: ' + str(samples_passing_clusters)), 'Option3',


if __name__ == '__main__':
    app.run_server(debug=True)
