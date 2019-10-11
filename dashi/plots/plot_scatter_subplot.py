import pandas
import plotly.subplots
import plotly.graph_objs

import collections
import itertools

# A convenience container that links how a metric should be graphed
# The name is the column name
# The properties is a dict
# The dict key is a value found in the column
# The dict value is the property (color, shape, etc) assigned to the dict keY
PlotProperty = collections.namedtuple("PlotProperty", ["name", "properties"])


def assign_consistent_property(values: list, prop: list) -> dict:
    """
    Entries in the DataFrame column (project, tissue, kit) need to be assigned
    consistent properties (color, shape) across all plots. This does is fairly
    simply, by looping in order through each unique column entry and assigning
    them the next available property. Property lists cannot run out, as it loops
    back to the beginning.

    Args:
        values: The column entries. Need to be unique.
        prop: The plotting properties to assign to each entry

    Returns: A dictionary with keys being the unique DataFrame column entries
        and the dictionary values being the plotting properties (color, shape).

    """
    result = {}
    prop = itertools.cycle(prop)

    for v in values:
        result[v] = next(prop)

    return result


def create_plot_dict(
    df: pandas.DataFrame,
    variable: str,
    date_column_name: str,
    library_column_name: str,
    color: PlotProperty,
    shape: PlotProperty,
    order: bool,
    show_legend: bool = False,
) -> list:
    """
    Creates the traces for a given column in the DataFrame, assigning each
    point shape and color.

    Args:
        df: DataFrame that contains the data
        variable: Which column to plot on the Y-axis
        date_column_name: Which column contains the dates
        library_column_name: Which column contains library names
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
        df["x_axis"] = list(range(0, len(df)))
    else:
        df["x_axis"] = list(df[date_column_name])

    for g in df.groupby([color.name, shape.name]):
        color_name = g[0][0]
        shape_name = g[0][1]
        data = g[1]

        data_shape = data[shape.name].apply(lambda x: shape.properties[x])

        p = {
            "x": list(data["x_axis"]),
            "y": list(data[variable]),
            "type": "scattergl",
            "mode": "markers",
            "name": color_name + "<br>" + shape_name,
            "text": list(data[library_column_name]),
            "legendgroup": color_name,
            "showlegend": show_legend,
            "marker": {
                "color": color.properties[color_name],
                "symbol": data_shape,
            },
            # Hover labels are not cropped
            # https://github.com/plotly/plotly.js/issues/460
            "hoverlabel": {"namelength": -1},
        }

        result.append(p)

    return result


def create_subplot(
    rna_df: pandas.DataFrame,
    graph_list: list,
    date_column_name: str,
    library_column_name: str,
    color_col: str,
    shape_col: str,
    order: bool,
) -> plotly.graph_objs.Figure:
    """
    Creates the subplots for the columns provided

    Args:
        rna_df: DataFrame containing the data
        graph_list: Which columns to plot
        date_column_name: Which column contains the dates
        library_column_name: Which column contains library names
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
        raise ValueError("Can only plot up to 8 subplots")

    traces = []

    # Sort irrespective of capital letters
    color_names = sorted(rna_df[color_col].unique(), key=lambda x: x.upper())
    colors = assign_consistent_property(color_names, COLOURS)
    color_prop = PlotProperty(color_col, colors)

    # Sort irrespective of capital letters
    shape_names = sorted(rna_df[shape_col].unique(), key=lambda x: x.upper())
    shapes = assign_consistent_property(shape_names, SHAPES)
    shape_prop = PlotProperty(shape_col, shapes)

    for g in graph_list:
        if len(traces) == 0:
            traces.append(
                create_plot_dict(
                    rna_df,
                    g,
                    date_column_name,
                    library_column_name,
                    color_prop,
                    shape_prop,
                    order,
                    show_legend=True,
                )
            )
        else:
            traces.append(
                create_plot_dict(
                    rna_df,
                    g,
                    date_column_name,
                    library_column_name,
                    color_prop,
                    shape_prop,
                    order,
                    show_legend=False,
                )
            )

    # Hardcoded subplot positions (starting from top left and going across)
    rows = [1, 2, 3, 4, 5, 6, 7, 8][: len(traces)]
    cols = [1, 1, 1, 1, 1, 1, 1, 1][: len(traces)]
    max_rows = max(rows)

    # Each row in the DataFrame is plotted across all subplots
    # The other approach would be to plot each column in only one subplot
    traces = zip(*traces)

    fig = plotly.subplots.make_subplots(
        rows=max_rows, cols=1, subplot_titles=graph_list, print_grid=False
    )

    # Go across each row and put each data point in the respective subplot
    for t in traces:
        fig.add_traces(t, rows=rows, cols=cols)

    fig.update_layout(height=400 * max_rows, template="plotly_white")

    # If the data is sorted, the x-axis will be increasing numbers. Hide them
    fig.update_xaxes(showticklabels=not order)

    # If you want legend at the bottom
    # fig['layout']['legend'].update(orientation="h")

    return fig


# The colours that are used in the graphs
COLOURS = [
    "#1f77b4",
    "#aec7e8",
    "#ff7f0e",
    "#ffbb78",
    "#2ca02c",
    "#98df8a",
    "#d62728",
    "#ff9896",
    "#9467bd",
    "#c5b0d5",
    "#8c564b",
    "#c49c94",
    "#e377c2",
    "#f7b6d2",
    "#7f7f7f",
    "#c7c7c7",
    "#bcbd22",
    "#dbdb8d",
    "#17becf",
    "#9edae5",
]

# The shapes of the points to use in the graph
# More can be added if the future needs it
# See https://plot.ly/python/reference/#scatter-marker
SHAPES = [
    "circle",
    "square",
    "diamond",
    "cross",
    "x",
    "triangle-up",
    "triangle-down",
    "triangle-left",
    "triangle-right",
    "pentagon",
    "star",
]
