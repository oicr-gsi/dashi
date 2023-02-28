from dash import html
from dash import dcc as core
from dash.dependencies import Input, Output
from ..dash_id import init_ids
import json
import pandas
import numpy
import plotly.figure_factory as ff

import gsiqcetl.load
from gsiqcetl.runreport.constants import CacheSchema

page_name = "runreport/proj_hist"

ids = init_ids([
    "project",
    "focused_run",
    "coverage_dist",
    "click-data"
])

idx = pandas.IndexSlice

rr = gsiqcetl.load.runreport(CacheSchema.v1)
rr_col = gsiqcetl.load.runreport_columns(CacheSchema.v1)

COL_PROJECT = "Project"

rr[COL_PROJECT] = rr[rr_col.Library].apply(lambda x: x.split("_", 1)[0])
rr.set_index([COL_PROJECT, rr_col.Run], inplace=True)
rr.sort_values([rr_col.Run, COL_PROJECT], ascending=False, inplace=True)

# Count how many runs per project
runs_per_proj_count = rr.reset_index().groupby(COL_PROJECT)[rr_col.Run].nunique()
proj_with_multi_run = runs_per_proj_count[runs_per_proj_count > 1].index
# Only display project that have more than one run
rr = rr.loc[idx[proj_with_multi_run, :], :]

rr = rr.groupby([COL_PROJECT, rr_col.Run]).filter(lambda x: len(x) > 1)

proj_list = list(rr.index.get_level_values(COL_PROJECT).unique())
proj_top = proj_list[0]
proj_list.sort()

run_list = list(rr.loc[idx[proj_top, :], :].index.get_level_values(rr_col.Run).unique())

layout = html.Div(
    [
        core.Dropdown(
            id=ids["project"],
            options=[{"label": v, "value": v} for v in proj_list],
            value=proj_top,
            clearable=False,
        ),
        core.Dropdown(id=ids["focused_run"], clearable=False),
        # core.Graph(
        #     id='coverage_hist'
        # ),
        core.Graph(id=ids["coverage_dist"]),
        html.Pre(id=ids["click-data"]),
    ]
)


def init_callbacks(dash_app):
    # When a project is selected,
    # show only runs where the project is found
    @dash_app.callback(
        Output(ids["focused_run"], "options"),
        [
            Input(ids["project"], "value")
        ]
    )
    @dash_app.server.cache.memoize(timeout=60)
    def set_focused_run_based_on_project(project):
        runs = rr.loc[idx[project, :], :].index.get_level_values(rr_col.Run).unique()

        return [{"label": v, "value": v} for v in runs]

    # When a project is selected
    # Set the newest run as the default selection
    @dash_app.callback(
        Output(ids["focused_run"], "value"),
        [
            Input(ids["project"], "value")
        ]
    )
    def set_focused_run_default_value_when_options_change(project):
        runs = rr.loc[idx[project, :], :].index.get_level_values("Run").unique()

        return list(runs)[0]

    @dash_app.callback(
        Output(ids["coverage_dist"], "figure"),
        [
            Input(ids["project"], "value"),
            Input(ids["focused_run"], "value")
        ],
    )
    @dash_app.server.cache.memoize(timeout=60)
    def create_coverage_dist(project, run_to_focus):
        highlight = rr.loc[idx[project, run_to_focus], rr_col.Coverage]

        other_runs = rr.index.get_level_values(rr_col.Run).difference(
            highlight.index.get_level_values(rr_col.Run)
        )

        other_runs_data = rr.loc[idx[project, other_runs], rr_col.Coverage]

        if len(other_runs_data.unique()) < 2:
            return []

        try:
            if len(other_runs_data) > 0:
                return ff.create_distplot(
                    [list(highlight), list(other_runs_data)],
                    ["Selected Run", "All Other Runs"],
                )
            else:
                return ff.create_distplot([list(highlight)], ["Selected Run"])
        # Thrown if all data points have the same value
        except numpy.linalg.linalg.LinAlgError:
            return ff.create_distplot([list(other_runs_data)], ["All Other Run"])
        # If data set only has one value
        except ValueError:
            return ff.create_distplot([list(other_runs_data)], ["All Other Run"])

    @dash_app.callback(
        Output(ids["click-data"], "children"),
        [
            Input(ids["coverage_dist"], "clickData")
        ],
    )
    @dash_app.server.cache.memoize(timeout=60)
    def display_click_data(clickData):
        return json.dumps(clickData, indent=2)
