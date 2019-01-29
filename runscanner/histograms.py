import itertools
import json
import pandas
import dash
import dash_html_components as html
import dash_core_components as dcc
import dash.dependencies as dep


machines = {
    'HiSeq': {
        'name': ['D00353', 'D00331', 'D00355', 'D00343'],
    },
    'MiSeq': {
        'name': ['M00146', 'M00753'],
    },
    'NovaSeq': {
        'name': ['A00469'],
    }
}


machine_ids = list(
    itertools.chain.from_iterable(
        [l['name'] for l in machines.values()]
    )
)


def machines_to_dispaly(df: pandas.DataFrame) -> bool:
    right_model = all(
        df.loc[
            (df['level'] == 'flow_cell') &
            (df['key'] == 'sequencerName'),
            'value'
        ].isin(machine_ids)
    )

    completed = all(
        df.loc[
            df['key'] == 'healthType',
            'value'
        ] == 'Completed'
    )

    return right_model and completed


app = dash.Dash()
rs = pandas.read_csv('./data/runscanner.csv')
rs = rs.groupby('run_alias').filter(
    machines_to_dispaly
)


app.layout = html.Div([
    html.H1('Histograms'),
    html.Div([
        dcc.Dropdown(
            id='dropdown_machine_name',
            options=[{'label': k, 'value': k} for k in machines.keys()],
        ),
        dcc.Dropdown(
            id='dropdown_run_alias',
            options=[
                {'label': k, 'value': k} for k in rs['run_alias'].unique()
            ]
        ),
        # dcc.Dropdown(
        #     id='dropdown_machine_id',
        #     options=[{'label': k, 'value': k} for k in machine_ids],
        # ),
    ]),

    dcc.Graph(
        id='clusters_pf_hist',
    ),

    html.Pre(id='click-data', style={
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }),

    html.Div(id='filtered_df', style={'display': 'none'}),
    html.Div(id='select_clicked', style={'display': 'none'}),
])


@app.callback(
    dep.Output('dropdown_run_alias', 'options'),
    [dep.Input('dropdown_machine_name', 'value')]
)
def update_run_alias_dropdown(machine_name):
    if machine_name is None:
        return [
            {'label': k, 'value': k} for k in rs['run_alias'].unique()
        ]
    else:
        machine_id = machines[machine_name]['name']

        clust = rs.groupby('run_alias').filter(
            lambda x: any(
                x.loc[x['key'] == 'sequencerName', 'value'].isin(machine_id)
            )
        )

        return [
            {'label': k, 'value': k} for k in clust['run_alias'].unique()
        ]


@app.callback(
    dep.Output('filtered_df', 'children'),
    [dep.Input('dropdown_machine_name', 'value')]
)
def update_hidden_df_div(machine_name):
    df = rs.copy()

    if machine_name is not None:
        machine_id = machines[machine_name]['name']

        df = df.groupby('run_alias').filter(
            lambda x: any(
                x.loc[x['key'] == 'sequencerName', 'value'].isin(machine_id)
            )
        )

    return df.to_json()


@app.callback(
    dep.Output('clusters_pf_hist', 'figure'),
    [dep.Input('filtered_df', 'children')]
)
def update_clusters_pf(json_str):
    df = pandas.read_json(json_str)

    clust = df.loc[
        (rs['level'] == 'flow_cell') &
        (rs['key'] == 'Clusters PF'),
        'value'
    ].astype('int')

    return {'data': [
        {'x': clust, 'type': 'histogram'}
    ]}


@app.callback(
    dep.Output('click-data', 'children'),
    [dep.Input('select_clicked', 'children'),
     dep.Input('filtered_df', 'children')]
)
def display_hist_click(clicked, json_str):
    clickData = json.loads(clicked)

    if clickData is None:
        return None

    run_inx = clickData['points'][0]['pointNumbers']
    df = pandas.read_json(json_str)

    run_alias = df.loc[
        (df['level'] == 'flow_cell') &
        (df['key'] == 'Clusters PF'),
        'run_alias'
    ]

    run_alias = run_alias.reset_index(drop=True)

    return json.dumps(list(run_alias[run_inx]), indent=2)


@app.callback(
    dep.Output('select_clicked', 'children'),
    [dep.Input('clusters_pf_hist', 'clickData')]
)
def store_click(clickData):
    return json.dumps(clickData)


if __name__ == '__main__':
    app.run_server(debug=True)
