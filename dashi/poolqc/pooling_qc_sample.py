import gsiqcetl.bcl2fastq.parse
import gsiqcetl.bcl2fastq.utility
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

rnaseq = pandas.read_hdf('./data/rnaseqqc_cache.hd5')
# Column name is being renamed to allow for a seamless merge on column 'library'
rnaseq.rename(columns={'Sample Name': 'library'}, inplace=True)

bamqc = pandas.read_hdf('./data/bamqc_cache.hd5')

bcl2fastq = gsiqcetl.bcl2fastq.parse.load_cache(
    gsiqcetl.bcl2fastq.parse.CACHENAME.SAMPLES,
    './data/bcl2fastq_cache.hd5')

# Column is being renamed for clarification
bcl2fastq.rename(columns={'SampleNumberReads': 'Clusters'}, inplace=True)
bcl2fastq['library'] = bcl2fastq['SampleID'].str.extract(
    'SWID_\d+_([A-Z0-9]+_\d+_[a-zA-Z]{2}_._[A-Z]{2}_\d+_[A-Z]{2})_')

df = bcl2fastq.merge(rnaseq, on='library', how='outer')
df = df.merge(bamqc, on='library', how='outer')
df = df.drop(columns=['Sequencer Run Name', 'Lane Number'])
df['Sample Type'] = df['library'].str[-2:]
df['% Yield over Q30'] = df['ReadYieldQ30'] / df['ReadYield'] * 100

runs = df['Run'].dropna().sort_values(ascending=False).unique()

layout = html.Div(children=[

    sd.Drawer(id='Filter_drawer',
              width='40%',
              docked=False,
              children=[
                  html.Div([
                      html.P(children='Run Name', style={'padding-left': '5px', 'font-weight': 'bold'}),
                      dcc.Dropdown(
                          id='select_a_run',
                          options=[{'label': r, 'value': r} for r in runs],
                          value=runs[0],
                          clearable=False
                      ),
                      html.Br(),
                      html.P(children='Lane Number', style={'padding-left': '5px', 'font-weight': 'bold'}),
                      html.Div(
                          dcc.RadioItems(
                              id='lane_select',
                              labelStyle={'display': 'inline-block', 'padding-left': '30px', }
                          )
                      ),
                      html.Br(),
                      html.P(children='Threshold Value for Index Clusters',
                             style={'padding-left': '5px', 'font-weight': 'bold'}),
                      html.Div(
                          dcc.Input(
                              id='index_threshold',
                              placeholder='Press "Enter" when complete',
                              debounce=True,
                              type='number',
                              value='0'
                          )
                      ),
                      html.Br(),
                      html.P(children='Sample QC Status',
                             style={'padding-left': '5px', 'font-weight': 'bold'}),
                      html.Div(
                          dcc.Checklist(
                              id='pass/fail',
                              options=[
                                  {'label': 'Passed Samples', 'value': 'Pass'},
                                  {'label': 'Failed Samples', 'value': 'Fail'},
                              ],
                              value=['Pass', 'Fail'],
                              labelStyle={'paddingLeft': 30}

                          ),
                      ),
                      html.Div([
                          html.P(children='Sample Type',
                                 style={'padding-left': '5px', 'font-weight': 'bold'}),
                          dcc.Dropdown(
                              id='sample_type',
                              options=[{'label': 'DNA: WG', 'value': 'WG'},
                                       {'label': 'DNA: EX', 'value': 'EX'},
                                       {'label': 'DNA: TS', 'value': 'TS'},
                                       {'label': 'DNA: AS', 'value': 'AS'},
                                       {'label': 'RNA: MR', 'value': 'MR'},
                                       {'label': 'RNA: SM', 'value': 'SM'},
                                       {'label': 'RNA: WT', 'value': 'WT'},
                                       {'label': 'RNA: TR', 'value': 'TR'}],
                              value=['WG', 'EX', 'TS', 'AS', 'MR', 'SM', 'WT', 'TR'],
                              clearable=False,
                              multi=True
                          )])
                  ])]
              ),
    sd.RaisedButton(id='filters',
                    label='Filters'),
    html.Div(children=[

        # TODO - URL bug https://jira.oicr.on.ca/browse/GR-755
        # dcc.ConfirmDialog(
        #    id='warning',
        #   message='The selected run does not return any data. Analysis may have not been completed yet.' '''
        # '''' Click either "Ok" or "Cancel" to return to the most recent run.'
        # ),
        # dcc.Location(
        #   id='PBQCrun_url',
        #  refresh=False
        # ),
        html.P(children='Pool Balancing QC Report',
               style={'fontSize': 35, 'textAlign': 'center', 'fontWeight': '900', 'fontFamily': 'sans serif'}),
        html.Div(id='Title', style={'fontSize': 20, 'fontFamily': 'sans serif', 'textAlign': 'center', 'padding': 30}),
        html.Br(),

        html.Div(sd.Paper(html.Div(id='object_threshold', style={'fontSize': 20, 'fontWeight': 'bold'}),
                          style={'padding': 50, 'background-color': 'rgb(222,222,222)'}),
                 style={'width': '45%', 'display': 'inline-block', 'textAlign': 'center', }),
        html.Div(sd.Paper(html.Div(id='object_passed_samples', style={'fontSize': 20, 'fontWeight': 'bold'}),
                          style={'padding': 50, 'background-color': 'rgb(222,222,222)'}),
                 style={'width': '45%', 'display': 'inline-block', 'textAlign': 'center', 'padding': 50}),
        html.Br(),
        html.Div([
            sd.Paper(
                dcc.Graph(id='SampleIndices'),
            ),
            sd.Paper(
                dcc.Graph(id='Per Cent Difference')
            )
        ],
            style={'padding-bottom': 30}),
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
                    'overflowX': 'scroll',

                },
                style_header={'backgroundColor': 'rgb(222,222,222)',
                              'fontSize': 12,
                              'fontWeight': 'bold',
                              'fontFamily': 'sans serif'},
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

# TODO - URL bug https://jira.oicr.on.ca/browse/GR-755

'''
@app.callback(
    [dep.Output('select_a_run', 'value'),
     dep.Output('warning', 'displayed')],
    [dep.Input('PBQCrun_url', 'pathname')]
)
def run_URL_update(value):
    if value == '/' or value is None:
        return runs[0], False
    elif value[1:-2] not in runs:
        return runs[0], True
    else:
        return value[1:-2], False
'''


@app.callback(
    dep.Output('lane_select', 'options'),
    [dep.Input('select_a_run', 'value')]
)
def update_lane_options(run_alias):
    run = df[df['Run'] == run_alias]
    run = run[run['Run'].notna()]
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
    dep.Output('Filter_drawer', 'open'),
    [dep.Input('filters', 'n_clicks')]
)
def open_project_drawer(n_clicks):
    return n_clicks is not None


@app.callback(
    dep.Output('index_threshold', 'value'),
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value')]
)
def initial_threshold_value(run_alias, lane_alias):
    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]
    run = run.drop_duplicates('library')

    index_threshold = round(sum(run['Clusters']) / len(run['library']))
    return index_threshold


def Summary_table(run):
    # Adding 'on-the-fly' metrics
    run['Proportion Coding Bases'] = run['Proportion Coding Bases'] * 100
    run['Proportion Intronic Bases'] = run['Proportion Intronic Bases'] * 100
    run['Proportion Intergenic Bases'] = run['Proportion Intergenic Bases'] * 100
    run['Proportion Correct Strand Reads'] = run['Proportion Correct Strand Reads'] * 100

    run = run.round(2)
    run = run.filter(
        ['library', 'Run', 'LaneNumber', 'Index1', 'Index2', 'Clusters', 'rRNA Contamination (%reads aligned)',
         'Proportion Coding Bases',
         'Proportion Intronic Bases',
         'Proportion Intergenic Bases', 'Proportion Correct Strand Reads',
         'Coverage', '% Yield over Q30'])
    run = run.sort_values('library')

    csv = run.to_csv(index=False)
    csv = 'data:text/csv;charset=utf-8,' + urllib.parse.quote(csv)

    run = run.drop(columns=['Run', 'LaneNumber'])
    run = run.dropna(axis=1, how='all', thresh=None, subset=None, inplace=False)

    columns = [{'name': i, 'id': i,
                'type': 'numeric'} for i in run.columns]

    data = run.to_dict('records')

    return columns, data, csv


def update_sampleindices(run, index_threshold):
    run = run.sort_values('library')

    data = []

    for inx, d in run.groupby(['library']):
        data.append(
            go.Bar(
                x=list(d['library']),
                y=list(d['Clusters']),
                name=inx,
                marker={'color': np.where((d['Clusters'] >= index_threshold), '#20639B', '#db4b4b')},
            )
        )
        data.append(
            go.Scatter(
                x=list(d['library']),
                y=[index_threshold] * len(d),
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
            'xaxis': {'title': 'Sample', 'automargin': True, 'tickangle': '90', },
            'yaxis': {'title': 'Clusters'},
            'showlegend': False,
            'barmode': 'group',

        }
    }


def percent_difference(run, index_threshold):
    data = []

    for inx, d in run.groupby('library'):
        data.append(
            go.Bar(
                x=list(d['library']),
                y=(d['Clusters'] - index_threshold) / index_threshold * 100,
                name=inx,
                marker={'color': '#20639B'},
            )
        )
    return {
        'data': data,
        'layout': {
            'title': 'Per Cent Difference of Index Clusters',
            'xaxis': {'title': 'Sample', 'automargin': True, 'tickangle': '90', },
            'yaxis': {'title': 'Per Cent', 'range': [-100, 100]},
            'showlegend': False,
        }
    }


@app.callback(
    [dep.Output('SampleIndices', 'figure'),
     dep.Output('Per Cent Difference', 'figure'),
     dep.Output('Summary Table', 'columns'),
     dep.Output('Summary Table', 'data'),
     dep.Output('download-link', 'href'),
     dep.Output('download-link', 'download'),
     dep.Output('object_threshold', 'children'),
     dep.Output('object_passed_samples', 'children')],
    [dep.Input('select_a_run', 'value'),
     dep.Input('lane_select', 'value'),
     dep.Input('index_threshold', 'value'),
     dep.Input('pass/fail', 'value'),
     dep.Input('sample_type', 'value')])
def update_graphs(run_alias, lane_alias, index_threshold, PassOrFail, sample_type):
    """
    Outputs:
        SampleIndices: updates the figure Layout element of the graph titled the Index Clusters per Sample
        Per Cent Difference: updates the figure of Layout element of Per Cent Differences of Index Clusters
        Summary Table:
            Columns: updates the names of columns in the Summary Table
            Data: updates the cells in the Summary Table
        download-link:
            href: clickable link to download page for raw data in Summary Table
            download: csv file for raw data in Summary Table
        'object_threshold': updates the value of the 'Clusters Threshold' textbox at the top of report
        'object_passed_samples': updates the value of the 'Passed Samples' textbox at the top of the report
    Inputs:
        select_a_run: the value from the run drop-down in drawer
        lane_select: value selected from lane options in drawer
        index_threshold: either the calculated initial threshold, or if changed, the new value of index_threshold
        pass/fail: calculated value of how many samples have passed dependent on the threshold
        sample_type: the values of all the types of samples selected to view in the report (DNA vs RNA)
    """
    index_threshold = int(index_threshold)
    run = df[(df['Run'] == run_alias) & (df['LaneNumber'] == lane_alias)]

    run = run.drop_duplicates('library')
    run = run[run['library'].notna()]

    num_libraries = len(run['library'])
    samples_passing_clusters = '%s/%s' % (sum(i > index_threshold for i in run['Clusters']), num_libraries)

    pass_or_fail = []
    for row in run['Clusters']:
        if row >= index_threshold:
            pass_or_fail.append('Pass')
        else:
            pass_or_fail.append('Fail')

    run['Pass/Fail'] = pass_or_fail
    run = run[run['Pass/Fail'].isin(PassOrFail)]

    run = run[run['Sample Type'].isin(sample_type)]

    downloadtimedate = datetime.today().strftime('%Y-%m-%d')
    download = 'PoolQC_%s_%s_%s.csv' % (downloadtimedate, run_alias, lane_alias)

    columns, data, csv = Summary_table(run)

    return (update_sampleindices(run, index_threshold),
            percent_difference(run, index_threshold),
            columns,
            data,
            csv,
            download,
            ('Clusters Threshold: ' + str(index_threshold)),
            ('Passed Samples: ' + str(samples_passing_clusters))
            )


if __name__ == '__main__':
    app.run_server(debug=True)
