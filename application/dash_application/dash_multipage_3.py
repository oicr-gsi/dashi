import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objects as go
from .dash_id import init_ids
from flask_caching import Cache

df = pd.read_csv(
    'https://raw.githubusercontent.com/plotly/'
    'datasets/master/gapminderDataFiveYear.csv')

page_name = 'complex-page'

ids = init_ids(['myGraph', 'year-slider', 'url'])

layout = html.Div([
    core.Location(id=ids['url'], refresh=False),
    core.Graph(id=ids['myGraph']),
    core.Slider(
        id=ids['year-slider'],
        min=df['year'].min(),
        max=df['year'].max(),
        value=df['year'].min(),
        marks={str(year): str(year) for year in df['year'].unique()},
        step=None
    )
])

def init_callbacks(dash_app):
    @dash_app.callback(
        Output(ids['url'], 'hash'),
        [Input(ids['year-slider'], 'value')]
    )
    @dash_app.server.cache.memoize(timeout=60)
    def onSlide(value):
        return '#'+str(value)

    @dash_app.callback(
        Output(ids['myGraph'], 'figure'),
        [Input(ids['url'], 'hash')])
    @dash_app.server.cache.memoize(timeout=60)
    def update_figure(selected_year):
        selected_year = int(selected_year[1:])
        filtered_df = df[df.year == selected_year]
        traces = []
        for i in filtered_df.continent.unique():
            df_by_continent = filtered_df[filtered_df['continent'] == i]
            traces.append(go.Scattergl(
                x=df_by_continent['gdpPercap'],
                y=df_by_continent['lifeExp'],
                text=df_by_continent['country'],
                mode='markers',
                opacity=0.7,
                marker={
                    'size': 15,
                    'line': {'width': 0.5, 'color': 'white'}
                },
                name=i
            ))
    
        return {
            'data': traces,
            'layout': go.Layout(
                xaxis={'type': 'log', 'title': 'GDP Per Capita'},
                yaxis={'title': 'Life Expectancy', 'range': [20, 90]},
                margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                legend={'x': 0, 'y': 1},
                hovermode='closest'
            )
        }

