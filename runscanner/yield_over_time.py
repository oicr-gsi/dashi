import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas
import plotly.graph_objs as go


def load_df_as_json():
    idx = pandas.IndexSlice

    rs_raw = pandas.read_hdf('./data/runscanner_illumina_cache.hd5')
    inst_raw = pandas.read_hdf('./data/pinery_instruments_cache.hd5')

    rs_flow = rs_raw.loc[idx[:, 'flow_cell', :, :], 'value'].unstack('key')
    rs_flow = rs_flow[['sequencerName', 'startDate', 'healthType']]
    rs_flow = rs_flow.reset_index()

    inst_model = inst_raw[['name_instrument', 'name_model']]

    rs_flow = rs_flow.merge(
        inst_model, 'left', left_on='sequencerName', right_on='name_instrument'
    )

    rs_lane = rs_raw.loc[
        idx[:, ['Read', 'Index'], :, :], 'value'
    ].unstack('key')
    rs_lane_yield = rs_lane.groupby('run_alias')[['Yield']].sum()
    rs_lane_yield = rs_lane_yield.rename(columns={'Yield': 'Total Yield (GB)'})

    final = rs_flow.merge(rs_lane_yield, on='run_alias', right_index=True)
    final = final[final['healthType'] == 'COMPLETED']
    final = final.astype({'startDate': 'datetime64[ns]'})

    return final


raw_df = load_df_as_json()
raw_df_table_col_names = [
    {'name': i, 'id': i} for i in raw_df.columns
]

layout = html.Div([
    dcc.Dropdown(
        id='freq_dropdown',
        options=[
            {'label': 'Daily', 'value': 'D'},
            {'label': 'Weekly', 'value': 'W'},
            {'label': 'Monthly', 'value': 'M'},
            {'label': 'Quarterly', 'value': 'BQ-MAR'},
            {'label': 'Yearly', 'value': 'Y'},
        ],
        value='M',
        clearable=False,
    ),

    dcc.Dropdown(
        id='colour_by_dropdown',
        options=[
            {'label': 'Machine ID', 'value': 'sequencerName'},
            {'label': 'Machine Model', 'value': 'name_model'},
        ],
        value=None,
        placeholder='Colour By'
    ),

    dcc.Graph(
        id='bar_sum',
    ),

    dcc.Tabs(id="table_tabs", value='grouped', children=[
        dcc.Tab(label='Grouped Data', value='grouped'),
        dcc.Tab(label='All Data', value='all'),
    ]),

    html.Div(
        id='table_tabs_content'
    ),

    html.Div(
        id='raw_df_json',
        style={'display': 'none'},
        children=raw_df.to_json(
            date_format='iso', orient='records'
        ),
    ),

    html.Div(
        id='df_group_sum',
        style={'display': 'none'},
    ),
])

try:
    from app import app
    app.layout = layout
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)
    app.layout = layout


@app.callback(
    Output('bar_sum', 'figure'),
    [Input('df_group_sum', 'children'),
     Input('colour_by_dropdown', 'value')]
)
def create_bar_sum_fig(df_group_sum, colour_by):
    df = pandas.read_json(df_group_sum, orient='split')

    layout = {
        'yaxis': {'title': 'PF Yield (GB)'},
        'legend': {'orientation': 'h'},
    }

    if colour_by is None:
        return {
            'data': [go.Bar(
                x=df['startDate'],
                y=df['Total Yield (GB)']
            )],
            'layout': layout,
        }
    else:
        traces = []
        for name, data in df.groupby(colour_by):
            t = go.Bar(
                x=list(data['startDate']),
                y=list(data['Total Yield (GB)']),
                name=name
            )
            traces.append(t)

        return {
            'data': traces,
            'layout': layout
        }


@app.callback(
    Output('table_tabs_content', 'children'),
    [Input('table_tabs', 'value'),
     Input('raw_df_json', 'children'),
     Input('df_group_sum', 'children')]
)
def update_table_tab(selected_tab, raw_df_json, group_df_json):
    if selected_tab == 'grouped':
        df = pandas.read_json(group_df_json, orient='split')
    if selected_tab == 'all':
        df = pandas.read_json(raw_df_json, orient='records')

    col_names = [{'name': i, 'id': i} for i in df.columns]

    return dash_table.DataTable(
        id='test',
        columns=col_names,
        data=df.to_dict('rows')
    )


@app.callback(
    Output('df_group_sum', 'children'),
    [Input('raw_df_json', 'children'),
     Input('freq_dropdown', 'value'),
     Input('colour_by_dropdown', 'value')]
)
def update_grouped_df(raw_df_json, frequency, colour_grouper):
    raw = pandas.read_json(
        raw_df_json, orient='records', convert_dates=['startDate']
    )

    if colour_grouper is None:
        grouper = [
            pandas.Grouper(key='startDate', freq=frequency)
        ]
    else:
        grouper = [
            pandas.Grouper(key='startDate', freq=frequency),
            colour_grouper
        ]

    return raw.groupby(
        grouper
    ).sum().reset_index().to_json(
        date_format='iso', orient='split',
    )


if __name__ == '__main__':
    app.run_server(debug=True)
