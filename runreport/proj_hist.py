import json
import pandas
import numpy
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import plotly.figure_factory as ff


idx = pandas.IndexSlice

rr = pandas.read_hdf('./data/run_report_cache.hd5')
rr['Project'] = rr['Library'].apply(lambda x: x.split('_', 1)[0])
rr.set_index(['Project', 'Run'], inplace=True)
rr.sort_values(['Run', 'Project'], ascending=False, inplace=True)

proj_list = list(rr.index.get_level_values('Project').unique())
proj_top = proj_list[0]
proj_list.sort()

run_list = list(
    rr.loc[idx[proj_top, :], :].index.get_level_values('Run').unique()
)

layout = html.Div([
    dcc.Dropdown(
        id='project',
        options=[
            {'label': v, 'value': v} for v in proj_list
        ],
        value=proj_top,
        clearable=False,
    ),
    dcc.Dropdown(
        id='focused_run',
        clearable=False,
    ),
    # dcc.Graph(
    #     id='coverage_hist'
    # ),
    dcc.Graph(
        id='coverage_dist'
    ),
    html.Pre(id='click-data'),
])


try:
    from app import app
except ModuleNotFoundError:
    import dash
    app = dash.Dash(__name__)
    app.layout = layout


# When a project is selected
# Show only runs where the project is found
@app.callback(
    Output('focused_run', 'options'),
    [Input('project', 'value')]
)
def set_focused_run_based_on_project(project):
    runs = rr.loc[idx[project, :], :].index.get_level_values(
        'Run'
    ).unique()

    return [{'label': v, 'value': v} for v in runs]


# When a project is selected
# Set the newest run as the default selection
@app.callback(
    Output('focused_run', 'value'),
    [Input('project', 'value')]
)
def set_focused_run_default_value_when_options_change(project):
    runs = rr.loc[idx[project, :], :].index.get_level_values(
        'Run'
    ).unique()

    return list(runs)[0]


@app.callback(
    Output('coverage_dist', 'figure'),
    [Input('project', 'value'), Input('focused_run', 'value')]
)
def create_coverage_dist(project, run_to_focus):
    highlight = (
        rr.loc[idx[project, run_to_focus], 'Coverage (collapsed)']
    )

    other_runs = rr.index.get_level_values(
        'Run'
    ).difference(
        highlight.index.get_level_values('Run')
    )

    other_runs_data = rr.loc[idx[project, other_runs], 'Coverage (collapsed)']

    if len(other_runs_data.unique()) < 2:
        return []

    try:
        if len(other_runs_data) > 0:
            return ff.create_distplot(
                [list(highlight), list(other_runs_data)],
                ['Selected Run', 'All Other Runs'],
            )
        else:
            return ff.create_distplot(
                [list(highlight)],
                ['Selected Run'],
            )
    # Thrown if all data points have the same value
    except numpy.linalg.linalg.LinAlgError:
        return ff.create_distplot(
            [list(other_runs_data)],
            ['All Other Run'],
        )
    # If data set only has one value
    except ValueError:
        return ff.create_distplot(
            [list(other_runs_data)],
            ['All Other Run'],
        )


@app.callback(
    Output('click-data', 'children'),
    [Input('coverage_dist', 'clickData')])
def display_click_data(clickData):
    return json.dumps(clickData, indent=2)


if __name__ == '__main__':
    app.run_server(debug=True)
