import pandas as pd
import dash_html_components as html
import dash_core_components as dcc
import dash.dependencies as dep
import plotly.graph_objs as go

import gsiqcetl.bamqc.cache


bamqc = gsiqcetl.bamqc.cache.load_cache("v1", "./data/bamqc_cache.hd5")
col = gsiqcetl.bamqc.cache.get_column_names("v1")

bamqc["total bases"] = bamqc[col.TotalReads] * bamqc[col.AverageReadLength]
bamqc["run date"] = pd.to_datetime(bamqc[col.Run].str[0:6], format="%y%m%d")

bamqc_lib = [
    {"label": x, "value": x} for x in bamqc[col.SequencingType].unique()
]
bamqc_lib.append({"label": "All", "value": "All"})

layout = html.Div(
    [
        dcc.Dropdown(id="lib", options=bamqc_lib, value="All"),
        dcc.Graph(id="month_plot"),
        dcc.Graph(id="3month_plot"),
        dcc.Graph(id="cum_plot"),
    ]
)

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout


def filter_df(seq_type):
    if seq_type == "All":
        return bamqc
    else:
        return bamqc.loc[bamqc[col.SequencingType] == seq_type]


@app.callback(dep.Output("month_plot", "figure"), [dep.Input("lib", "value")])
def update_per_month(seq_type):
    subset = filter_df(seq_type)

    month_sum = subset.resample("MS", on="run date").sum()
    trace = [go.Bar(x=month_sum.index, y=month_sum["total bases"] / 1e9)]
    return {
        "data": trace,
        "layout": go.Layout(
            title="GB per month", yaxis=dict(title="Gigabases")
        ),
    }


@app.callback(dep.Output("3month_plot", "figure"), [dep.Input("lib", "value")])
def update_per_3month(seq_type):
    subset = filter_df(seq_type)
    month_sum = subset.resample("3MS", on="run date").sum()
    trace = [go.Bar(x=month_sum.index, y=month_sum["total bases"] / 1e9)]
    return {
        "data": trace,
        "layout": go.Layout(
            title="GB per 3 months", yaxis=dict(title="Gigabases")
        ),
    }


@app.callback(dep.Output("cum_plot", "figure"), [dep.Input("lib", "value")])
def update_cumulative(seq_type):
    subset = filter_df(seq_type)
    month_sum = subset.resample("MS", on="run date").sum()
    month_cumsum = month_sum.cumsum()

    trace = [
        go.Scatter(x=month_cumsum.index, y=month_cumsum["total bases"] / 1e9)
    ]

    return {
        "data": trace,
        "layout": go.Layout(
            title="Cumulative GB per month", yaxis=dict(title="Gigabases")
        ),
    }


if __name__ == "__main__":
    app.run_server(debug=True)
