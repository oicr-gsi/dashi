import gsiqcetl.bcl2fastq.parse
import gsiqcetl.bcl2fastq.utility
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep
import pandas

index = gsiqcetl.bcl2fastq.parse.load_cache(
    gsiqcetl.bcl2fastq.parse.CACHENAME.SAMPLES,
    './data/bcl2fastq_cache.hd5'
)
unknown = gsiqcetl.bcl2fastq.parse.load_cache(
    gsiqcetl.bcl2fastq.parse.CACHENAME.UNKNOWN,
    './data/bcl2fastq_cache.hd5'
)

all_runs = index['Run'].sort_values(ascending=False).unique()

all_runs = [{'label': r, 'value': r} for r in all_runs]

""" Sample_run_hidden holds json split format of "Known"
        columns: "FlowCell","Index1","Index2","LIMS IUS SWID","LaneClusterPF","LaneClusterRaw",
                 "LaneNumber","LaneYield","QualityScoreSum","ReadNumber","Run","RunNumber","SampleID",
                 "SampleName","SampleNumberReads","SampleYield","TrimmedBases","Yield","YieldQ30"
                   

     pruned_unknown_hidden holds json split format of "unknown"
        columns:  "Count","LaneNumber","Index1","Index2","Run","LIMS IUS SWID
               
         """

"""Within the main layout division there are 4 groups:
          1. the section with the 100% bar graph
          2.  Nested subdivision of:
                  a) pie graph at 24%
                  b) bar graph at 76%
          3. Sample Run hidden
          4. Pruned  Unknown Hidden
            Note: span can be used for inline setting


          Dropdown option's label set to all_runs(combination of unknown and known)
          Dropdown multi set to false (default) - only single select possible
                -  multiple select gives error due to inconsistent values
          """
layout = html.Div(children=[
    dcc.Dropdown(
        id='run_select',
        options=all_runs,
        value=all_runs[0]['value'],
        clearable=False
    ),

    dcc.Graph(
        id='known_index_bar',

    ),
    # Bar graph with defaults set, no change in colour etc
    html.Div([
        html.Div(
            [dcc.Graph(id='known_unknown_pie'),
             dcc.Textarea(
                 id='known_fraction',
                 style={'width': '100%'},
                 readOnly=True,
                 # This is the textbox at the bottom, hover over to see title
                 title=(
                     "Assumptions are made about which indexes are known "
                     "or unknown. This is due to multiple bcl2fastq analyses "
                     "being used on one run. This number should be 100%."
                 ),

             )],
            style={'width': '24%', 'display': 'inline-block', }
        ),
        html.Div(
            [dcc.Graph(id='unknown_index_bar')],
            style={'width': '76%', 'display': 'inline-block', 'float': 'right'}
        ),
    ]),

    html.Div(id='sample_run_hidden', style={'display': 'none'}),
    html.Div(id='pruned_unknown_hidden', style={'display': 'none'}),

])

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    dep.Output('sample_run_hidden', 'children'),
    [dep.Input('run_select', 'value')]

)
def update_sample_run_hidden(run_alias):
    """ When input (run_select) is changed, function is rerun to get json data for selected run
        Parameters:
            run_alias(str): alias of the run

        Returns:
             json object with columns, indices, and data, from run variable
             updates json string "sample_run_hidden"
"""
    run = index[index['Run'] == run_alias]
    run = run[run['ReadNumber'] == 1]
    run = run[~run['SampleID'].isna()]
    run = run.drop_duplicates(['SampleID', 'LaneNumber'])

    return run.to_json(date_format='iso', orient='split')


@app.callback(
    dep.Output('pruned_unknown_hidden', 'children'),
    [dep.Input('run_select', 'value')]
)
def update_pruned_unknown_hidden(run_alias):
    """ When input (run_select) is changed, function prune_unknown_index_from_run is run within
        update_pruned_unknown_hidden to get json data for selected run
        Parameters:
            run_alias(str): alias of the run

        Returns:
             json object with columns, indices, and data, from pruned variable
             updates json string "pruned_unknown_hidden"
    """
    pruned = gsiqcetl.bcl2fastq.utility.prune_unknown_index_from_run(
        run_alias, index, unknown
    )
    return pruned.to_json(date_format='iso', orient='split')


@app.callback(
    dep.Output('known_index_bar', 'figure'),
    [dep.Input('sample_run_hidden', 'children')]
)
def update_known_index_bar(run_json):
    """ When input (sample_run_hidden) is changed, function is rerun to get update bar graph of sample indices
           Parameters:
               run_json(str): json format of run data

           Returns:
              data and values for the layout of stacked bar graph of sample indices
              updates bar graph "known_index_bar"
       """
    run = pandas.read_json(run_json, orient='split')
    run['library'] = run['SampleID'].str.extract(
        'SWID_\d+_(\w+_\d+_.*_\d+_[A-Z]{2})_'
    )
    run['index'] = run['Index1'].str.cat(
        run['Index2'].fillna(''), sep=' '
    )
    data = []
    for inx, d in run.groupby('index'):
        data.append({
            'x': list(d['library']),
            # One library can be run on multiple lanes. Sum them together.
            'y': list(d.groupby('library')['SampleNumberReads'].sum()),
            'type': 'bar',
            'name': inx,
            'marker': {'line': {
                'width': 2,
                'color': 'rgb(255,255, 255)'
            }}
        })

    return {
        'data': data,
        'layout': {
            'barmode': 'stack',
            'title': 'Sample Indices',
            'xaxis': {'title': 'Library', 'automargin': True},
            'yaxis': {'title': 'Clusters'},
        }
    }


@app.callback(
    dep.Output('unknown_index_bar', 'figure'),
    [dep.Input('pruned_unknown_hidden', 'children')]
)
def update_unknown_index_bar(run_json):
    """ When input (sample_run_hidden) is changed, function is rerun to get updated bar graph of known and unknown indices
               Parameters:
                   run_json(str): json format of run data

               Returns:
                   data and layout values for stacked bar graph for unknown indices
                   updates unknown_index_bar bar graph
           """
    # pruned(str): holds first 30 unknown indices
    pruned = pandas.read_json(run_json, orient='split')
    pruned['index'] = pruned['Index1'].str.cat(
        pruned['Index2'].fillna(''), sep=' '
    )
    pruned = pruned.sort_values('Count', ascending=False)
    pruned = pruned.head(30)
    data = []
    for lane, d in pruned.groupby('LaneNumber'):
        data.append({
            'x': list(d['index']),
            'y': list(d['Count']),
            'type': 'bar',
            'name': lane,
        })
    return {
        'data': data,
        'layout': {
            'barmode': 'stack',
            'title': 'Unknown Indices',
            'xaxis': {'title': 'Index'},
            'yaxis': {'title': 'Clusters'},
        }
    }


@app.callback(
    [dep.Output('known_unknown_pie', 'figure'),
     dep.Output('known_fraction', 'value')],
    [dep.Input('run_select', 'value'),
     dep.Input('sample_run_hidden', 'children'),
     dep.Input('pruned_unknown_hidden', 'children')]
)
def update_pie_chart(run_alias, known_json, unknown_json):
    """ When inputs are changed function is rerun to get updated pie chart
            Parameters:
                run_alias(str): alias of run
                Known_json: json format of known indices data
                unknown_json: json format of unknown indices data
            Returns:
                updated pie chart "known_unknown_pie" with known and unknown indices ratio over total cluster
                updates value of known_fraction
    """
    known = pandas.read_json(known_json, orient='split')
    pruned = pandas.read_json(unknown_json, orient='split')
    known_count = known['SampleNumberReads'].sum()
    pruned_count = pruned['Count'].sum()

    total_clusters = gsiqcetl.bcl2fastq.utility.total_clusters_for_run(
        run_alias, index
    )
    fraction = (known_count + pruned_count) / total_clusters * 100

    return {
               'data': [{
                   'labels': ['Known', 'Unknown'],
                   'values': [known_count, pruned_count],
                   'type': 'pie',
                   'marker': {'colors': ['#349600', '#ef963b']},
               }],
               'layout': {
                   'title': 'Flow Cell Composition of Known/Unknown Indices'
               }
           }, 'Predicted clusters / produced clusters: {}%'.format(
        str(round(fraction, 1))
    )


if __name__ == '__main__':
    app.run_server(debug=True)
