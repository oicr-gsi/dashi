from typing import List, Tuple, Union, Dict, Callable

import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dcc as core
from pandas import DataFrame
import pinery
import gsiqcetl.column
from .df_manipulation import sample_type_col, ml_col
from .sidebar_utils import runs_in_range
from .Mode import Mode
import re

PINERY_COL = pinery.column.SampleProvenanceColumn
COMMON_COL = gsiqcetl.column.ColumnNames
BEDTOOLS_COL = gsiqcetl.column.BedToolsGenomeCovCalculationsColumn
BAMQC_COL = gsiqcetl.column.BamQc4Column
CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
INSTRUMENT_COL = pinery.column.InstrumentWithModelColumn
RUN_COL = gsiqcetl.column.RunScannerFlowcellColumn

"""
Avoid the following symbols, which fail to render correctly:
'triangle-sw-dot', 'star-diamond-dot', 'hash', 'hash-dot', 'cross-thin',
'x-thin', 'y-up', 'y-down', 'y-left', 'y-right', 'line-ew', 'line-ns', 
'line-ne', 'line-nw', 'asterisk'
"""
ALL_SYMBOLS = [
    'circle', 'triangle-up', 'square', 'triangle-down', 'pentagon', 'diamond',
    'triangle-left', 'hexagon', 'cross', 'triangle-right', 'star', 'x',
    'hexagram', 'star-square', 'diamond-wide', 'square-cross', 'triangle-ne',
    'octagon', 'triangle-se', 'star-triangle-up', 'triangle-nw', 'diamond-tall',
    'triangle-sw', 'star-diamond', 'hourglass', 'bowtie', 'circle-cross',
    'circle-open', 'triangle-up-open', 'square-open', 'triangle-down-open',
    'pentagon-open', 'diamond-open', 'triangle-left-open', 'hexagon-open',
    'cross-open', 'triangle-right-open', 'star-open', 'x-open', 'hexagram-open',
    'star-square-open', 'diamond-wide-open', 'square-cross-open',
    'triangle-ne-open', 'octagon-open', 'cross-thin-open', 'triangle-se-open',
    'star-triangle-up-open', 'asterisk-open', 'triangle-nw-open',
    'diamond-tall-open', 'hash-open', 'triangle-sw-open', 'star-diamond-open',
    'hourglass-open', 'bowtie-open', 'circle-cross-open', 'circle-dot',
    'triangle-up-dot', 'square-dot', 'triangle-down-dot', 'pentagon-dot',
    'diamond-dot', 'triangle-left-dot', 'hexagon-dot', 'cross-dot',
    'triangle-right-dot', 'star-dot', 'x-dot', 'hexagram-dot',
    'star-square-dot', 'diamond-wide-dot', 'y-up-open', 'triangle-ne-dot',
    'octagon-dot', 'triangle-se-dot', 'star-triangle-up-dot', 'triangle-nw-dot',
    'line-ew-open', 'diamond-tall-dot', 'circle-open-dot', 'y-down-open',
    'triangle-up-open-dot', 'square-open-dot', 'triangle-down-open-dot',
    'pentagon-open-dot', 'diamond-open-dot', 'triangle-left-open-dot',
    'line-ns-open', 'hexagon-open-dot', 'cross-open-dot',
    'triangle-right-open-dot', 'star-open-dot', 'x-open-dot',
    'hexagram-open-dot', 'y-left-open', 'star-square-open-dot',
    'diamond-wide-open-dot',  'triangle-ne-open-dot', 'octagon-open-dot',
    'line-ne-open', 'triangle-se-open-dot', 'star-triangle-up-open-dot',
    'triangle-nw-open-dot', 'diamond-tall-open-dot', 'hash-open-dot',
    'y-right-open', 'triangle-sw-open-dot', 'star-diamond-open-dot',
    'line-nw-open'
]

# Colourblind-friendly palette shuffled to make more distinct
# Source https://personal.sron.nl/~pault/#sec:qualitative
# Tested with 'A11Y Color Blindness Empathy Test' extension for Firefox
COLOURS=[
    '#4477AA',  # blue
    '#CCBB44',  # yellow
    '#66CCEE',  # cyan
    '#EE6677',  # red
    '#228833',  # green
    '#AA3377'   # purple
]

CUTOFF_LINE_COLOURS = [
    '#222255', # dark blue
    '#225555', # dark cyan
    '#225522'  # dark green
]

BIG_MARKER_SIZE = 20

DATA_LABEL_ORDER = [
    PINERY_COL.SampleName,
    PINERY_COL.RootSampleName,
    PINERY_COL.TissueOrigin,
    PINERY_COL.TissueType,
    PINERY_COL.GroupID,
    COMMON_COL.Reference,
    PINERY_COL.TissuePreparation,
    PINERY_COL.PrepKit,
    PINERY_COL.SequencerRunName,
    PINERY_COL.LibrarySourceTemplateType
]

# If the Data Label is found here, the name is added. Eg: "Group ID: 12345"
DATA_LABEL_NAME = {
    PINERY_COL.GroupID: 'Group ID: ',
    PINERY_COL.TissuePreparation: 'Tissue Preparation: ',
    PINERY_COL.PrepKit: 'Kit: ',
    COMMON_COL.Reference: 'Reference: ',
    BEDTOOLS_COL.Coverage90Percentile: '90 Percentile Coverage: ',
    BEDTOOLS_COL.Coverage10Percentile: '10 Percentile Coverage: ',
    BAMQC_COL.CoverageMedian90Percentile: '90 Percentile Median Coverage: ',
    BAMQC_COL.CoverageMedian10Percentile: '10 Percentile Median Coverage: ',
    CALL_COL.NormalMinCoverage: 'Normal coverage for callability >= ',
    CALL_COL.TumorMinCoverage: 'Tumor coverage for callability >= ',
}

REPORT_TYPE = {
    "RunScanner": RUN_COL.Run,
    "Single-Lane": PINERY_COL.SampleName,
    "Call-Ready": PINERY_COL.RootSampleName
}


def create_data_label(
        df: pandas.DataFrame, cols: Union[None, List[str]], additional_text=None) -> List[str]:
    """
    Creates data labels that are in the correct order and have proper names
    appended. If the columns don't exist in the order constant, their label
    will be appended at the end in the order passed to this function.

    Args:
        df: The DataFrame that contains columns that match the labels
        cols: Which columns to generate the labels from
        additional_text: Text to add which is not taken from a column

    Returns:

    """
    if cols is None and additional_text is None:
        return []
    if cols is None:
        return df.apply(lambda r: "<br />"+additional_text, axis=1)

    no_order = [x for x in cols if x not in DATA_LABEL_ORDER]
    ordered = [x for x in cols if x in DATA_LABEL_ORDER]
    ordered = sorted(ordered, key=lambda x: DATA_LABEL_ORDER.index(x))
    ordered.extend(no_order)

    def apply_label(row):
        with_names = [
            DATA_LABEL_NAME.get(x, '') + str(row[x]) for x in ordered
        ]
        if additional_text:
            with_names += [additional_text]
        return "<br>".join(with_names)
    return df.apply(apply_label, axis=1)


def add_graphable_cols(
        df: DataFrame,
        graph_params: dict,
        shape_or_colour: dict,
        highlight_samples: List[str] = None,
        highlight_col: str = REPORT_TYPE["Single-Lane"]
) -> DataFrame:
    df = fill_in_shape_col(df, graph_params["shape_by"], shape_or_colour)
    df = fill_in_colour_col(df, graph_params["colour_by"], shape_or_colour,
                            highlight_samples, highlight_col)
    df = fill_in_size_col(df, highlight_samples, highlight_col)
    return df


def fill_in_shape_col(df: DataFrame, shape_col: str, shape_or_colour_values:
        dict):
    if df.empty:
        df['shape'] = pandas.Series
    else:
        all_shapes = _get_shapes_for_values(shape_or_colour_values[shape_col])
        # for each row, apply the shape according the shape col's value
        shape_col = df.apply(lambda row: all_shapes.get(row[shape_col]),
                             axis=1)
        df = df.assign(shape=shape_col.values)
    return df


def fill_in_colour_col(
        df: DataFrame,
        colour_col: str,
        shape_or_colour_values: dict,
        highlight_samples: List[str] = None,
        highlight_col: str = REPORT_TYPE["Single-Lane"]
):
    """
    Add a colour column that determines data point colour in plot
    
    Args:
        df: Input DataFrame
        colour_col: Which column to use to assign colours
        shape_or_colour_values: For each column that can be used in `colour_col`,
            provides a list of possible unique values
        highlight_samples: Which data points to highlight
        highlight_col: Which column to use for highlighting samples

    Returns:

    """
    if df.empty:
        df['colour'] = pandas.Series
    else:
        all_colours = _get_colours_for_values(shape_or_colour_values[colour_col])
        # for each row, apply the colour according the colour col's value
        colour_col = df.apply(
            lambda row: all_colours.get(row[colour_col]), axis=1
        )
        df = df.assign(colour=colour_col.values)
        if highlight_samples:
            df.loc[df[highlight_col].isin(highlight_samples), 'colour'] = '#F00'
    return df


def fill_in_size_col(
        df: DataFrame,
        highlight_samples: List[str] = None,
        highlight_col: str = REPORT_TYPE["Single-Lane"]
):
    """
    Set the size column that will determine the of size data points

    Args:
        df: Input DataFrame
        highlight_samples: Which data points to highlight (make bigger)
        highlight_col: Which column to use for highlighting

    Returns:

    """
    df['markersize'] = 12
    if highlight_samples:
        df.loc[df[highlight_col].isin(highlight_samples), 'markersize'] = BIG_MARKER_SIZE
    return df


def reshape_runscanner_df(
        df,
        instruments,
        first_sort,
        second_sort,
        colour_by,
        shape_by,
        shape_or_colour_values,
        searchsample,
):
    if not instruments:
        return DataFrame(columns=df.columns)

    if instruments:
        df = df[df[INSTRUMENT_COL.ModelName].isin(instruments)]

    sort_by = [first_sort, second_sort]
    df = df.sort_values(by=sort_by)
    df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = fill_in_colour_col(
        df, colour_by, shape_or_colour_values, searchsample, RUN_COL.Run
    )
    df = fill_in_size_col(df, searchsample, REPORT_TYPE["RunScanner"])

    return df


def reshape_single_lane_df(df, runs, instruments, projects, references, kits, library_designs,
        start_date, end_date, first_sort, second_sort, colour_by, shape_by,
        shape_or_colour_values, searchsample) -> DataFrame:
    """
    This performs dataframe manipulation based on the input filters, and gets the data into a
    graph-friendly form.
    """
    if not runs and not instruments and not projects and not kits and not library_designs and not references:
        df = DataFrame(columns=df.columns)

    if runs:
        df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs)]
    if instruments:
        df = df[df[pinery.column.InstrumentWithModelColumn.ModelName].isin(instruments)]
    if projects:
        df = df[df[pinery.column.SampleProvenanceColumn.StudyTitle].isin(projects)]
    if references:
        df = df[df[COMMON_COL.Reference].isin(references)]
    if kits:
        df = df[df[pinery.column.SampleProvenanceColumn.PrepKit].isin(kits)]
    if library_designs:
        df = df[df[pinery.column.SampleProvenanceColumn.LibrarySourceTemplateType].isin(
            library_designs)]
    df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs_in_range(start_date, end_date))]
    sort_by = [first_sort, second_sort]
    df = df.sort_values(by=sort_by)
    df["SampleNameExtra"] = df[PINERY_COL.SampleName].str.cat(
        [str(x) for x in range(len(df))], sep=".")
    df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample)
    df = fill_in_size_col(df, searchsample)
    return df


def reshape_call_ready_df(df, projects, references, tissue_preps, sample_types,
        first_sort, second_sort, colour_by, shape_by, shape_or_colour_values, searchsample):
    """
    This performs dataframe manipulation based on the input filters, and gets the data into a
    graph-friendly form.
    """
    if not projects and not tissue_preps and not sample_types and not references:
        df = DataFrame(columns=df.columns)

    if projects:
        df = df[df[pinery.column.SampleProvenanceColumn.StudyTitle].isin(projects)]
    if references:
        df = df[df[COMMON_COL.Reference].isin(references)]
    if tissue_preps:
        df = df[df[pinery.column.SampleProvenanceColumn.TissuePreparation].isin(
            tissue_preps)]
    if sample_types:
        df = df[df[sample_type_col].isin(sample_types)]

    sort_by = [first_sort, second_sort]
    df = df.sort_values(by=sort_by)
    df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = fill_in_colour_col(
        df, colour_by, shape_or_colour_values, searchsample, REPORT_TYPE["Call-Ready"]
    )
    df = fill_in_size_col(df, searchsample, REPORT_TYPE["Call-Ready"])
    return df


def is_empty_plot(trace_list) -> bool:
    """
    Check if any traces will be drawn on the graph

    Args:
        trace_list: The list of traces. Can be dict or plotly graph objects

    Returns:

    """
    for t in trace_list:
        if t['x'] is not None and len(t['x']):
            return False
        if t['y'] is not None and len(t['y']):
            return False

    return True


def generate(title_text, sorted_data, y_fn, axis_text, colourby, shapeby,
             hovertext_cols, page_mode, cutoff_lines: List[Tuple[str, float]]=[],
             x_fn=None, markermode="markers", bar_positive=None, bar_negative=None):
    margin = go.layout.Margin(
        l=50,
        r=50,
        b=50,
        t=50,
        pad=4
    )
    # if axis_text == '%':
    #     y_axis['range'] = [0, 100]

    if x_fn is None:
        if page_mode == Mode.IUS:
            x_fn = lambda d: d["SampleNameExtra"]
            display_x = lambda d: d[PINERY_COL.SampleName]
        elif page_mode == Mode.MERGED:
            x_fn = lambda d: d[ml_col]
            display_x = lambda d: d[ml_col]
    else:
        display_x = x_fn

    traces = _generate_traces(
        sorted_data,
        y_fn,
        colourby,
        shapeby,
        hovertext_cols,
        display_x,
        x_fn,
        cutoff_lines,
        markermode,
        bar_positive,
        bar_negative
    )

    y_axis = {
        'title': {
            'text': axis_text
        },
        'showline': True,
        'linewidth': 1,
        'linecolor': 'darkgrey',
        'zeroline': True,
        'zerolinewidth': 1,
        'zerolinecolor': 'darkgrey',
        'showgrid': True,
        'gridwidth': 1,
        'gridcolor': 'lightgrey',
        'rangemode': 'nonnegative' if is_empty_plot(traces) else 'normal'
    }

    return go.Figure(
        data = traces,
        layout = go.Layout(
            title=title_text,
            margin=margin,
            xaxis={'visible': False,
                   'rangemode': 'normal',
                   'autorange': True,
                   'categoryorder': 'array',
                   'categoryarray': x_fn(sorted_data)},
            yaxis=y_axis,
            legend = {
                'tracegroupgap': 0,
            },
        )
    )


def _generate_traces(
        sorted_data,
        y_fn,
        colourby,
        shapeby,
        hovertext_cols,
        display_x,
        x_fn=None,
        cutoff_lines: List[Tuple[str, float]]=[],
        markermode="markers",
        bar_positive=None,
        bar_negative=None
):
    highlight_df = sorted_data.loc[sorted_data['markersize']==BIG_MARKER_SIZE]
    # Webgl bugs occur with error bars: https://github.com/oicr-gsi/dashi/pull/170
    if bar_positive is None and bar_negative is None:
        graph_type = "scattergl"
    else:
        graph_type = "scatter"

    if sorted_data.empty:
        return [dict(
                type=graph_type,
                x=None,
                y=None
        )]

    traces = []
    grouped_data = sorted_data.groupby([colourby, shapeby]) #Unfortunately necessary
    if colourby == shapeby:
        name_format = lambda n: "{0}".format(n[0])
    else:
        name_format = lambda n: "{0}<br>{1}".format(n[0], n[1])

    if isinstance(y_fn, list):
        in_legend = {}
        for fn in y_fn:
            for name, data in grouped_data:
                traces.append(_define_graph(data, fn, bar_positive, bar_negative, hovertext_cols, markermode, name, name_format, graph_type, display_x, x_fn=x_fn, show_legend=(name_format(name) not in in_legend), additional_hovertext=fn(data).name))
                in_legend[name_format(name)] = True
    else: 
        for name, data in grouped_data:
            traces.append(_define_graph(data, y_fn, bar_positive, bar_negative, hovertext_cols, markermode, name, name_format, graph_type, display_x, x_fn=x_fn))    
    for index, (cutoff_label, cutoff_value) in enumerate(cutoff_lines):
        traces.append(dict( # Cutoff line
            type=graph_type,
            x=x_fn(sorted_data),
            y=[cutoff_value] * len(sorted_data),
            showlegend=False,
            mode="lines",
            line={"width": 1, "color": CUTOFF_LINE_COLOURS[index], "dash": "dash"},
            name=cutoff_label
        ))
    if not highlight_df.empty:
        if isinstance(y_fn, list):
            for fn in y_fn: # Don't like looping over this twice but unsure whether these can be guaranteed to be in foreground otherwise
                traces.append(dict( # Draw highlighted items on top
                    type=graph_type,
                    x=x_fn(highlight_df),
                    y=fn(highlight_df),
                    name="Highlighted Samples",
                    mode='markers',
                    showlegend=False,
                    marker={
                        "symbol": highlight_df['shape'],
                        "color": highlight_df['colour'],
                        "size": highlight_df['markersize'],
                        "opacity": 1
                    }
                ))
        else:
            traces.append(dict( # Draw highlighted items on top
                type=graph_type,
                x=x_fn(highlight_df),
                y=y_fn(highlight_df),
                name="Highlighted Samples",
                mode='markers',
                showlegend=False,
                marker={
                    "symbol": highlight_df['shape'],
                    "color": highlight_df['colour'],
                    "size": highlight_df['markersize'],
                    "opacity": 1
                }
            ))

    return traces


def generate_bar(df, criteria, x_fn, y_fn, title_text, yaxis_text, fill_color: Dict[str, str]=None):
    """
    Factory function to create a stacked bar graph

    Args:
        df: The DataFrame with the data
        criteria: Which columns to plot (first will be at the bottom of the stack)
        x_fn: Function that returns the x-axis values
        y_fn: Function that returns the y-axis values
        title_text: Title of the graph
        yaxis_text: Y-axis title
        fill_color: Dictionary specifying bar color. Key should match criteria and value
            is the color

    Returns:

    """
    graphs = []
    for col in criteria:
        marker = {}
        if fill_color is not None:
            if col in fill_color:
                marker['color'] = fill_color[col]

        graph = go.Bar(
            name = col + " (%)",
            x = x_fn(df),
            y = y_fn(df, col),
            marker=marker,
        )
        graphs.append(graph)
    
    figure = go.Figure(
        data = graphs,
        layout = go.Layout(
            title = title_text,
            xaxis={'visible': False,
                    'rangemode': 'normal',
                    'autorange': True},
            yaxis = {
                'title': {
                    'text': yaxis_text
                },
                'showline': True,
                'linewidth': 1,
                'linecolor': 'darkgrey',
                'zeroline': True,
                'zerolinewidth': 1,
                'zerolinecolor': 'darkgrey',
                'showgrid': True,
                'gridwidth': 1,
                'gridcolor': 'lightgrey',
                'autorange': True,
                'rangemode': 'nonnegative' if is_empty_plot(graphs) else 'normal'
            },
            margin = go.layout.Margin(
                l=50,
                r=50,
                b=50,
                t=50,
                pad=4
            ),
            bargap=0.05,
        )
    )
    figure.update_layout(barmode='stack')

    return figure


def generate_line(df, criteria, x_fn, y_fn, title_text, yaxis_text, xaxis_text=None):
    graphs = []
    for name, df in df.groupby(criteria):
        graph = go.Scattergl(
            name = '<br>'.join(str(x) for x in name) + '<br>',
            x = x_fn(df),
            y = y_fn(df),
            mode="lines",
            line={
                "color": re.search('#.{6}', str(df['colour'].unique())).group(0),
            }
        )
        graphs.append(graph)

    figure = go.Figure(
        data = graphs,
        layout = go.Layout(
            title = title_text,
            xaxis={'visible': xaxis_text is not None,
                   'rangemode': 'nonnegative',
                   'autorange': True,
                   'title': {
                       'text': xaxis_text
                   }},
            yaxis = {
                'title': {
                    'text': yaxis_text
                },
                'showline': True,
                'linewidth': 1,
                'linecolor': 'darkgrey',
                'zeroline': True,
                'zerolinewidth': 1,
                'zerolinecolor': 'darkgrey',
                'showgrid': True,
                'gridwidth': 1,
                'gridcolor': 'lightgrey',
                'autorange': True,
                'rangemode': 'nonnegative' if is_empty_plot(graphs) else 'normal'
            },
            margin = go.layout.Margin(
                l=50,
                r=50,
                b=50,
                t=50,
                pad=4
            ),
            hoverlabel={"namelength": -1},
        )
    )

    return figure


def _define_graph(data, y_fn, bar_positive, bar_negative, hovertext_cols, markermode, name, name_format, graph_type, display_x, x_fn=None, show_legend=True, additional_hovertext=None):
    y_data = y_fn(data)

    if bar_positive and bar_negative:
        error_y = dict(
            type='data',
            symmetric=False,
            array=data[bar_positive] - y_data,
            arrayminus=y_data - data[bar_negative],
            # Allows for only one color. `groupby` ensures this
            color=data['colour'].iloc[0],
            width=0,
        )

        # Error bar info is not displayed, so is added to hover label
        if hovertext_cols is None:
            hovertext_display_cols = [bar_positive, bar_negative]
        else:
            hovertext_display_cols = hovertext_cols + [bar_positive, bar_negative]
    else:
        error_y = None
        hovertext_display_cols = hovertext_cols

    hovertext = create_data_label(data, hovertext_display_cols, additional_hovertext)

    additional_str = ""
    if len(hovertext) > 0:
        additional_str = "<br />%{hovertext}"

    return dict(
        type=graph_type,
        x=x_fn(data),
        y=y_data,
        name=name_format(name),
        legendgroup=name_format(name),
        customdata=display_x(data),
        hovertext=hovertext,
        hovertemplate = "%{customdata}, %{y}" + additional_str, 
        showlegend=show_legend,
        mode=markermode,
        marker={
            "symbol": data['shape'],
            "color": data['colour'], # Please note the 'u'
            "size": data['markersize']
        },
        # Hover labels are not cropped
        # https://github.com/plotly/plotly.js/issues/460
        hoverlabel={"namelength": -1},
        error_y=error_y,
    )


def _get_dict_wrapped(key_list, value_list):
    kv_dict = {}
    index = 0
    for item in key_list:
        # loop back to beginning of value list
        if index >= len(value_list):
            index = 0
        kv_dict[item] = value_list[index]
        index += 1
    return kv_dict


def _get_shapes_for_values(shapeby: List[str]):
    return _get_dict_wrapped(shapeby, ALL_SYMBOLS)


def _get_colours_for_values(colourby: List[str]):
    return _get_dict_wrapped(colourby, COLOURS)


def get_initial_single_lane_values():
    return {
        "runs": [],
        "instruments": [],
        "projects": [],
        "references": [],
        "kits": [],
        "library_designs": [],
        "start_date": None,
        "end_date": None,
        "first_sort": pinery.column.SampleProvenanceColumn.StudyTitle,
        "second_sort": None,
        "colour_by": pinery.column.SampleProvenanceColumn.StudyTitle,
        "shape_by": pinery.column.SampleProvenanceColumn.PrepKit,
        "shownames_val": None,
    }


def get_initial_call_ready_values():
    return {
        "projects": [],
        "references": [],
        "kits": [],
        "library_designs": [],
        "institutes": [],
        "tissue_materials": [],
        "sample_types": [],
        "start_date": None,
        "end_date": None,
        "first_sort": pinery.column.SampleProvenanceColumn.StudyTitle,
        "second_sort": None,
        "colour_by": pinery.column.SampleProvenanceColumn.StudyTitle,
        "shape_by": sample_type_col,
        "shownames_val": None
    }

def get_initial_cfmedip_values():
    return {
        "runs": [],
        "instruments": [],
        "projects": [],
        "references": [],
        "kits": [],
        "library_designs": [],
        "start_date": None,
        "end_date": None,
        "first_sort": pinery.column.SampleProvenanceColumn.StudyTitle,
        "second_sort": None,
        "colour_by": pinery.column.SampleProvenanceColumn.StudyTitle,
        "shape_by": pinery.column.SampleProvenanceColumn.StudyTitle,
        "shownames_val": None,
    }


class ColourShapeSARSCoV2:
    def __init__(self, projects, runs, kits, tissue_materials, library_designs, seq_control_types):
        self.projects = projects
        self.runs = runs
        self.kits = kits
        self.tissue_materials = tissue_materials
        self.library_designs = library_designs
        self.seq_control_types = seq_control_types

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Run", "value": PINERY_COL.SequencerRunName},
            {"label": "Kit", "value": PINERY_COL.PrepKit},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
            {"label": "Sequencing Control Type", "value": PINERY_COL.SequencingControlType}
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.SequencerRunName: self.runs,
            PINERY_COL.PrepKit: self.kits,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            PINERY_COL.LibrarySourceTemplateType: self.library_designs,
            PINERY_COL.SequencingControlType: self.seq_control_types,
        }

class ColourShapeSingleLane:
    def __init__(self, projects, runs, kits, tissue_materials, tissue_origin, library_designs, reference):
        self.projects = projects
        self.runs = runs
        self.kits = kits
        self.tissue_materials = tissue_materials
        self.tissue_origin = tissue_origin
        self.library_designs = library_designs
        self.reference = reference

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Run", "value": PINERY_COL.SequencerRunName},
            {"label": "Kit", "value": PINERY_COL.PrepKit},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Tissue Origin", "value": PINERY_COL.TissueOrigin},
            {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
            {"label": "Reference", "value": COMMON_COL.Reference},
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.SequencerRunName: self.runs,
            PINERY_COL.PrepKit: self.kits,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            PINERY_COL.TissueOrigin: self.tissue_origin,
            PINERY_COL.LibrarySourceTemplateType: self.library_designs,
            COMMON_COL.Reference: self.reference,
        }


class ColourShapeCallReady:
    def __init__(self, projects, library_designs, institutes, sample_types, tissue_materials, tissue_origin, reference):
        self.projects = projects
        self.library_designs = library_designs
        self.institutes = institutes
        self.sample_types = sample_types
        self.tissue_materials = tissue_materials
        self.tissue_origin = tissue_origin
        self.reference = reference

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
            {"label": "Institute", "value": PINERY_COL.Institute},
            {"label": "Sample Type", "value": sample_type_col},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Tissue Origin", "value": PINERY_COL.TissueOrigin},
            {"label": "Reference", "value": COMMON_COL.Reference},
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.LibrarySourceTemplateType: self.library_designs,
            PINERY_COL.Institute: self.institutes,
            sample_type_col: self.sample_types,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            PINERY_COL.TissueOrigin: self.tissue_origin,
            COMMON_COL.Reference: self.reference,
        }

class ColourShapeCfMeDIP:
    def __init__(self, projects, runs, institutes, sample_types, tissue_materials, tissue_origin, reference):
        self.projects = projects
        self.runs = runs
        self.institutes = institutes
        self.sample_types = sample_types
        self.tissue_materials = tissue_materials
        self.tissue_origin = tissue_origin
        self.reference = reference

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Run", "value": PINERY_COL.SequencerRunName},
            {"label": "Institute", "value": PINERY_COL.Institute},
            {"label": "Sample Type", "value": sample_type_col},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Tissue Origin", "value": PINERY_COL.TissueOrigin},
            {"label": "Reference", "value": COMMON_COL.Reference},
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.SequencerRunName: self.runs,
            PINERY_COL.Institute: self.institutes,
            sample_type_col: self.sample_types,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            PINERY_COL.TissueOrigin: self.tissue_origin,
            COMMON_COL.Reference: self.reference,
        }


class ColourShapeRunscanner:
    def __init__(self, instrument, workflow_type):
        self.instrument = instrument
        self.workflow_type = workflow_type

    @staticmethod
    def dropdown():
        return [
            {"label": "Instrument", "value": INSTRUMENT_COL.ModelName},
            {"label": "Workflow Type", "value": RUN_COL.WorkflowType}
        ]

    def items_for_df(self):
        return {
            INSTRUMENT_COL.ModelName: self.instrument,
            RUN_COL.WorkflowType: self.workflow_type,
        }


class Subplot:
    def __init__(
            self,
            title,
            df,
            mode,
            y_fn,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            x_fn,
            cutoff_lines,
            markermode,
            bar_positive,
            bar_negative,
            log_y
    ):
        self.title = title
        self.y_label = y_label
        self.df = df
        self.x_fn = x_fn
        self.y_fn = y_fn
        self.colourby = colourby
        self.shapeby = shapeby
        self.hovertext_cols = hovertext_cols
        self.cutoff_lines = [] if cutoff_lines is None else cutoff_lines
        self.markermode = markermode
        self.bar_positive = bar_positive
        self.bar_negative = bar_negative
        self.log_y = log_y
        self.mode = mode

    def traces(self):
        self.display_x = None
        if self.x_fn is None:
            if self.mode == Mode.IUS:
                self.x_fn = lambda d: d["SampleNameExtra"]
                self.display_x = lambda d: d[PINERY_COL.SampleName]
            elif self.mode == Mode.MERGED:
                self.x_fn = lambda d: d[ml_col]
                self.display_x = lambda d: d[ml_col]
        else:
            self.display_x = self.x_fn

        return _generate_traces(
            self.df,
            self.y_fn,
            self.colourby,
            self.shapeby,
            self.hovertext_cols,
            self.display_x,
            self.x_fn,
            self.cutoff_lines,
            self.markermode,
            self.bar_positive,
            self.bar_negative,
        )


class SingleLaneSubplot(Subplot):
    def __init__(
            self,
            title,
            df,
            y_fn,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            x_fn=None,
            cutoff_lines=None,
            markermode="markers",
            bar_positive=None,
            bar_negative=None,
            log_y=False
    ):
        super().__init__(
            title,
            df,
            Mode.IUS,
            y_fn,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            x_fn,
            cutoff_lines,
            markermode,
            bar_positive,
            bar_negative,
            log_y,
        )


class CallReadySubplot(Subplot):
    def __init__(
            self,
            title,
            df,
            y_fn,
            y_label,
            colourby,
            shapeby,
            hovertext_cols=[],
            x_fn=None,
            cutoff_lines=None,
            markermode="markers",
            bar_positive=None,
            bar_negative=None,
            log_y=False,
    ):
        super().__init__(
            title,
            df,
            Mode.MERGED,
            y_fn,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            x_fn,
            cutoff_lines,
            markermode,
            bar_positive,
            bar_negative,
            log_y,
        )


def generate_plot_with_subplots(subplots: List[Subplot]):
    """
    Generates a subplot using functions that take a DataFrame and graph paramaters,
    returning a list of traces.
    """
    fig = make_subplots(
        rows=len(subplots),
        cols=1,
        vertical_spacing=0.02,
        shared_xaxes=True,
        subplot_titles=[subplot.title for subplot in subplots]
    )

    for i, trace in enumerate([subplot.traces() for subplot in subplots]):
        for t in trace:
            fig.add_trace(t, row=i+1, col=1)

    fig.update_xaxes(
        visible=False,
        rangemode="normal",
        autorange=True,
        # The x-axis is shared, so order all plots based on first one
        categoryorder='array',
        categoryarray=subplots[0].x_fn(subplots[0].df),
    )

    for i, subplot in enumerate([subplot for subplot in subplots]):
        y_type = "log" if subplot.log_y else "linear"
        fig.update_yaxes(
            title_text=subplot.y_label,
            type=y_type,
            rangemode='nonnegative' if len(subplot.df) == 0 else 'normal',
            row=i+1,
            col=1,
        )

        # All traces have the same legends
        # Only show those of the first trace
        if i != 0:
            fig.update_traces(showlegend=False, row=i+1, col=1)

        # if subplot.is_pct_graph():
        #    fig.update_yaxes(range=[0, 100], row=i+1, col=1)

    fig.update_yaxes(
        showline=True,
        linewidth=1,
        linecolor='darkgrey',
        zeroline=True,
        zerolinewidth=1,
        zerolinecolor='darkgrey',
        showgrid=True,
        gridwidth=1,
        gridcolor='lightgrey',
        autorange=True,
    )

    fig.update_layout(
        height=350 * len(subplots),
        margin=go.layout.Margin(l=50, r=50, b=50, t=50, pad=4),
        legend=dict(tracegroupgap=0),
        template="plotly_white",
    )

    # By default, subplot titles are center. Set to left alignment
    # https://community.plotly.com/t/subplot-title-alignment/33210/2
    for i in range(len(fig.layout.annotations)):
        fig.layout.annotations[i].update(
            x=-0,
            xanchor='left',
        )

    return fig


def generate_subplot_from_func(
        df: DataFrame,
        graph_params: Dict[str, str],
        graph_funcs: List[Callable[[DataFrame, Dict[str, str]], Subplot]]
):
    return generate_plot_with_subplots([func(df, graph_params) for func in graph_funcs])


def create_graph_element_with_subplots(graph_id, df, graph_params, graph_funcs):
    """
    Subplots are necessary because of WebGL contexts limit (GR-932).
    """
    return core.Graph(
        id=graph_id,
        figure=generate_plot_with_subplots([func(df, graph_params) for func in graph_funcs]),
        config={
            "toImageButtonOptions": {
                "width": None,
                "height": None
            }
        }  # This makes the downloaded png behave properly: https://community.plot.ly/t/save-plot-as-png-sizing-and-positioning/10166/6
    )
