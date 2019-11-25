import pandas
import plotly.graph_objects as go

# TODO: if this remains necessary i'll be mad. Can we get it from plotly itself?
ALL_SYMBOLS = ['circle', 'circle-open', 'circle-dot',
                'circle-open-dot', 'square', 'square-open', 
                'square-dot', 'square-open-dot', 'diamond',
                'diamond-open', 'diamond-dot',
                'diamond-open-dot', 'cross', 'cross-open',
                'cross-dot', 'cross-open-dot', 'x', 'x-open',
                'x-dot', 'x-open-dot', 'triangle-up',
                'triangle-up-open', 'triangle-up-dot',
                'triangle-up-open-dot', 'triangle-down',
                'triangle-down-open', 'triangle-down-dot',
                'triangle-down-open-dot', 'triangle-left',
                'triangle-left-open', 'triangle-left-dot',
                'triangle-left-open-dot', 'triangle-right',
                'triangle-right-open', 'triangle-right-dot',
                'triangle-right-open-dot', 'triangle-ne', 
                'triangle-ne-open', 'triangle-ne-dot',
                'triangle-ne-open-dot', 'triangle-se',
                'triangle-se-open', 'triangle-se-dot',
                'triangle-se-open-dot', 'triangle-sw',
                'triangle-sw-open', 'triangle-sw-dot',
                'triangle-sw-open-dot', 'triangle-nw',
                'triangle-nw-open', 'triangle-nw-dot',
                'triangle-nw-open-dot', 'pentagon', 
                'pentagon-open', 'pentagon-dot',
                'pentagon-open-dot', 'hexagon', 'hexagon-open',
                'hexagon-dot', 'hexagon-open-dot',
                'hexagon2', 'hexagon2-open', 'hexagon2-dot',
                'hexagon2-open-dot', 'octagon', 
                'octagon-open', 'octagon-dot', 
                'octagon-open-dot', 'star',  'star-open',
                'star-dot', 'star-open-dot', 'hexagram',
                'hexagram-open', 'hexagram-dot',
                'hexagram-open-dot', 'star-triangle-up', 
                'star-triangle-up-open', 'star-triangle-up-dot',
                'star-triangle-up-open-dot', 'star-triangle-down',
                'star-triangle-down-open',
                'star-triangle-down-dot',
                'star-triangle-down-open-dot', 'star-square', 
                'star-square-open','star-square-dot',
                'star-square-open-dot', 'star-diamond', 
                'star-diamond-open', 'star-diamond-dot',
                'star-diamond-open-dot', 'diamond-tall',
                'diamond-tall-open', 'diamond-tall-dot',
                'diamond-tall-open-dot', 'diamond-wide', 
                'diamond-wide-open', 'diamond-wide-dot',
                'diamond-wide-open-dot', 'hourglass', 
                'hourglass-open', 'bowtie', 'bowtie-open',
                'circle-cross', 'circle-cross-open', 'circle-x',
                'circle-x-open', 'square-cross', 
                'square-cross-open', 'square-x', 'square-x-open',
                'diamond-cross', 'diamond-cross-open', 
                'diamond-x', 'diamond-x-open', 'cross-thin', 
                'cross-thin-open', 'x-thin', 'x-thin-open', 
                'asterisk', 'asterisk-open', 'hash', 
                'hash-open', 'hash-dot', 'hash-open-dot', 
                'y-up', 'y-up-open', 'y-down', 
                'y-down-open', 'y-left', 'y-left-open',
                'y-right', 'y-right-open', 'line-ew', 
                'line-ew-open', 'line-ns', 'line-ns-open',
                'line-ne', 'line-ne-open', 'line-nw', 
                'line-nw-open']


# writing a factory may be peak Java poisoning but it might help with all these parameters
def generate(title_text, sorted_data, x_fn, y_fn, axis_text, colourby, hovertext_type, line_y=None):
    if sorted_data.empty:
        return go.Figure(
        data = [go.Scattergl(
            x = None,
            y = None
        )],
        layout = go.Layout(
            title=title_text, 
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
