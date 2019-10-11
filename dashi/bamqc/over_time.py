import collections
import pandas
import dash.dependencies as dep
import dash.exceptions
import itertools
from typing import List, Union

import plotly.subplots
import plotly.graph_objs

import gsiqcetl.load
from gsiqcetl.bamqc.constants import CacheSchema
from gsiqcetl.pinery.sampleprovenance.constants import (
    CacheSchema as SampleProvenanceCacheSchema,
)

from dashi.plots.shiny_mimic import ShinyMimic


RNA_DF = gsiqcetl.load.bamqc(CacheSchema.v1)
RNA_COL = gsiqcetl.load.bamqc_columns(CacheSchema.v1)

COL_RUN_DATE = "Run Date"
PROJECT = "Project"
FRACTION_ON_TARGET = "Read Fraction on Target"
FRACTION_MAPPED = "Read Fraction Mapped"
FRACTION_SECONDARY = "Read Fraction Secondary"

# The Run Name is used to extract the date
RNA_DF[COL_RUN_DATE] = (
    RNA_DF[RNA_COL.Run].dropna().apply(lambda x: x.split("_")[0])
)
# Some runs do not have the proper format and will be excluded
RNA_DF = RNA_DF[RNA_DF[COL_RUN_DATE].str.isnumeric()]
RNA_DF[COL_RUN_DATE] = pandas.to_datetime(RNA_DF[COL_RUN_DATE], yearfirst=True)

RNA_DF[PROJECT] = RNA_DF[RNA_COL.Library].apply(lambda x: x.split("_")[0])

RNA_DF[FRACTION_ON_TARGET] = (
    RNA_DF[RNA_COL.ReadsOnTarget] / RNA_DF[RNA_COL.TotalReads]
)
RNA_DF[FRACTION_MAPPED] = (
    RNA_DF[RNA_COL.MappedReads] / RNA_DF[RNA_COL.TotalReads]
)
RNA_DF[FRACTION_SECONDARY] = (
    RNA_DF[RNA_COL.NonPrimaryReads] / RNA_DF[RNA_COL.TotalReads]
)

# Pull in meta data from Pinery
# noinspection PyTypeChecker
PINERY: pandas.DataFrame = gsiqcetl.load.pinery_sample_provenance(
    SampleProvenanceCacheSchema.v1
)
PINERY_COL = gsiqcetl.load.pinery_sample_provenance_columns(
    SampleProvenanceCacheSchema.v1
)

PINERY = PINERY[
    [
        PINERY_COL.SampleName,
        PINERY_COL.SequencerRunName,
        PINERY_COL.LaneNumber,
        PINERY_COL.PrepKit,
        PINERY_COL.LibrarySourceTemplateType,
        PINERY_COL.TissueOrigin,
        PINERY_COL.TissueType,
        PINERY_COL.TissuePreparation,
    ]
]

RNA_DF = RNA_DF.merge(
    PINERY,
    how="left",
    left_on=[RNA_COL.Library, RNA_COL.Run, RNA_COL.Lane],
    right_on=[
        PINERY_COL.SampleName,
        PINERY_COL.SequencerRunName,
        PINERY_COL.LaneNumber,
    ],
)

# NaN kits need to be changed to a str. Use the existing Unspecified
RNA_DF = RNA_DF.fillna({PINERY_COL.PrepKit: "Unspecified"})
RNA_DF = RNA_DF.fillna({PINERY_COL.LibrarySourceTemplateType: "Unknown"})
# NaN Tissue Origin is set to `nn`, which is used by MISO for unknown
RNA_DF = RNA_DF.fillna({PINERY_COL.TissueOrigin: "nn"})
# NaN Tissue Type is set to `n`, which is used by MISO for unknown
RNA_DF = RNA_DF.fillna({PINERY_COL.TissueType: "n"})
RNA_DF = RNA_DF.fillna({PINERY_COL.TissuePreparation: "Unknown"})

# Which metrics can be plotted
METRICS_TO_GRAPH = (
    FRACTION_ON_TARGET,
    FRACTION_MAPPED,
    RNA_COL.InsertMean,
    RNA_COL.ReadsPerStartPoint,
    RNA_COL.TotalReads,
    FRACTION_SECONDARY,
)

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

# Which columns will the data table always have
DEFAULT_TABLE_COLUMN = [
    {"name": "Library", "id": RNA_COL.Library},
    {"name": "Project", "id": PROJECT},
    {"name": "Run", "id": RNA_COL.Run},
    {"name": "Lane", "id": RNA_COL.Lane},
    {"name": "Kit", "id": PINERY_COL.PrepKit},
    {"name": "Library Design", "id": PINERY_COL.LibrarySourceTemplateType},
    {"name": "Tissue Origin", "id": PINERY_COL.TissueOrigin},
    {"name": "Tissue Type", "id": PINERY_COL.TissueType},
    {"name": "Tissue Material", "id": PINERY_COL.TissuePreparation},
]

# Columns on which shape and colour can be set
SHAPE_COLOUR_COLUMN = [
    {"name": "Project", "id": PROJECT},
    {"name": "Kit", "id": PINERY_COL.PrepKit},
    {"name": "Library Design", "id": PINERY_COL.LibrarySourceTemplateType},
    {"name": "Tissue Origin", "id": PINERY_COL.TissueOrigin},
    {"name": "Tissue Type", "id": PINERY_COL.TissueType},
    {"name": "Tissue Material", "id": PINERY_COL.TissuePreparation},
]

# A convenience container that links how a metric should be graphed
# The name is the column name
# The properties is a dict
# The dict key is a value found in the column
# The dict value is the property (color, shape, etc) assigned to the dict keY
PlotProperty = collections.namedtuple("PlotProperty", ["name", "properties"])

plot_creator = ShinyMimic(
    RNA_DF,
    "bamqc_over_time",
    METRICS_TO_GRAPH,
    SHAPE_COLOUR_COLUMN,
    SHAPE_COLOUR_COLUMN,
    PROJECT,
    PINERY_COL.PrepKit,
    COL_RUN_DATE,
)


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
        df["x_axis"] = list(df[COL_RUN_DATE])

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
            "text": list(data[RNA_COL.Library]),
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
    color_col: str,
    shape_col: str,
    order: bool,
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
                    rna_df, g, color_prop, shape_prop, order, show_legend=True
                )
            )
        else:
            traces.append(
                create_plot_dict(
                    rna_df, g, color_prop, shape_prop, order, show_legend=False
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


layout = plot_creator.generate_layout(
    4,
    PROJECT,
    PINERY_COL.PrepKit,
    DEFAULT_TABLE_COLUMN + [{"name": i, "id": i} for i in METRICS_TO_GRAPH],
)

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    dep.Output(plot_creator.id_button_update, "n_clicks"),
    [dep.Input(plot_creator.id_data_table, "data")],
    [dep.State(plot_creator.id_button_update, "n_clicks")],
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
    dep.Output(plot_creator.id_data_table, "data"),
    [dep.Input(plot_creator.id_drawer, "open")],
    [
        dep.State(plot_creator.id_multiselect_project, "value"),
        dep.State(plot_creator.id_multiselect_kit, "value"),
        dep.State(plot_creator.id_date_picker, "start_date"),
        dep.State(plot_creator.id_date_picker, "end_date"),
    ],
)
def populate_data_table(
    drawer_open: bool,
    projects: List[str],
    kits: List[str],
    start_date: str,
    end_date: str,
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
            "Drawer opening does not require recalculation"
        )

    to_table = RNA_DF[RNA_DF[PROJECT].isin(projects)]
    to_table = to_table[to_table[PINERY_COL.PrepKit].isin(kits)]
    to_table = to_table[
        to_table[COL_RUN_DATE] >= pandas.to_datetime(start_date)
    ]
    to_table = to_table[to_table[COL_RUN_DATE] <= pandas.to_datetime(end_date)]

    return to_table.to_dict("records")


@app.callback(
    dep.Output(plot_creator.id_plot, "figure"),
    [dep.Input(plot_creator.id_button_update, "n_clicks")],
    [
        dep.State(plot_creator.id_data_table, "derived_virtual_data"),
        dep.State(plot_creator.id_multiselect_plots, "value"),
        dep.State(plot_creator.id_select_colour, "value"),
        dep.State(plot_creator.id_select_shape, "value"),
        dep.State(plot_creator.id_data_table, "sort_by"),
    ],
)
def graph_subplot(
    _clicks: int,
    data_to_plot: list,
    graphs: List[str],
    colour_by: str,
    shape_by: str,
    sort_by: Union[None, list],
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
        return create_subplot(to_plot, graphs, colour_by, shape_by, order)
    else:
        return {}


@app.callback(
    dep.Output(plot_creator.id_drawer, "open"),
    [dep.Input(plot_creator.id_button_options, "n_clicks")],
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


if __name__ == "__main__":
    app.run_server(debug=True)
