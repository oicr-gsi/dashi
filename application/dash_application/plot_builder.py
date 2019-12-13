from typing import List, Tuple

import pandas
import plotly.graph_objects as go
from pandas import DataFrame
import pinery

PINERY_COL = pinery.column.SampleProvenanceColumn

ALL_SYMBOLS = [
    'circle', 'triangle-up', 'square', 'triangle-down', 'pentagon', 'diamond',
    'triangle-left', 'hexagon', 'cross', 'triangle-right', 'star', 'x',
    'hexagram', 'star-square', 'diamond-wide', 'square-cross', 'triangle-ne',
    'octagon',
    'triangle-se', 'star-triangle-up',
    'triangle-nw', 'diamond-tall', 'hash', 'triangle-sw', 'star-diamond',
    'hourglass', 'bowtie', 'circle-cross', 'y-up', 'circle-open',
    'triangle-up-open', 'square-open', 'triangle-down-open', 'pentagon-open',
    'diamond-open', 'triangle-left-open', 'hexagon-open', 'cross-open',
    'triangle-right-open', 'line-ew', 'star-open', 'x-open', 'hexagram-open',
    'star-square-open', 'diamond-wide-open', 'square-cross-open',
    'triangle-ne-open', 'y-down', 'octagon-open', 'cross-thin-open',
    'triangle-se-open', 'star-triangle-up-open', 'asterisk-open',
    'triangle-nw-open', 'line-ns', 'diamond-tall-open', 'hash-open',
    'triangle-sw-open', 'star-diamond-open', 'hourglass-open', 'bowtie-open',
    'circle-cross-open', 'circle-dot', 'y-left', 'triangle-up-dot',
    'square-dot', 'triangle-down-dot', 'pentagon-dot', 'diamond-dot',
    'triangle-left-dot', 'hexagon-dot', 'cross-dot', 'line-ne', 'y-right',
    'triangle-right-dot', 'star-dot', 'x-dot', 'hexagram-dot', 'line-nw',
    'star-square-dot', 'diamond-wide-dot',  
    'y-up-open',
    'triangle-ne-dot', 'octagon-dot', 
     'triangle-se-dot',
    'star-triangle-up-dot', 
    'triangle-nw-dot', 'line-ew-open',
    'diamond-tall-dot', 'hash-dot', 'triangle-sw-dot', 'star-diamond-dot',
    'circle-open-dot',
    'y-down-open', 'triangle-up-open-dot', 'square-open-dot',
    'triangle-down-open-dot', 'pentagon-open-dot', 'diamond-open-dot',
    'triangle-left-open-dot', 'line-ns-open', 'hexagon-open-dot',
    'cross-open-dot', 'triangle-right-open-dot', 'star-open-dot', 'x-open-dot',
    'hexagram-open-dot', 'y-left-open', 'star-square-open-dot',
    'diamond-wide-open-dot',  
    'triangle-ne-open-dot',
    'octagon-open-dot', 
    'line-ne-open',
    'triangle-se-open-dot', 'star-triangle-up-open-dot', 
    'triangle-nw-open-dot', 'diamond-tall-open-dot', 'hash-open-dot',
    'y-right-open', 'triangle-sw-open-dot', 'star-diamond-open-dot',
    'line-nw-open'
]

PLOTLY_DEFAULT_COLOURS=[
    '#1f77b4',  # muted blue
    '#ff7f0e',  # safety orange
    '#2ca02c',  # cooked asparagus green
    '#d62728',  # brick red
    '#9467bd',  # muted purple
    '#8c564b',  # chestnut brown
    '#e377c2',  # raspberry yogurt pink
    '#7f7f7f',  # middle gray
    '#bcbd22',  # curry yellow-green
    '#17becf'   # blue-teal
]

BIG_MARKER_SIZE = 20

def fill_in_shape_col(df: DataFrame, shape_col: str, shape_or_colour_values:
        dict):
    if df.empty:
        df['shape'] = pandas.Series
    else:
        all_shapes = get_shapes_for_values(shape_or_colour_values[
                                            shape_col].tolist())
        # for each row, apply the shape according the shape col's value
        shape_col = df.apply(lambda row: all_shapes.get(row[shape_col]),
                             axis=1)
        df = df.assign(shape=shape_col.values)
    return df

def fill_in_colour_col(df: DataFrame, colour_col: str, shape_or_colour_values:
        dict, highlight_samples=None):
    if df.empty:
        df['colour'] = pandas.Series
    else:
        all_colours = get_colours_for_values(shape_or_colour_values[
                                            colour_col].tolist())
        # for each row, apply the colour according the colour col's value
        colour_col = df.apply(lambda row: all_colours.get(row[colour_col]),
                             axis=1)
        df = df.assign(colour=colour_col.values)
        if highlight_samples:
            df.loc[df[PINERY_COL.SampleName].isin(highlight_samples), 'colour'] = '#F00'
    return df

def fill_in_size_col(df: DataFrame, highlight_samples=None):
    df['markersize'] = 12
    if highlight_samples:
        df.loc[df[PINERY_COL.SampleName].isin(highlight_samples), 'markersize'] = BIG_MARKER_SIZE
    return df

# writing a factory may be peak Java poisoning but it might help with all these parameters
def generate(title_text, sorted_data, x_fn, y_fn, axis_text, colourby, shapeby,
             hovertext_type, line_y=None):
    highlight_df = sorted_data.loc[sorted_data['markersize']==BIG_MARKER_SIZE]
    margin = go.layout.Margin(
                l=50,
                r=50,
                b=50,
                t=50,
                pad=4
            )
    if sorted_data.empty:
        return go.Figure(
            data=[go.Scattergl(
                x=None,
                y=None
            )],
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
                }
            )
        )
    traces = []
    grouped_data = sorted_data.groupby([colourby, shapeby]) #Unfortunately necessary
    if colourby == shapeby:
        name_format = lambda n: "{0}".format(n[0])
    else:
        name_format = lambda n: "{0} {1}".format(n[0], n[1])
    for name, data in grouped_data:
        if hovertext_type == 'none':
            text_content = None
        else:
            text_content = data[hovertext_type]
        graph = go.Scattergl(
            x=x_fn(data),
            y=y_fn(data),
            name=name_format(name),
            hovertext=text_content,
            showlegend=True,
            mode="markers",
            marker={
                "symbol": data['shape'],
                "color": data['colour'], # Please note the 'u'
                "size": data['markersize']
            }
        )
        traces.append(graph)
    if line_y is not None:
        traces.append(go.Scattergl( # Cutoff line
            x=sorted_data[PINERY_COL.SampleName], 
            y=[line_y] * len(sorted_data),
            mode="lines",
            line={"width": 1, "color": "black", "dash": "dash"},
            name="Cutoff"
        ))
    if not highlight_df.empty:
        traces.append(go.Scattergl( # Draw highlighted items on top
            x=x_fn(highlight_df),
            y=y_fn(highlight_df),
            name="Highlighted Samples",
            mode='markers',
            marker={
                "symbol": highlight_df['shape'],
                "color": highlight_df['colour'],
                "size": highlight_df['markersize'],
                "opacity": 1
            }
        ))
    return go.Figure(
        data = traces,
        layout = go.Layout(
            title=title_text,
            margin=margin,
            xaxis={'visible': False,
                'rangemode': 'normal',
                'autorange': True},
            yaxis={
                'title': {
                    'text': axis_text
                }
            }
        )
    )

def get_dict_wrapped(key_list, value_list):
    kv_dict = {}
    index = 0
    for item in key_list:
        # loop back to beginning of value list
        if index >= len(value_list):
            index = 0
        kv_dict[item] = value_list[index]
        index += 1
    return kv_dict

def get_shapes_for_values(shapeby: List[str]):
    return get_dict_wrapped(shapeby, ALL_SYMBOLS)

def get_colours_for_values(colourby: List[str]):
    return get_dict_wrapped(colourby, PLOTLY_DEFAULT_COLOURS)

def terminal_output(data:DataFrame, limits:List[Tuple[str, str, float]]) -> str:
    if data.empty:
        return "No data!"

    output = ""

    for (name, column, cutoff) in limits:
        output += "$failed_%s\n" %name
        newline = False
        linenumber = 0
        for failed in data.loc[data[column] < cutoff][pinery.column.SampleProvenanceColumn.SampleName]:
            if not newline:
                output += "[{0}] ".format(linenumber)
            output += "\"" + failed + "\"\t\t"
            if newline:
                output += "\n"
            newline = not newline
            linenumber += 1
    if output:
        return output
    else:
        return "All samples within cutoffs"
