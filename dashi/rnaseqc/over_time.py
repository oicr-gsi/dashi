import collections
import pandas
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep
import dash.exceptions
import itertools

import plotly
import sd_material_ui

rna_df: pandas.DataFrame = pandas.read_hdf('./data/rnaseqqc_cache.hd5')
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
pinery: pandas.DataFrame = pandas.read_hdf('./data/pinery_samples_cache.hd5', 'pinery_samples')

pin_needed = pinery[['name', 'preparation_kit_name']]
# Only include libraries (ensure dilutions aren't merged in)
pin_needed = pin_needed[pin_needed.index.str.startswith('LIB')]

rna_df = rna_df.merge(pin_needed, how='left', left_on='Sample Name', right_on='name')

# There are NaN kits, which need to be changed to a str. Use the existing Unspecified
rna_df = rna_df.fillna({'preparation_kit_name': 'Unspecified'})

all_kits = rna_df['preparation_kit_name'].sort_values().unique()

graphs_to_plot = (
    'Proportion Usable Bases',
    'rRNA Contamination (%reads aligned)',
    'Proportion Correct Strand Reads',
    'Proportion Aligned Bases',
    'Proportion Coding Bases',
    'Proportion Intronic Bases',
    'Proportion Intergenic Bases',
    'Proportion UTR Bases',
)

COLOURS = [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
    '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
    '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
    '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5'
]

# More can be added if the future needs it
# See https://plot.ly/python/reference/#scatter-marker
SHAPES = [
    "circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down",
    "triangle-left", "triangle-right", "pentagon", "star",
]

PlotProperty = collections.namedtuple('PlotProperty', ['name', 'properties'])


def assign_consistent_property(values: list, prop: list) -> dict:
    """
    Values in the DataFrame (project, tissue, kit) need to be assigned
    consistent properties (color, shape). This does is fairly simply, by looping
    in order through the values and assigning them the next available property.
    Property lists cannot run out, as it loops back to the beginning.

    Args:
        values: The values of assign properties to. Need to be unique
        prop: The properties to assign to

    Returns: A dictionary with keys being the values (project, tissue, kit) and
        the dictionary values being the properties (color, shape).

    """
    result = {}
    prop = itertools.cycle(prop)

    for v in values:
        result[v] = next(prop)

    return result


def create_plot_dict(df, variable, color, shape, show_legend=False):
    result = []

    for g in df.groupby([color.name, shape.name]):
        color_name = g[0][0]
        shape_name = g[0][1]
        data = g[1]

        data_shape = data[shape.name].apply(
            lambda x: shape.properties[x]
        )

        p = {
            'x': list(data['Run Date']),
            'y': list(data[variable]),
            'type': 'scattergl',
            'mode': 'markers',
            'name': color_name+'<br>'+shape_name,
            'text': list(data['Sample Name']),
            'legendgroup': color_name,
            'showlegend': show_legend,
            'marker': {
                'color': color.properties[color_name],
                'symbol': data_shape
            },
            # Hover labels are not cropped
            # https://github.com/plotly/plotly.js/issues/460
            'hoverlabel': {'namelength': -1},
        }

        result.append(p)

    return result


def create_subplot(rna_df, graph_list):
    traces = []

    projects = sorted(rna_df['Study Title'].unique(), key=lambda x: x.upper())
    colors = assign_consistent_property(projects, COLOURS)

    kits = sorted(
        rna_df['preparation_kit_name'].unique(),
        key=lambda x: x.upper()
    )
    shapes = assign_consistent_property(kits, SHAPES)

    for g in graph_list:
        if len(traces) == 0:
            traces.append(create_plot_dict(
                rna_df,
                g,
                PlotProperty('Study Title', colors),
                PlotProperty('preparation_kit_name', shapes),
                show_legend=True
            ))
        else:
            traces.append(create_plot_dict(
                rna_df,
                g,
                PlotProperty('Study Title', colors),
                PlotProperty('preparation_kit_name', shapes),
                show_legend=False
            ))

    # This assumes at most 8 graphs
    rows = [1, 1, 2, 2, 3, 3, 4, 4][:len(traces)]
    cols = [1, 2, 1, 2, 1, 2, 1, 2][:len(traces)]
    max_rows = max(rows)

    traces = zip(*traces)

    fig = plotly.subplots.make_subplots(
        rows=max_rows, cols=2,
        subplot_titles=graph_list,
        print_grid=False,
    )

    for t in traces:
        fig.add_traces(
            t,
            rows=rows,
            cols=cols,
        )

    fig['layout'].update(
        height=400*max_rows,
        template='plotly_white',
    )

    # If you want legend at the bottom
    # fig['layout']['legend'].update(orientation="h")

    return fig


layout = html.Div(children=[
    html.Div(children=[
        sd_material_ui.Drawer(
            id='project_drawer', open=False, docked=False, width='50%',
            children=[html.Div(children=[
                html.Label('Project:'),
                dcc.Dropdown(
                    id='project_multi_drop',
                    multi=True,
                    options=[{'label': x, 'value': x} for x in all_projects],
                    value=all_projects
                ),
                html.Br(),
                html.Label('Kits:'),
                dcc.Dropdown(
                    id='kits_multi_drop',
                    multi=True,
                    options=[{'label': x, 'value': x} for x in all_kits],
                    value=all_kits
                ),
                html.Br(),
                html.Label('Dates: '),
                dcc.DatePickerRange(
                    id='date_picker',
                    display_format='YYYY-MM-DD',
                    min_date_allowed=min(rna_df['Run Date']),
                    max_date_allowed=max(rna_df['Run Date']),
                    start_date=min(rna_df['Run Date']),
                    end_date=max(rna_df['Run Date']),
                ),
                html.Br(),
                html.Label('Show Graphs:'),
                dcc.Dropdown(
                    id='graphs_to_plot',
                    multi=True,
                    options=[{'label': x, 'value': x} for x in graphs_to_plot],
                    value=graphs_to_plot[:4]
                ),
            ], style={'margin': '23px'})]
        ),
        sd_material_ui.RaisedButton(id='filter_button', label='Filters'),
    ]),
    dcc.Loading(id="graph_loader", children=[
        sd_material_ui.Paper(
            [dcc.Graph(
                id='graph_subplot',
            )]
        ),
    ], type='circle')
])

try:
    from app import app
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    dep.Output('graph_subplot', 'figure'),
    [dep.Input('project_drawer', 'open')],
    [dep.State('project_multi_drop', 'value'),
     dep.State('kits_multi_drop', 'value'),
     dep.State('date_picker', 'start_date'),
     dep.State('date_picker', 'end_date'),
     dep.State('graphs_to_plot', 'value')]
)
def graph_subplot(drawer_open, projects, kits, start_date, end_date, graphs):
    if drawer_open:
        raise dash.exceptions.PreventUpdate(
            'Drawer opening does not require recalculation'
        )

    to_plot = rna_df[rna_df['Study Title'].isin(projects)]
    to_plot = to_plot[to_plot['preparation_kit_name'].isin(kits)]
    to_plot = to_plot[to_plot['Run Date'] >= pandas.to_datetime(start_date)]
    to_plot = to_plot[to_plot['Run Date'] <= pandas.to_datetime(end_date)]

    if len(to_plot) > 0:
        return create_subplot(to_plot, graphs)
    else:
        return {}


@app.callback(
    dep.Output('project_drawer', 'open'),
    [dep.Input('filter_button', 'n_clicks')]
)
def open_project_drawer(n_clicks):
    return n_clicks is not None


if __name__ == '__main__':
    app.run_server(debug=True)
