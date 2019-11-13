import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from ..dash_id import init_ids
import pandas as pd
import plotly.graph_objects as go
import gsiqcetl.load
from gsiqcetl.bamqc.constants import CacheSchema
from flask import current_app as app

page_name = "bamqc/gbovertime"

ids = init_ids(["lib", "month_plot", "3month_plot", "cum_plot"])

bamqc = gsiqcetl.load.bamqc(CacheSchema.v1)
col = gsiqcetl.load.bamqc_columns(CacheSchema.v1)

COL_TOTAL_BASES = "total bases"
COL_RUN_DATE = "run date"

bamqc[COL_TOTAL_BASES] = bamqc[col.TotalReads] * bamqc[col.AverageReadLength]
bamqc[COL_RUN_DATE] = pd.to_datetime(bamqc[col.Run].str[0:6], format="%y%m%d")

bamqc_lib = [{"label": x, "value": x} for x in bamqc[col.SequencingType].unique()]
bamqc_lib.append({"label": "All", "value": "All"})

layout = html.Div(
    [
        core.Dropdown(id=ids["lib"], options=bamqc_lib, value="All"),
        core.Graph(id=ids["month_plot"]),
        core.Graph(id=ids["3month_plot"]),
        core.Graph(id=ids["cum_plot"]),
    ]
)


def init_callbacks(dash_app):
    @dash_app.callback(
        Output(ids["month_plot"], "figure"), [Input(ids["lib"], "value")]
    )
    @dash_app.server.cache.memoize(timeout=60)
    def update_per_month(seq_type):
        subset = filter_df(seq_type)

        month_sum = subset.resample("MS", on=COL_RUN_DATE).sum()
        trace = [go.Bar(x=month_sum.index, y=month_sum[COL_TOTAL_BASES] / 1e9)]
        return {
            "data": trace,
            "layout": go.Layout(title="GB per month", yaxis=dict(title="Gigabases")),
        }

    @dash_app.callback(
        Output(ids["3month_plot"], "figure"), [Input(ids["lib"], "value")]
    )
    @dash_app.server.cache.memoize(timeout=60)
    def update_per_3month(seq_type):
        subset = filter_df(seq_type)
        month_sum = subset.resample("3MS", on=COL_RUN_DATE).sum()
        trace = [go.Bar(x=month_sum.index, y=month_sum[COL_TOTAL_BASES] / 1e9)]
        return {
            "data": trace,
            "layout": go.Layout(title="GB per 3 months", yaxis=dict(title="Gigabases")),
        }

    @dash_app.callback(Output(ids["cum_plot"], "figure"), [Input(ids["lib"], "value")])
    @dash_app.server.cache.memoize(timeout=60)
    def update_cumulative(seq_type):
        subset = filter_df(seq_type)
        month_sum = subset.resample("MS", on=COL_RUN_DATE).sum()
        month_cumsum = month_sum.cumsum()

        trace = [
            go.Scatter(x=month_cumsum.index, y=month_cumsum[COL_TOTAL_BASES] / 1e9)
        ]

        return {
            "data": trace,
            "layout": go.Layout(
                title="Cumulative GB per month", yaxis=dict(title="Gigabases")
            ),
        }


@app.cache.memoize(timeout=60)
def filter_df(seq_type):
    if seq_type == "All":
        return bamqc
    else:
        return bamqc.loc[bamqc[col.SequencingType] == seq_type]
