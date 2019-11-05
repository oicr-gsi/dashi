import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids
import dash_table
import pandas
import plotly.graph_objects as go
import gsiqcetl.load
from gsiqcetl.runscanner.illumina.constants import FlowCellCacheSchema
from gsiqcetl.pinery.instruments.constants import CacheSchema

page_name = 'runscanner/sum_over_time'

ids = init_ids([
    'freq_dropdown',
    'colour_by_dropdown',
    'bar_sum',
    'table_tabs',
    'table_tabs_content',
    'raw_df_json',
    'df_group_sum'
])

rs_flow = gsiqcetl.load.runscanner_illumina_flowcell(FlowCellCacheSchema.v1)
rs_flow_col = gsiqcetl.load.runscanner_illumina_flowcell_columns(
    FlowCellCacheSchema.v1
)

COL_TOTAL_YIELD = "Total Yield (GB)"

rs_flow[COL_TOTAL_YIELD] = rs_flow[
    [
        rs_flow_col.YieldRead1,
        rs_flow_col.YieldRead2,
        rs_flow_col.YieldIndex1,
        rs_flow_col.YieldIndex2,
    ]
].sum(axis=1)

rs_flow = rs_flow[
    [
        rs_flow_col.SequencerName,
        rs_flow_col.StartDate,
        rs_flow_col.HealthType,
        COL_TOTAL_YIELD,
    ]
]

inst_raw = gsiqcetl.load.pinery_instruments(CacheSchema.v1)
inst_col = gsiqcetl.load.pinery_instruments_columns(CacheSchema.v1)

inst_model = inst_raw[[inst_col.InstrumentName, inst_col.ModelName]]

rs_flow = rs_flow.merge(
    inst_model,
    "left",
    left_on=rs_flow_col.SequencerName,
    right_on=inst_col.InstrumentName,
)

raw_df = rs_flow[rs_flow[rs_flow_col.HealthType] == "COMPLETED"]

raw_df_table_col_names = [{"name": i, "id": i} for i in raw_df.columns]

layout = html.Div(
    [
        core.Dropdown(
            id="freq_dropdown",
            options=[
                {"label": "Daily", "value": "D"},
                {"label": "Weekly", "value": "W"},
                {"label": "Monthly", "value": "M"},
                {"label": "Quarterly", "value": "BQ-MAR"},
                {"label": "Yearly", "value": "Y"},
            ],
            value="M",
            clearable=False,
        ),
        core.Dropdown(
            id="colour_by_dropdown",
            options=[
                {"label": "Machine ID", "value": inst_col.InstrumentName},
                {"label": "Machine Model", "value": inst_col.ModelName},
            ],
            value=None,
            placeholder="Colour By",
        ),
        core.Graph(id="bar_sum"),
        core.Tabs(
            id="table_tabs",
            value="grouped",
            children=[
                core.Tab(label="Grouped Data", value="grouped"),
                core.Tab(label="All Data", value="all"),
            ],
        ),
        html.Div(id="table_tabs_content"),
        html.Div(
            id="raw_df_json",
            style={"display": "none"},
            children=raw_df.to_json(date_format="iso", orient="records"),
        ),
        html.Div(id="df_group_sum", style={"display": "none"}),
    ]
) 

def init_callbacks(dash_app):
    @dash_app.callback(
        Output(ids['bar_sum'], "figure"),
        [Input(ids['df_group_sum'], "children"), 
        Input(ids['colour_by_dropdown'], "value")])
    def create_bar_sum_fig(df_group_sum, colour_by):
        df = pandas.read_json(df_group_sum, orient="split")

        layout = {
            "yaxis": {"title": "PF Yield (GB)"},
            "legend": {"orientation": "h"},
        }

        if colour_by is None:
            return {
                "data": [
                    go.Bar(x=df[rs_flow_col.StartDate], y=df[COL_TOTAL_YIELD])
                ],
                "layout": layout,
            }
        else:
            traces = []
            for name, data in df.groupby(colour_by):
                t = go.Bar(
                    x=list(data[rs_flow_col.StartDate]),
                    y=list(data[COL_TOTAL_YIELD]),
                    name=name,
                )
                traces.append(t)

            return {"data": traces, "layout": layout}


    @dash_app.callback(
        Output(ids['table_tabs_content'], "children"),
        [Input(ids['table_tabs'], "value"),
        Input(ids['raw_df_json'], "children"),
        Input(ids['df_group_sum'], "children")])
    def update_table_tab(selected_tab, raw_df_json, group_df_json):
        if selected_tab == "grouped":
            df = pandas.read_json(group_df_json, orient="split")
        if selected_tab == "all":
            df = pandas.read_json(raw_df_json, orient="records")

        col_names = [{"name": i, "id": i} for i in df.columns]

        return dash_table.DataTable(
            id="test", columns=col_names, data=df.to_dict("rows")
        )


    @dash_app.callback(
        Output(ids['df_group_sum'], "children"),
        [Input(ids['raw_df_json'], "children"),
        Input(ids['freq_dropdown'], "value"),
        Input(ids['colour_by_dropdown'], "value")])
    def update_grouped_df(raw_df_json, frequency, colour_grouper):
        raw = pandas.read_json(
            raw_df_json, orient="records", convert_dates=[rs_flow_col.StartDate]
        )

        if colour_grouper is None:
            grouper = [pandas.Grouper(key=rs_flow_col.StartDate, freq=frequency)]
        else:
            grouper = [
                pandas.Grouper(key=rs_flow_col.StartDate, freq=frequency),
                colour_grouper,
            ]

        return (
            raw.groupby(grouper)
            .sum()
            .reset_index()
            .to_json(date_format="iso", orient="split")
        )