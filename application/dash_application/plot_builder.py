from typing import List

import pandas
import plotly.graph_objects as go

# TODO: if this remains necessary i'll be mad. Can we get it from plotly itself?
# ALL_SYMBOLS = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up',
#                'triangle-down',  'triangle-left', 'triangle-right',
#                'circle-open',
#                'circle-dot',
#                 'circle-open-dot', 'square-open',
#                 'square-dot', 'square-open-dot',
#                 'diamond-open', 'diamond-dot',
#                 'diamond-open-dot', 'cross-open',
#                 'cross-dot', 'cross-open-dot', 'x-open',
#                 'x-dot', 'x-open-dot',
#                 'triangle-up-open', 'triangle-up-dot',
#                 'triangle-up-open-dot',
#                 'triangle-down-open', 'triangle-down-dot',
#                 'triangle-down-open-dot',
#                 'triangle-left-open', 'triangle-left-dot',
#                 'triangle-left-open-dot',
#                 'triangle-right-open', 'triangle-right-dot',
#                 'triangle-right-open-dot', 'triangle-ne',
#                 'triangle-ne-open', 'triangle-ne-dot',
#                 'triangle-ne-open-dot', 'triangle-se',
#                 'triangle-se-open', 'triangle-se-dot',
#                 'triangle-se-open-dot', 'triangle-sw',
#                 'triangle-sw-open', 'triangle-sw-dot',
#                 'triangle-sw-open-dot', 'triangle-nw',
#                 'triangle-nw-open', 'triangle-nw-dot',
#                 'triangle-nw-open-dot', 'pentagon',
#                 'pentagon-open', 'pentagon-dot',
#                 'pentagon-open-dot', 'hexagon', 'hexagon-open',
#                 'hexagon-dot', 'hexagon-open-dot',
#                 'hexagon2', 'hexagon2-open', 'hexagon2-dot',
#                 'hexagon2-open-dot', 'octagon',
#                 'octagon-open', 'octagon-dot',
#                 'octagon-open-dot', 'star',  'star-open',
#                 'star-dot', 'star-open-dot', 'hexagram',
#                 'hexagram-open', 'hexagram-dot',
#                 'hexagram-open-dot', 'star-triangle-up',
#                 'star-triangle-up-open', 'star-triangle-up-dot',
#                 'star-triangle-up-open-dot', 'star-triangle-down',
#                 'star-triangle-down-open',
#                 'star-triangle-down-dot',
#                 'star-triangle-down-open-dot', 'star-square',
#                 'star-square-open','star-square-dot',
#                 'star-square-open-dot', 'star-diamond',
#                 'star-diamond-open', 'star-diamond-dot',
#                 'star-diamond-open-dot', 'diamond-tall',
#                 'diamond-tall-open', 'diamond-tall-dot',
#                 'diamond-tall-open-dot', 'diamond-wide',
#                 'diamond-wide-open', 'diamond-wide-dot',
#                 'diamond-wide-open-dot', 'hourglass',
#                 'hourglass-open', 'bowtie', 'bowtie-open',
#                 'circle-cross', 'circle-cross-open', 'circle-x',
#                 'circle-x-open', 'square-cross',
#                 'square-cross-open', 'square-x', 'square-x-open',
#                 'diamond-cross', 'diamond-cross-open',
#                 'diamond-x', 'diamond-x-open', 'cross-thin',
#                 'cross-thin-open', 'x-thin', 'x-thin-open',
#                 'asterisk', 'asterisk-open', 'hash',
#                 'hash-open', 'hash-dot', 'hash-open-dot',
#                 'y-up', 'y-up-open', 'y-down',
#                 'y-down-open', 'y-left', 'y-left-open',
#                 'y-right', 'y-right-open', 'line-ew',
#                 'line-ew-open', 'line-ns', 'line-ns-open',
#                 'line-ne', 'line-ne-open', 'line-nw',
#                 'line-nw-open']

ALL_SYMBOLS = [
    'circle', 'triangle-up', 'square', 'triangle-down', 'pentagon', 'diamond',
    'triangle-left', 'hexagon', 'cross', 'triangle-right', 'star', 'x',
    'hexagram', 'star-square', 'diamond-wide', 'square-cross', 'triangle-ne',
    'octagon', 'cross-thin', 'triangle-se', 'star-triangle-up', 'asterisk',
    'triangle-nw', 'diamond-tall', 'hash', 'triangle-sw', 'star-diamond',
    'hourglass', 'bowtie', 'circle-cross','circle-open', 'triangle-up-open',
    'square-open', 'triangle-down-open', 'pentagon-open', 'diamond-open',
    'triangle-left-open', 'hexagon-open', 'cross-open', 'triangle-right-open',
    'star-open', 'x-open', 'hexagram-open', 'star-square-open',
    'diamond-wide-open', 'square-cross-open', 'triangle-ne-open',
    'octagon-open', 'cross-thin-open', 'triangle-se-open',
    'star-triangle-up-open', 'asterisk-open', 'triangle-nw-open',
    'diamond-tall-open', 'hash-open', 'triangle-sw-open', 'star-diamond-open',
    'hourglass-open', 'bowtie-open', 'circle-cross-open', 'circle-dot',
    'triangle-up-dot', 'square-dot', 'triangle-down-dot', 'pentagon-dot',
    'diamond-dot', 'triangle-left-dot', 'hexagon-dot', 'cross-dot',
    'triangle-right-dot', 'star-dot', 'x-dot', 'hexagram-dot',
    'star-square-dot', 'diamond-wide-dot', 'square-cross-dot',
    'triangle-ne-dot', 'octagon-dot', 'cross-thin-dot', 'triangle-se-dot',
    'star-triangle-up-dot', 'asterisk-dot', 'triangle-nw-dot',
    'diamond-tall-dot', 'hash-dot', 'triangle-sw-dot', 'star-diamond-dot',
    'hourglass-dot', 'bowtie-dot', 'circle-cross-dot', 'circle-open-dot',
    'triangle-up-open-dot', 'square-open-dot', 'triangle-down-open-dot',
    'pentagon-open-dot', 'diamond-open-dot', 'triangle-left-open-dot',
    'hexagon-open-dot', 'cross-open-dot', 'triangle-right-open-dot',
    'star-open-dot', 'x-open-dot', 'hexagram-open-dot',
    'star-square-open-dot', 'diamond-wide-open-dot', 'square-cross-open-dot',
    'triangle-ne-open-dot', 'octagon-open-dot', 'cross-thin-open-dot',
    'triangle-se-open-dot', 'star-triangle-up-open-dot', 'asterisk-open-dot',
    'triangle-nw-open-dot', 'diamond-tall-open-dot', 'hash-open-dot',
    'triangle-sw-open-dot', 'star-diamond-open-dot', 'hourglass-open-dot',
    'bowtie-open-dot', 'circle-cross-open-dot',
]


# writing a factory may be peak Java poisoning but it might help with all these parameters
def generate(title_text, sorted_data, x_fn, y_fn, axis_text, colourby, hovertext_type, line_y=None):
    margin = go.layout.Margin(
                l=50,
                r=50,
                b=50,
                t=50,
                pad=4
            )
    if sorted_data.empty:
        return go.Figure(
        data = [go.Scattergl(
            x = None,
            y = None
        )],
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
    traces = []
    grouped_data = sorted_data.groupby(colourby) #TODO: is this inefficient?
    i = 0
    if hovertext_type == 'none':
        marker_mode = 'markers'
    else:
        marker_mode = 'markers+text'
    for name, data in grouped_data:
        if hovertext_type == 'sample':
            text_content = data['sample']
        elif hovertext_type == 'group-id':
            text_content = data['group id']
        else:
            text_content = None
    for name, data in grouped_data:
        graph = go.Scattergl(
            x = x_fn(data),
            y = y_fn(data),
            name = name,
            hovertext = text_content,
            mode = marker_mode,
            marker = {
                "symbol": ALL_SYMBOLS[i]
            }
        )
        if i == len(ALL_SYMBOLS)-1:
            i = 0
        else:
            i += 1
        traces.append(graph)
    if line_y != None:
        traces.append(go.Scattergl( # Cutoff line
            x=sorted_data['sample'],
            y=[line_y] * len(sorted_data),
            mode="lines",
            line={"width": 3, "color": "black", "dash": "dash"},
            name="Cutoff"
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

def get_shapes_for_values(shapeby: List[str]):
    shape_dict = {}
    for index, item in enumerate(shapeby):
        # loop back to beginning of symbols list if we run out of symbols
        if index >= len(ALL_SYMBOLS):
            index = index - len(ALL_SYMBOLS)
        shape_dict[item] = ALL_SYMBOLS[index]
    return shape_dict
