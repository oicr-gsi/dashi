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
    dcc.ConfirmDialog(
        id='error',
        message='You have input an incorrect run. Click either "Ok" or "Cancel" to return to the most recent run.'
    ),
    dcc.Dropdown(
        id='run_select',
        #   Options is concantenated string versions of all_runs.
        options=[{'label': r, 'value': r} for r in all_runs],
        value=all_runs[0],
        clearable=False
    ),
    dcc.Location(
        id='url',
        refresh=False
    ),

    dcc.Graph(
        id='known_index_bar',

    ),
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
            style={'width': '25%', 'display': 'inline-block', }
        ),
        html.Div(
            [dcc.Graph(id='unknown_index_bar')],
            style={'width': '75%', 'display': 'inline-block', 'float': 'right'}
        ),

    ])
])

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


def create_known_index_bar(run):
    """ Function to update known index bar according to user selected run
           Parameters:
               run_alias: name of run
           Returns:
              data and values for the layout of stacked bar graph of sample indices
              updates bar graph "known_index_bar"
       """
    data_known = []
    for inx, d in run.groupby('index'):
        data_known.append({
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
        'data': data_known,
        'layout': {
            'barmode': 'stack',
            'title': 'Sample Indices',
            'xaxis': {'title': 'Library', 'automargin': True},
            'yaxis': {'title': 'Clusters'},
        }}


def create_unknown_index_bar(pruned):
    """ Function to update unknown index bar  according to user selected run
            Parameters:
                 run_alias: name of run
            Returns:
                data and layout values for stacked bar graph for unknown indices
                updates unknown_index_bar bar graph
              """

    data_unknown = []
    for lane, d in pruned.groupby('LaneNumber'):
        data_unknown.append({
            'x': list(d['index']),
            'y': list(d['Count']),
            'type': 'bar',
            'name': lane,
        })
    return {
        'data': data_unknown,
        'layout': {
            'barmode': 'stack',
            'title': 'Unknown Indices',
            'xaxis': {'title': 'Index'},
            'yaxis': {'title': 'Clusters'},
        }
    }


def create_pie_chart(run, pruned, total_clusters):
    """ Function to update pie chart and known fraction according to user selected run
             Parameters:
                 run_alias(str): name of run
             Returns:
                 updated pie chart "known_unknown_pie" with known and unknown indices ratio over total cluster
                 updates value of known_fraction
     """
    known_count = run['SampleNumberReads'].sum()
    pruned_count = pruned['Count'].sum()
    fraction = (known_count + pruned_count) / total_clusters * 100
    return {'data': [{
        'labels': ['Known', 'Unknown'],
        'values': [known_count, pruned_count],
        'type': 'pie',
        'marker': {'colors': ['#349600', '#ef963b']},
                      }],
            'layout': {
              'title': 'Flow Cell Composition of Known/Unknown Indices'}

           }, \
           ('Predicted clusters / produced clusters: {}%'.format(

               str(round(fraction, 1))
           ))


@app.callback(
    [dep.Output('run_select', 'value'),
     dep.Output('error', 'displayed')],
    [dep.Input('url', 'pathname')]
)
def change_url(pathname):
    """ Allows user to enter Run name in URL which will update dropdown automatically, and the graphs.
        If User enters any value that's not a valid run an error box will pop up and return user to most recent run

        Parameters:
             pathname: user-requested path.

        Returns:
            The string value (without '/') of the user input for the drop-down to use
            Error pop-up displayed depending on user input.
    """
    #   In a pathname, it automatically adds '/' to the beginning of the input even if pathname blank
    #   While page loads, pathname is set to 'None'. Once page is loaded pathname is set to user input.
    if pathname == "/" or pathname is None:
        return all_runs[0], False
    elif pathname[1:] not in all_runs:
        return all_runs[0], True
    else:
        return pathname[1:], False


@app.callback(
    [dep.Output('known_index_bar', 'figure'),
     dep.Output('unknown_index_bar', 'figure'),
     dep.Output('known_unknown_pie', 'figure'),
     dep.Output('known_fraction', 'value')],
    [dep.Input('run_select', 'value')]
)
def update_layout(run_alias):
    """ When input(run dropdown) is changed, known index bar, unknown index bar, piechart and textarea are updated
        Returns:
            functions update_known_index_bar, update_unknown_index_bar, update_pie_chart's data value,
            and update_pie_chart's fraction value
    """

    run = index[index['Run'] == run_alias]
    run = run[run['ReadNumber'] == 1]
    run = run[~run['SampleID'].isna()]
    run = run.drop_duplicates(['SampleID', 'LaneNumber'])
    run['library'] = run['SampleID'].str.extract(
        'SWID_\d+_(\w+_\d+_.*_\d+_[A-Z]{2})_'
    )
    run['index'] = run['Index1'].str.cat(
        run['Index2'].fillna(''), sep=' '
    )

    pruned = gsiqcetl.bcl2fastq.utility.prune_unknown_index_from_run(
        run_alias, index, unknown
    )
    pruned['index'] = pruned['Index1'].str.cat(
        pruned['Index2'].fillna(''), sep=' '
    )
    pruned = pruned.sort_values('Count', ascending=False)
    pruned = pruned.head(30)

    total_clusters = gsiqcetl.bcl2fastq.utility.total_clusters_for_run(
        run_alias, index)

    pie_data, textarea_fraction = create_pie_chart(run, pruned, total_clusters)

    return create_known_index_bar(run), create_unknown_index_bar(pruned), pie_data, textarea_fraction


if __name__ == '__main__':
    app.run_server(debug=True)
