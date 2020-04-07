from typing import List, Tuple, Union

import dash_core_components as core
import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pandas import DataFrame
import pinery
import gsiqcetl.column
from .df_manipulation import sample_type_col, ml_col
from .sidebar_utils import runs_in_range


PINERY_COL = pinery.column.SampleProvenanceColumn
COMMON_COL = gsiqcetl.column.ColumnNames

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
    COMMON_COL.Reference: 'Reference: '
}


def create_data_label(
        df: pandas.DataFrame, cols: Union[None, List[str]]) -> List[str]:
    """
    Creates data labels that are in the correct order and have proper names
    appended. If the columns don't exist in the order constant, their label
    will be appended at the end in the order passed to this function.

    Args:
        df: The DataFrame that contains columns that match the labels
        cols: Which columns to generate the labels from

    Returns:

    """
    if cols is None:
        return []

    no_order = [x for x in cols if x not in DATA_LABEL_ORDER]
    ordered = sorted(cols, key=lambda x: DATA_LABEL_ORDER.index(x))
    ordered.extend(no_order)

    def apply_label(row):
        with_names = [
            DATA_LABEL_NAME.get(x, '') + str(row[x]) for x in ordered
        ]
        return "<br>".join(with_names)

    return df.apply(apply_label, axis=1)


def add_graphable_cols(df: DataFrame, graph_params: dict, shape_or_colour: dict,
        highlight_samples: List[str]=None, call_ready: bool=False) -> DataFrame:
    df = _fill_in_shape_col(df, graph_params["shape_by"], shape_or_colour)
    df = _fill_in_colour_col(df, graph_params["colour_by"], shape_or_colour,
                             highlight_samples, call_ready)
    df = _fill_in_size_col(df, highlight_samples, call_ready)
    return df


def _fill_in_shape_col(df: DataFrame, shape_col: str, shape_or_colour_values:
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


def _fill_in_colour_col(df: DataFrame, colour_col: str, shape_or_colour_values:
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


def _fill_in_size_col(df: DataFrame, highlight_samples: List[str] = None,
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
    df = _fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = _fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample)
    df = _fill_in_size_col(df, searchsample)
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
    df = _fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = _fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample, True)
    df = _fill_in_size_col(df, searchsample, True)
    return df


class Subplot:
    def __init__(self, title, y_label, df, x_col, y_col, graph_params, cutoffs,
                 showlegend=False):
        self.title = title
        self.y_label = y_label
        self.df = df
        self.x_col = x_col
        self.y_col = y_col
        self.graph_params = graph_params
        self.cutoffs = cutoffs
        self.showlegend = showlegend

    def traces(self):
        return generate_traces(self.df,
                               lambda d: d[self.x_col],
                               lambda d: d[self.y_col],
                               self.graph_params, self.cutoffs,
                               self.x_col, self.showlegend)

    def is_pct_graph(self):
        return self.y_label == GraphTitles.PCT


class SingleLaneSubplot(Subplot):
    def __init__(self, title, y_label, df, y_col, graph_params, cutoffs=[],
                 showlegend=False):
        super().__init__(title, y_label, df, PINERY_COL.SampleName, y_col,
                         graph_params, cutoffs, showlegend)


class CallReadySubplot(Subplot):
    def __init__(self, title, y_label, df, y_col, graph_params, cutoffs=[],
                 showlegend=False):
        super().__init__(title, y_label, df, ml_col, y_col,
                         graph_params, cutoffs, showlegend)


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



def generate_traces(
        sorted_data, x_fn, y_fn, graph_params, cutoff_lines=[],
        name_col=PINERY_COL.SampleName, showlegend=False):
    colourby = "colour_by"
    shapeby = "shape_by"
    shownames = "shownames_val"
    if sorted_data.empty:
        return [go.Scattergl(x=None, y=None)]

    highlight_df = sorted_data.loc[sorted_data['markersize']==BIG_MARKER_SIZE]
    traces = []
    grouped_data = sorted_data.groupby([graph_params[colourby],
                                        graph_params[shapeby]])
    #Unfortunately necessary
    if graph_params[colourby] == graph_params[shapeby]:
        name_format = lambda n: "{0}".format(n[0])
    else:
        name_format = lambda n: "{0}<br>{1}".format(n[0], n[1])
    for name, data in grouped_data:
        hovertext = create_data_label(data, graph_params[shownames])

        graph = go.Scattergl(
            x=x_fn(data),
            y=y_fn(data),
            name=name_format(name),
            hovertext=hovertext,
            showlegend=showlegend,
            legendgroup=name_format(name),
            mode="markers",
            marker={
                "symbol": data['shape'],
                "color": data['colour'], # Please note the 'u'
                "size": data['markersize']
            },
            # Hover labels are not cropped
            # https://github.com/plotly/plotly.js/issues/460
            hoverlabel={"namelength": -1},
        )
        traces.append(graph)
    for index, (cutoff_label, cutoff_value) in enumerate(cutoff_lines):
        traces.append(go.Scattergl( # Cutoff line
            x=sorted_data[name_col],
            y=[cutoff_value] * len(sorted_data),
            mode="lines",
            line={"width": 1, "color": CUTOFF_LINE_COLOURS[index], "dash": "dash"},
            name=cutoff_label
        ))
    if not highlight_df.empty:
        traces.append(go.Scattergl( # Draw highlighted items on top
            x=x_fn(highlight_df),
            y=y_fn(highlight_df),
            name="Highlighted Samples",
            mode='markers',
            legendgroup="gsi_reserved_highlighted_samples",
            showlegend=showlegend,
            marker={
                "symbol": highlight_df['shape'],
                "color": highlight_df['colour'],
                "size": highlight_df['markersize'],
                "opacity": 1
            }
        ))

    return traces


# writing a factory may be peak Java poisoning but it might help with all these parameters
def generate(title_text, sorted_data, x_fn, y_fn, axis_text, graph_params,
             cutoff_lines:
List[Tuple[str, float]]=[], name_col=PINERY_COL.SampleName):
    margin = go.layout.Margin(
                l=50,
                r=50,
                b=50,
                t=50,
                pad=4
            )

    traces = generate_traces(
        sorted_data, x_fn, y_fn, graph_params, cutoff_lines,
        name_col
    )

    return go.Figure(
        data=traces,
        layout=go.Layout(
            title=title_text,
            margin=margin,
            xaxis={'visible': False,
                'rangemode': 'normal',
                'autorange': True},
            yaxis={
                'title': {
                    'text': axis_text
                }
            },
            legend={
                'tracegroupgap': 0
            }
        )
    )


def generate_subplot(subplots: List[Subplot]):
    """
    Generates a subplot using functions that take a DataFrame and graph paramaters,
    returning a list of traces.

    """
    fig = make_subplots(
        rows=len(subplots),
        cols=1,
        vertical_spacing=0.02,
        # This can be enabled again when ploty bug is fixed
        # https://github.com/plotly/plotly.js/issues/4718
        # shared_xaxes=True,
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
        fig.update_yaxes(title_text=subplot.y_label, row=i+1, col=1)
        if subplot.is_pct_graph():
            fig.update_yaxes(range=[0, 100], row=i+1, col=1)

    fig.update_layout(
        height=350 * len(subplots),
        margin=go.layout.Margin(l=50, r=50, b=50, t=50, pad=4),
        legend=dict(tracegroupgap=0),
    )

    return fig


def generate_graphs(graph_id, df, graph_params, graph_funcs):
    """
    Subplots are necessary because of WebGL contexts limit (GR-932).
    """
    return core.Graph(
        id=graph_id,
        figure=generate_subplot([func(df, graph_params) for func in graph_funcs]),
        config={
            "toImageButtonOptions": {
                "width": None,
                "height": None
            }
        }  # This makes the downloaded png behave properly: https://community.plot.ly/t/save-plot-as-png-sizing-and-positioning/10166/6
    )


def update_graphs(df, graph_params, graph_funcs):
    return generate_subplot([func(df, graph_params) for func in graph_funcs])


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


