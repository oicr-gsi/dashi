import collections
import pandas
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep
import dash.exceptions
import dash_table
import itertools
from typing import List, Union

import plotly.subplots
import plotly.graph_objs
import sd_material_ui

# noinspection PyTypeChecker
RNA_DF: pandas.DataFrame = pandas.read_hdf('./data/rnaseqqc_cache.hd5')

# The Run Name is used to extract the date
RNA_DF['Run Date'] = RNA_DF['Sequencer Run Name'].dropna().apply(
    lambda x: x.split('_')[0]
)
# Some runs do not have the proper format and will be excluded
RNA_DF = RNA_DF[RNA_DF['Run Date'].str.isnumeric()]
RNA_DF['Run Date'] = pandas.to_datetime(
    RNA_DF['Run Date'], yearfirst=True
)

RNA_DF['Proportion Aligned Bases'] = (
        RNA_DF['Passed Filter Aligned Bases'] / RNA_DF['Passed Filter Bases']
)

# List projects for which RNA-Seq studies have been done
ALL_PROJECTS = RNA_DF['Study Title'].sort_values().unique()

# Pull in meta data from Pinery
# noinspection PyTypeChecker
PINERY: pandas.DataFrame = pandas.read_hdf(
    './data/pinery_samples_provenance_cache.hd5'
)

PINERY = PINERY[[
    'sampleName', 'sequencerRunName', 'laneNumber', 'geo_prep_kit',
    'geo_library_source_template_type', 'geo_tissue_origin', 'geo_tissue_type',
    'geo_tissue_preparation',
]]

RNA_DF = RNA_DF.merge(
    PINERY,
    how='left',
    left_on=['Sample Name', 'Sequencer Run Name', 'Lane Number'],
    right_on=['sampleName', 'sequencerRunName', 'laneNumber'],
)

# NaN kits need to be changed to a str. Use the existing Unspecified
RNA_DF = RNA_DF.fillna({'geo_prep_kit': 'Unspecified'})
RNA_DF = RNA_DF.fillna({'geo_library_source_template_type': 'Unknown'})
# NaN Tissue Origin is set to `nn`, which is used by MISO for unknown
RNA_DF = RNA_DF.fillna({'geo_tissue_origin': 'nn'})
# NaN Tissue Type is set to `n`, which is used by MISO for unknown
RNA_DF = RNA_DF.fillna({'geo_tissue_type': 'n'})
RNA_DF = RNA_DF.fillna({'geo_tissue_preparation': 'Unknown'})

# Kits used for RNA-Seq experiments
ALL_KITS = RNA_DF['geo_prep_kit'].sort_values().unique()

# Which metrics can be plotted
METRICS_TO_GRAPH = (
    'Proportion Usable Bases',
    'rRNA Contamination (%reads aligned)',
    'Proportion Correct Strand Reads',
    'Proportion Aligned Bases',
    'Proportion Coding Bases',
    'Proportion Intronic Bases',
    'Proportion Intergenic Bases',
    'Proportion UTR Bases',
)

# The colours that are used in the graphs
COLOURS = [
    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c',
    '#98df8a', '#d62728', '#ff9896', '#9467bd', '#c5b0d5',
    '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f',
    '#c7c7c7', '#bcbd22', '#dbdb8d', '#17becf', '#9edae5'
]

# The shapes of the points to use in the graph
# More can be added if the future needs it
# See https://plot.ly/python/reference/#scatter-marker
SHAPES = [
    "circle", "square", "diamond", "cross", "x", "triangle-up", "triangle-down",
    "triangle-left", "triangle-right", "pentagon", "star",
]

# Which columns will the data table always have
DEFAULT_TABLE_COLUMN = [
    {'name': 'Library', 'id': 'Sample Name'},
    {'name': 'Project', 'id': 'Study Title'},
    {'name': 'Run', 'id': 'Sequencer Run Name'},
    {'name': 'Lane', 'id': 'Lane Number'},
    {'name': 'Kit', 'id': 'geo_prep_kit'},
    {'name': 'Library Source Type', 'id': 'geo_library_source_template_type'},
    {'name': 'Tissue Origin', 'id': 'geo_tissue_origin'},
    {'name': 'Tissue Type', 'id': 'geo_tissue_type'},
    {'name': 'Tissue State', 'id': 'geo_tissue_preparation'},
]

# Columns on which shape and colour can be set
SHAPE_COLOUR_COLUMN = [
    {'name': 'Project', 'id': 'Study Title'},
    {'name': 'Kit', 'id': 'geo_prep_kit'},
    {'name': 'Library Source Type', 'id': 'geo_library_source_template_type'},
    {'name': 'Tissue Origin', 'id': 'geo_tissue_origin'},
    {'name': 'Tissue Type', 'id': 'geo_tissue_type'},
    {'name': 'Tissue State', 'id': 'geo_tissue_preparation'},
]

# A convenience container that links how a metric should be graphed
# The name is the column name
# The properties is a dict
# The dict key is a value found in the column
# The dict value is the property (color, shape, etc) assigned to the dict keY
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


def create_plot_dict(
        df: pandas.DataFrame, variable: str, color: PlotProperty,
        shape: PlotProperty, order: bool, show_legend: bool = False
) -> list:
    """
    Creates the traces for a given column in the DataFrame, assigning each
    point shape and color.

    Args:
        df: DataFrame that contains the data
        variable: Which column to plot on the Y-axis
        color: What color to assign to each data point
        shape: What shape to assign to each data point
        order: If true, plot the points in the order given. Otherwise, plot
            by date
        show_legend: Should the trace have a legend displayed

    Returns:
        Plotly compliant list of traces to plot

    """
    result = []

    if order:
        df['x_axis'] = list(range(0, len(df)))
    else:
        df['x_axis'] = list(df['Run Date'])

    for g in df.groupby([color.name, shape.name]):
        color_name = g[0][0]
        shape_name = g[0][1]
        data = g[1]

        data_shape = data[shape.name].apply(
            lambda x: shape.properties[x]
        )

        p = {
            'x': list(data['x_axis']),
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


def create_subplot(
        rna_df: pandas.DataFrame, graph_list: list,
        color_col: str, shape_col: str, order: bool
) -> plotly.graph_objs.Figure:
    """
    Creates the subplots for the columns provided

    Args:
        rna_df: DataFrame containing the data
        graph_list: Which columns to plot
        color_col: Which column should specify the colors in the plot
        shape_col: Which column should specify the shapes in the plot
        order: If True, points will be plotted in their DataFrame order (0 to
            n - 1). Otherwise, plotted by date.

    Returns: The plotly figure that can be displayed

    Raises:
        ValueError: If more than 8 columns are given. Up to 8 subplots are
        supported.

    """
    if len(graph_list) > 8:
        raise ValueError('Can only plot up to 8 subplots')

    traces = []

    # Sort irrespective of capital letters
    color_names = sorted(
        rna_df[color_col].unique(),
        key=lambda x: x.upper()
    )
    colors = assign_consistent_property(color_names, COLOURS)
    color_prop = PlotProperty(color_col, colors)

    # Sort irrespective of capital letters
    shape_names = sorted(
        rna_df[shape_col].unique(),
        key=lambda x: x.upper()
    )
    shapes = assign_consistent_property(shape_names, SHAPES)
    shape_prop = PlotProperty(shape_col, shapes)

    for g in graph_list:
        if len(traces) == 0:
            traces.append(create_plot_dict(
                rna_df,
                g,
                color_prop,
                shape_prop,
                order,
                show_legend=True
            ))
        else:
            traces.append(create_plot_dict(
                rna_df,
                g,
                color_prop,
                shape_prop,
                order,
                show_legend=False
            ))

    # Hardcoded subplot positions (starting from top left and going across)
    rows = [1, 1, 2, 2, 3, 3, 4, 4][:len(traces)]
    cols = [1, 2, 1, 2, 1, 2, 1, 2][:len(traces)]
    max_rows = max(rows)

    # Each row in the DataFrame is plotted across all subplots
    # The other approach would be to plot each column in only one subplot
    traces = zip(*traces)

    fig = plotly.subplots.make_subplots(
        rows=max_rows, cols=2,
        subplot_titles=graph_list,
        print_grid=False,
    )

    # Go across each row and put each data point in the respective subplot
    for t in traces:
        fig.add_traces(
            t,
            rows=rows,
            cols=cols,
        )

    fig.update_layout(
        height=400*max_rows,
        template='plotly_white',
    )

    # If the data is sorted, the x-axis will be increasing numbers. Hide them
    fig.update_xaxes(showticklabels=not order)

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
                    options=[{'label': x, 'value': x} for x in ALL_PROJECTS],
                    value=ALL_PROJECTS
                ),
                html.Br(),
                html.Label('Kits:'),
                dcc.Dropdown(
                    id='kits_multi_drop',
                    multi=True,
                    options=[{'label': x, 'value': x} for x in ALL_KITS],
                    value=ALL_KITS
                ),
                html.Br(),
                html.Label('Dates: '),
                dcc.DatePickerRange(
                    id='date_picker',
                    display_format='YYYY-MM-DD',
                    min_date_allowed=min(RNA_DF['Run Date']),
                    max_date_allowed=max(RNA_DF['Run Date']),
                    start_date=min(RNA_DF['Run Date']),
                    end_date=max(RNA_DF['Run Date']),
                ),
                html.Br(),
                html.Br(),
                html.Label('Show Graphs:'),
                dcc.Dropdown(
                    id='graphs_to_plot',
                    multi=True,
                    options=[
                        {'label': x, 'value': x} for x in METRICS_TO_GRAPH
                    ],
                    value=METRICS_TO_GRAPH[:4]
                ),
                html.Br(),
                html.Div([
                    html.Div([
                        html.Label('Colour by:'),
                        dcc.Dropdown(
                            id='colour_by',
                            options=[
                                {'label': x['name'], 'value': x['id']} for x
                                in SHAPE_COLOUR_COLUMN
                            ],
                            value='Study Title'
                        ),
                    ], style={'width': '45%', 'display': 'inline-block', }),
                    html.Div([
                        html.Label('Shape by:'),
                        dcc.Dropdown(
                            id='shape_by',
                            options=[
                                {'label': x['name'], 'value': x['id']} for x
                                in SHAPE_COLOUR_COLUMN
                            ],
                            value='geo_prep_kit'
                        ),
                    ], style={
                        'width': '45%', 'display': 'inline-block',
                        'float': 'right'
                    }),
                ])
            ], style={'margin': '23px'})]
        ),
        html.Div([
            html.Div(
                sd_material_ui.RaisedButton(
                    id='filter_button', label='Options'
                ), style={'display': 'inline-block', }
            ),
            html.Div(
                sd_material_ui.RaisedButton(
                    id='update_from_table_button', label='Update Order',
                ), style={'display': 'inline-block', 'margin-left': '15px'}
            ),
        ]),
    ]),
    dcc.Loading(id="graph_loader_plot", children=[
        sd_material_ui.Paper(
            [dcc.Graph(
                id='graph_subplot',
            )]
        ),
    ]),
    dcc.Loading(id="graph_loader_data_table", children=[
        sd_material_ui.Paper(
            [dash_table.DataTable(
                id='data_table',
                columns=DEFAULT_TABLE_COLUMN + [
                    {'name': i, 'id': i} for i in METRICS_TO_GRAPH[:4]
                ],
                data=RNA_DF.to_dict('records'),
                page_size=50,
                sort_action='native',
                sort_mode='multi',
                export_format='csv'
            )]
        )
    ], type='circle')
])

try:
    from app import app
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    dep.Output('update_from_table_button', 'n_clicks'),
    [dep.Input('data_table', 'data')],
    [dep.State('update_from_table_button', 'n_clicks')]
)
def click_update_graph_button(_data, n_clicks):
    """
    A programmatic way to click the button when the data_table data changes,
    which causes the graphs to be rendered.

    This function is necessary because rendering the graphs when the data_table
    data changes does not work. See the rendering function for more details.

    Args:
        _data: Causes the button to be clicked, but not used
        n_clicks: The previous number of clicks on the button

    Returns: The incremented click number

    """
    n_clicks = 0 if n_clicks is None else n_clicks + 1
    return n_clicks


@app.callback(
    dep.Output('data_table', 'data'),
    [dep.Input('project_drawer', 'open')],
    [dep.State('project_multi_drop', 'value'),
     dep.State('kits_multi_drop', 'value'),
     dep.State('date_picker', 'start_date'),
     dep.State('date_picker', 'end_date'), ]
)
def populate_data_table(
        drawer_open: bool, projects: List[str], kits: List[str],
        start_date: str, end_date: str,
):
    """
    Given the filtering options in the side drawer, create the data table with
    the filtered data.

    Args:
        drawer_open: Has the drawer been opened (False is it was closed)
        projects: Which projects to plot
        kits: Which kits to plot
        start_date: From which date to display (inclusive)
        end_date: Up to which date to display (inclusive)

    Returns: The data to put in the data table

    """
    if drawer_open:
        raise dash.exceptions.PreventUpdate(
            'Drawer opening does not require recalculation'
        )

    to_table = RNA_DF[RNA_DF['Study Title'].isin(projects)]
    to_table = to_table[to_table['geo_prep_kit'].isin(kits)]
    to_table = to_table[to_table['Run Date'] >= pandas.to_datetime(start_date)]
    to_table = to_table[to_table['Run Date'] <= pandas.to_datetime(end_date)]

    return to_table.to_dict('records')


@app.callback(
    dep.Output('graph_subplot', 'figure'),
    [dep.Input('update_from_table_button', 'n_clicks')],
    [dep.State('data_table', 'derived_virtual_data'),
     dep.State('graphs_to_plot', 'value'),
     dep.State('colour_by', 'value'),
     dep.State('shape_by', 'value'),
     dep.State('data_table', 'sort_by')]
)
def graph_subplot(
        _clicks: int, data_to_plot: list, graphs: List[str],
        colour_by: str, shape_by: str, sort_by: Union[None, list]
):
    """
    Plots the data from the data table, preserving all sorting and filtering
    applied.

    The button that fires this callback had to be used. The simpler option
    would have been to fire it when the data table body is updated, but the
    `derived_virtual_data` property was linked to the body data and was not
    updated fast enough

    Args:
        _clicks: The click fires the callback, but is never used
        data_to_plot: This is the sorted and filtered data table data, which
            will be used for plots
        graphs: Which columns to plot
        colour_by: The column that determines data colour
        shape_by: The column that determines data shape
        sort_by: The columns on which data is sorted. The content does not
            matter for this function. If there is anything in this variable,
            the data will be plotted in order it is found in the input DataFrame

    Returns: The figures to plot

    """
    to_plot = pandas.DataFrame(data_to_plot)

    # The variable can either be None or an empty list when no sorting is done
    order = True if sort_by else False

    if len(to_plot) > 0:
        return create_subplot(
            to_plot,
            graphs,
            colour_by,
            shape_by,
            order,
        )
    else:
        return {}


@app.callback(
    dep.Output('project_drawer', 'open'),
    [dep.Input('filter_button', 'n_clicks')]
)
def open_project_drawer(n_clicks: Union[int, None]) -> bool:
    """
    Open the drawer when the Open Drawer button is clicked

    Args:
        n_clicks: How often has the button been clicked. None if it has never
            been clicked

    Returns: Should the drawer be opened

    """
    # Do no open if the button has never been clicked, otherwise open
    return n_clicks is not None


if __name__ == '__main__':
    app.run_server(debug=True)
