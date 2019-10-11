import pandas
import dash.dependencies as dep
import dash.exceptions
from typing import List, Union


import gsiqcetl.load
from gsiqcetl.bamqc.constants import CacheSchema
from gsiqcetl.pinery.sampleprovenance.constants import (
    CacheSchema as SampleProvenanceCacheSchema,
)

from dashi.plots.shiny_mimic import ShinyMimic
from dashi.plots.plot_scatter_subplot import create_subplot


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
        return create_subplot(
            to_plot,
            graphs,
            COL_RUN_DATE,
            RNA_COL.Library,
            colour_by,
            shape_by,
            order,
        )
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
