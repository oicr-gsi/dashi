from typing import List, Tuple, Union, Dict, Callable

import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_core_components as core
from pandas import DataFrame
import pinery
import gsiqcetl.column
from .df_manipulation import sample_type_col
from .sidebar_utils import runs_in_range
import re

PINERY_COL = pinery.column.SampleProvenanceColumn
COMMON_COL = gsiqcetl.column.ColumnNames
BEDTOOLS_COL = gsiqcetl.column.BedToolsGenomeCovCalculationsColumn
BAMQC_COL = gsiqcetl.column.BamQc4Column

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
    BAMQC_COL.Insert90Percentile: '90 Percentile Median Insert: ',
    BAMQC_COL.Insert10Percentile: '10 Percentile Median Insert: ',
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


def add_graphable_cols(df: DataFrame, graph_params: dict, shape_or_colour: dict,
        highlight_samples: List[str]=None, call_ready: bool=False) -> DataFrame:
    df = fill_in_shape_col(df, graph_params["shape_by"], shape_or_colour)
    df = fill_in_colour_col(df, graph_params["colour_by"], shape_or_colour,
                             highlight_samples, call_ready)
    df = fill_in_size_col(df, highlight_samples, call_ready)
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


def fill_in_colour_col(df: DataFrame, colour_col: str, shape_or_colour_values:
        dict, highlight_samples: List[str]=None, call_ready: bool=False):
    if df.empty:
        df['colour'] = pandas.Series
    else:
        all_colours = _get_colours_for_values(shape_or_colour_values[
                                            colour_col])
        # for each row, apply the colour according the colour col's value
        colour_col = df.apply(lambda row: all_colours.get(row[colour_col]),
                             axis=1)
        df = df.assign(colour=colour_col.values)
        if highlight_samples:
            sample_name_col = PINERY_COL.RootSampleName if call_ready else PINERY_COL.SampleName
            df.loc[df[sample_name_col].isin(highlight_samples), 'colour'] = '#F00'
    return df


def fill_in_size_col(df: DataFrame, highlight_samples: List[str] = None,
        call_ready: bool=False):
    df['markersize'] = 12
    if highlight_samples:
        sample_name_col = PINERY_COL.RootSampleName if call_ready else PINERY_COL.SampleName
        df.loc[df[sample_name_col].isin(highlight_samples), 'markersize'] = BIG_MARKER_SIZE
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
    df = fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample, True)
    df = fill_in_size_col(df, searchsample, True)
    return df


# writing a factory may be peak Java poisoning but it might help with all these parameters
def generate(title_text, sorted_data, x_fn, y_fn, axis_text, colourby, shapeby,
             hovertext_cols, cutoff_lines: List[Tuple[str, float]]=[],
             markermode="markers", bar_positive=None, bar_negative=None):
    margin = go.layout.Margin(
        l=50,
        r=50,
        b=50,
        t=50,
        pad=4
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
        'gridcolor': 'lightgrey'
    }
    # if axis_text == '%':
    #     y_axis['range'] = [0, 100]

    traces = _generate_traces(
        sorted_data,
        x_fn,
        y_fn,
        colourby,
        shapeby,
        hovertext_cols,
        cutoff_lines,
        markermode,
        bar_positive,
        bar_negative
    )

    return go.Figure(
        data = traces,
        layout = go.Layout(
            title=title_text,
            margin=margin,
            xaxis={'visible': False,
                   'rangemode': 'normal',
                   'autorange': True},
            yaxis=y_axis,
            legend = {
                'tracegroupgap': 0,
            },
        )
    )


def _generate_traces(
        sorted_data,
        x_fn,
        y_fn,
        colourby,
        shapeby,
        hovertext_cols,
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
                traces.append(_define_graph(data, x_fn, fn, bar_positive, bar_negative, hovertext_cols, markermode, name, name_format, graph_type, show_legend=(name_format(name) not in in_legend), additional_hovertext=fn(data).name))
                in_legend[name_format(name)] = True
    else: 
        for name, data in grouped_data:
            traces.append(_define_graph(data, x_fn, y_fn, bar_positive, bar_negative, hovertext_cols, markermode, name, name_format, graph_type))
    
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
                'autorange': True
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
                'autorange': True
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


def _define_graph(data, x_fn, y_fn, bar_positive, bar_negative, hovertext_cols, markermode, name, name_format, graph_type, show_legend=True, additional_hovertext=None):
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

    return dict(
        type=graph_type,
        x=x_fn(data),
        y=y_data,
        name=name_format(name),
        legendgroup=name_format(name),
        hovertext=hovertext,
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


# Generators for graphs used on multiple pages
def generate_total_reads(
        df: DataFrame, x_col: str, y_col: str, colour_by: str, shape_by: str,
        show_names: Union[None, str], cutoff_lines: List[Tuple[str, float]]=[]
) -> go.Figure:
    return generate(
        "Total Reads (Passed Filter)",
        df,
        lambda d: d[x_col],
        lambda d: d[y_col],
        "# PF Reads X 10^6",
        colour_by,
        shape_by,
        show_names,
        cutoff_lines,
    )


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
    def __init__(self, projects, runs, kits, tissue_materials, library_designs, reference):
        self.projects = projects
        self.runs = runs
        self.kits = kits
        self.tissue_materials = tissue_materials
        self.library_designs = library_designs
        self.reference = reference

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Run", "value": PINERY_COL.SequencerRunName},
            {"label": "Kit", "value": PINERY_COL.PrepKit},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
            {"label": "Reference", "value": COMMON_COL.Reference},
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.SequencerRunName: self.runs,
            PINERY_COL.PrepKit: self.kits,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            PINERY_COL.LibrarySourceTemplateType: self.library_designs,
            COMMON_COL.Reference: self.reference,
        }


class ColourShapeCallReady:
    def __init__(self, projects, library_designs, institutes, sample_types, tissue_materials, reference):
        self.projects = projects
        self.library_designs = library_designs
        self.institutes = institutes
        self.sample_types = sample_types
        self.tissue_materials = tissue_materials
        self.reference = reference

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Library Design", "value": PINERY_COL.LibrarySourceTemplateType},
            {"label": "Institute", "value": PINERY_COL.Institute},
            {"label": "Sample Type", "value": sample_type_col},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Reference", "value": COMMON_COL.Reference},
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.LibrarySourceTemplateType: self.library_designs,
            PINERY_COL.Institute: self.institutes,
            sample_type_col: self.sample_types,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            COMMON_COL.Reference: self.reference,
        }

class ColourShapeCfMeDIP:
    def __init__(self, projects, runs, institutes, sample_types, tissue_materials, reference):
        self.projects = projects
        self.runs = runs
        self.institutes = institutes
        self.sample_types = sample_types
        self.tissue_materials = tissue_materials
        self.reference = reference

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": PINERY_COL.StudyTitle},
            {"label": "Run", "value": PINERY_COL.SequencerRunName},
            {"label": "Institute", "value": PINERY_COL.Institute},
            {"label": "Sample Type", "value": sample_type_col},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Reference", "value": COMMON_COL.Reference},
        ]

    def items_for_df(self):
        return {
            PINERY_COL.StudyTitle: self.projects,
            PINERY_COL.SequencerRunName: self.runs,
            PINERY_COL.Institute: self.institutes,
            sample_type_col: self.sample_types,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            COMMON_COL.Reference: self.reference,
        }


class Subplot:
    def __init__(
            self,
            title,
            df,
            x_col,
            y_col,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            cutoff_lines,
            name_col,
            markermode,
            bar_positive,
            bar_negative,
            log_y
    ):
        self.title = title
        self.y_label = y_label
        self.df = df
        self.x_col = x_col
        self.y_col = y_col
        self.colourby = colourby
        self.shapeby = shapeby
        self.hovertext_cols = hovertext_cols
        self.cutoff_lines = [] if cutoff_lines is None else cutoff_lines
        self.name_col = name_col
        self.markermode = markermode
        self.bar_positive = bar_positive
        self.bar_negative = bar_negative
        self.log_y = log_y

    def traces(self):
        return _generate_traces(
            self.df,
            self.x_col,
            self.y_col,
            self.colourby,
            self.shapeby,
            self.hovertext_cols,
            self.cutoff_lines,
            self.name_col,
            self.markermode,
            self.bar_positive,
            self.bar_negative,
        )


class SingleLaneSubplot(Subplot):
    def __init__(
            self,
            title,
            df,
            x_col,
            y_col,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            cutoff_lines=None,
            name_col=PINERY_COL.SampleName,
            markermode="markers",
            bar_positive=None,
            bar_negative=None,
            log_y=False
    ):
        super().__init__(
            title,
            df,
            x_col,
            y_col,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            cutoff_lines,
            name_col,
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
            x_col,
            y_col,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            cutoff_lines=None,
            name_col=PINERY_COL.SampleName,
            markermode="markers",
            bar_positive=None,
            bar_negative=None,
            log_y=False,
    ):
        super().__init__(
            title,
            df,
            x_col,
            y_col,
            y_label,
            colourby,
            shapeby,
            hovertext_cols,
            cutoff_lines,
            name_col,
            markermode,
            bar_positive,
            bar_negative,
            log_y,
        )


# TODO: Currently not in use. Big question: How to deal with titles in Dashi?
class GraphTitles:
    AT_DROPOUT = "AT Dropout (%)"
    BASE_PAIRS = "Base Pairs"
    CALLABILITY_14_8 = "Callability (14x/8x) (%)"
    CODING = "Coding Bases (%)"
    CORRECT_READ_STRAND = "🚧 Correct Read Strand (%) -- DATA MAY BE SUSPECT 🚧"
    DEDUPLICATED_COVERAGE = "Deduplicated Coverage (x)"
    DUPLICATION = "Duplication (%)"
    DV200 = "DV200"
    EXCLUDED_DUE_TO_OVERLAP = "Excluded due to Overlap (%)"
    FIVE_TO_THREE = "5 to 3 Prime Bias"
    GC_DROPOUT = "GC Dropout (%)"
    HS_LIBRARY_SIZE = "HS Library Size"
    MEAN_INSERT_SIZE = "Mean Insert Size (bp)"
    MEAN_TARGET_COVERAGE = "Mean Target Coverage"
    NONE = ""
    NON_PRIMARY_READS = "Non-Primary Reads (%)"
    ON_TARGET_READS = "On-Target Reads (%)"
    PCT = "%"
    PLOIDY = "Ploidy"
    PURITY = "Purity (%)"
    RATIO = "Ratio"
    READ_COUNTS = "Read Counts"
    RIN = "RIN"
    RRNA_CONTAM = "Ribosomal RNA Contamination (%)"
    TOTAL_READS = "Total Reads (Passed Filter)"
    TOTAL_READS_Y = "# PF Reads x 10e6"
    UNIQUE_READS = "🚧 Unique Reads (Passed Filter) (%) -- DATA MAY BE SUSPECT 🚧"
    UNMAPPED_READS = "Unmapped Reads (%)"
    UNMAPPED_READS_COUNTS = "Unmapped Reads"
    X = "x"


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
        autorange=True
    )

    for i, subplot in enumerate([subplot for subplot in subplots]):
        y_type = "log" if subplot.log_y else "linear"
        fig.update_yaxes(
            title_text=subplot.y_label,
            type=y_type,
            row=i+1,
            col=1
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
