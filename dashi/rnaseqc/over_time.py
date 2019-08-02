import pandas
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep

import plotly


rna_df = pandas.read_hdf('./data/rnaseqqc_cache.hd5')
rna_df['Run Date'] = rna_df['Sequencer Run Name'].dropna().apply(
    lambda x: x.split('_')[0]
)

rna_df['Proportion Aligned Bases'] = (
    rna_df['Passed Filter Aligned Bases'] / rna_df['Passed Filter Bases']
)

# The Run Name is used to extract the date
# Some runs do not have the proper format
rna_df = rna_df[rna_df['Run Date'].str.isnumeric()]

rna_df['Run Date'] = pandas.to_datetime(
     rna_df['Run Date'], yearfirst=True
 )

all_projects = rna_df['Study Title'].sort_values().unique()

# Pull in meta data from Pinery
pinery = pandas.read_hdf('./data/pinery_samples_cache.hd5', 'pinery_samples')

pin_needed = pinery[['name', 'preparation_kit_name']]
# Only include libraries (ensure dilutions aren't merged in)
pin_needed = pin_needed[pin_needed.index.str.startswith('LIB')]

rna_df = rna_df.merge(pin_needed, how='left', left_on='Sample Name', right_on='name')
# There are NaN kits, which need to be changed to a str. Use the existing Unspecified
rna_df = rna_df.fillna({'preparation_kit_name': 'Unspecified'})

all_kits = rna_df['preparation_kit_name'].sort_values().unique()


def create_plot_dict(df, variable):
    result = []

    for g in df.groupby('Study Title'):
        proj = g[0]
        data = g[1]

        p = {
            'x': list(data['Run Date']),
            'y': list(data[variable]),
            'type': 'scattergl',
            'mode': 'markers',
            'name': proj,
            'text': list(data['Sample Name']),
            'legendgroup': proj,
            'showlegend': False,
        }

        result.append(p)

    return result


def create_subplot(rna_df):
    trace1 = create_plot_dict(rna_df, 'Proportion Usable Bases')
    trace2 = create_plot_dict(rna_df, 'rRNA Contamination (%reads aligned)')
    trace3 = create_plot_dict(rna_df, 'Proportion Correct Strand Reads')
    trace4 = create_plot_dict(rna_df, 'Proportion Aligned Bases')
    trace5 = create_plot_dict(rna_df, 'Proportion Coding Bases')
    trace6 = create_plot_dict(rna_df, 'Proportion Intronic Bases')
    trace7 = create_plot_dict(rna_df, 'Proportion Intergenic Bases')
    trace8 = create_plot_dict(rna_df, 'Proportion UTR Bases')

    color = [
        '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
        '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
        '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
        '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5'
    ]

    fig = plotly.tools.make_subplots(
        rows=4, cols=2,
        subplot_titles=(
            'Proportion Usable Bases',
            'rRNA Contamination (%reads aligned)',
            'Proportion Correct Strand Reads',
            'Proportion Aligned Bases',
            'Proportion Coding Bases',
            'Proportion Intronic Bases',
            'Proportion Intergenic Bases',
            'Proportion UTR Bases',
        ),
        print_grid=False,
    )

    color_index = 0
    for i in range(len(trace1)):
        if color_index >= len(color):
            color_index = 0

        t1 = trace1[i]
        t1['marker'] = {'color': color[color_index]}
        t1['showlegend'] = True

        fig.append_trace(t1, 1, 1)

        t2 = trace2[i]
        t2['marker'] = {'color': color[color_index]}
        fig.append_trace(t2, 1, 2)

        t3 = trace3[i]
        t3['marker'] = {'color': color[color_index]}
        fig.append_trace(t3, 2, 1)

        t4 = trace4[i]
        t4['marker'] = {'color': color[color_index]}
        fig.append_trace(t4, 2, 2)

        t5 = trace5[i]
        t5['marker'] = {'color': color[color_index]}
        fig.append_trace(t5, 3, 1)

        t6 = trace6[i]
        t6['marker'] = {'color': color[color_index]}
        fig.append_trace(t6, 3, 2)

        t7 = trace7[i]
        t7['marker'] = {'color': color[color_index]}
        fig.append_trace(t7, 4, 1)

        t8 = trace8[i]
        t8['marker'] = {'color': color[color_index]}
        fig.append_trace(t8, 4, 2)

        color_index += 1

    fig['layout'].update(
        height=1600,
        title='RNASeQC Metrics Over Time'
    )

    # If you want legend at the bottom
    # fig['layout']['legend'].update(orientation="h")

    return fig


layout = html.Div(children=[
    html.Div(children=[
        html.Label('Project'),
        dcc.Dropdown(
            id='project_multi_drop',
            multi=True,
            options=[{'label': x, 'value': x} for x in all_projects],
            value=all_projects
        ),
        html.Label('Kits'),
        dcc.Dropdown(
            id='kits_multi_drop',
            multi=True,
            options=[{'label': x, 'value': x} for x in all_kits],
            value=all_kits
        ),
        html.Label('Dates: '),
        dcc.DatePickerRange(
            id='date_picker',
            min_date_allowed=min(rna_df['Run Date']),
            max_date_allowed=max(rna_df['Run Date']),
            start_date=min(rna_df['Run Date']),
            end_date=max(rna_df['Run Date']),
        ),
    ]),
    dcc.Graph(
        id='graph_subplot',
        figure=create_subplot(rna_df)
    ),
])

try:
    from app import app
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    dep.Output('graph_subplot', 'figure'),
    [dep.Input('project_multi_drop', 'value'),
     dep.Input('kits_multi_drop', 'value'),
     dep.Input('date_picker', 'start_date'),
     dep.Input('date_picker', 'end_date'),]
)
def graph_subplot(projects, kits, start_date, end_date):
    to_plot = rna_df[rna_df['Study Title'].isin(projects)]
    to_plot = to_plot[to_plot['preparation_kit_name'].isin(kits)]
    to_plot = to_plot[to_plot['Run Date'] >= pandas.to_datetime(start_date)]
    to_plot = to_plot[to_plot['Run Date'] <= pandas.to_datetime(end_date)]

    if len(to_plot) > 0:
        return create_subplot(to_plot)
    else:
        return {}


if __name__ == '__main__':
    app.run_server(debug=True)
