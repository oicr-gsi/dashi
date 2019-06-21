import pandas
import dash_core_components as dcc
import dash_html_components as html

try:
    from app import app
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)


rna_df = pandas.read_hdf('./data/rnaseqqc_cache.hd5')
rna_df['Run Date'] = rna_df['Sequencer Run Name'].apply(
    lambda x: x.split('_')[0]
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
            'type': 'scatter',
            'mode': 'markers',
            'name': proj,
            'text': list(data['Sample Name']),
        }

        result.append(p)

    return result


layout = html.Div(children=[
    dcc.Graph(
        id='rRNA',
        figure={
            'data': create_plot_dict(
                rna_df,
                'rRNA Contamination (%reads aligned)'
            ),
            'layout': {
                'title': 'rRNA Contamination (%reads aligned)',
                'yaxis': dict(range=[0, 100]),
                'hovermode': 'closest',
            }
        }
    ),
    dcc.Graph(
        id='usable_bases',
        figure={
            'data': create_plot_dict(
                rna_df,
                'Proportion Usable Bases'
            ),
            'layout': {
                'title': 'Proportion Usable Bases',
                'yaxis': dict(range=[0, 1]),
                'hovermode': 'closest',
            }
        }
    ),
    dcc.Graph(
        id='correct_strand',
        figure={
            'data': create_plot_dict(
                rna_df,
                'Proportion Correct Strand Reads'
            ),
            'layout': {
                'title': 'Proportion Correct Strand Reads',
                'yaxis': dict(range=[0, 1]),
                'hovermode': 'closest',
            }
        }
    )
])

if __name__ == '__main__':
    app.layout = layout
    app.run_server(debug=True)
