import pandas
import dash_core_components as dcc
import dash_html_components as html

import plotly

try:
    from app import app
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)


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
    fig['layout']['legend'].update(orientation="h")

    return fig


layout = html.Div(children=[
    dcc.Graph(
        id='rRNA',
        figure=create_subplot(rna_df)
    ),
])

if __name__ == '__main__':
    app.layout = layout
    app.run_server(debug=True)
