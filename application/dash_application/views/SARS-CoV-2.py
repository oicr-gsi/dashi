from collections import defaultdict

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output, State
from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs, cutoff_table_data_ius
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from gsiqcetl.column import BamQc3Column
import pinery
import logging

logger = logging.getLogger(__name__)

page_name = 'SARS-CoV-2'
title = "SARS-CoV-2"

ids = init_ids([
    # Buttons
    'jira-issue-with-runs-button',
    'general-jira-issue-button',
    'update-button-top',
    'update-button-bottom',
    'approve-run-button',

    # Sidebar controls
    'all-runs',
    'run-id-list',
    'all-instruments',
    'instruments-list',
    'all-projects',
    'projects-list',
    "all-references",
    "references-list",
    'all-kits',
    'kits-list',
    'all-library-designs',
    'library-designs-list',
    'all-templates',
    'templates-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'show-data-labels',
    'show-all-data-labels',
    'date-range',

    #Graphs
    'on-target-reads-various-bar',
    'average-coverage-scatter',
    'on-target-reads-sars-cov-2-scatter',
    'coverage-percentiles-line',
    'coverage-uniformity-scatter',

    #Potential Graphs
    'base-by-base-line',
    'coverage-number-by-amplicon',
    'base-by-base-coverage-genome', #TODO: Graph type?
    'variants-observed', #TODO: Graph Type?
    #Data table
    'failed-samples',
    'data-table'
])



# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
    "references": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_REFERENCES, "all_references"),
}



def generate_on_target_reads_bar(current_data, graph_params):
    return generate_bar(
        current_data,
        #TODO: get all genomes,
        lambda d: d[PINERY_COL.SampleName], #TODO is that right? jira says 'reads'
        lambda d, col: , # TODO f'n
        "On-Target (%)",
        "%"
    )


def generate_average_coverage_scatter(current_data, graph_params):
    return generate(
        "Average Coverage",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[], #TODO: column
        "", #TODO: Units
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )

def generate_on_target_reads_scatter(current_data, graph_params):
    return generate(
        "On Target Reads, SARS-CoV-2 (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[], #TODO: column
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )

def generate_coverage_percentiles_line(current_data, graph_params):
    #TODO: line chart needs multiple values per sample, figure that out

    return generate(
    "Coverage Percentile",
    current_data,
    lambda d: d[PINERY_COL.SampleName],
    lambda d: d[], #TODO: column
    "n% of Genome covered",
    graph_params["colour_by"],
    graph_params["shape_by"],
    graph_params["shownames_val"],
    markermode="lines+markers"
)

def generate_coverage_uniformity_scatter(current_data, graph_params):
    return generate(
        "Uniformity of Coverage",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[], #TODO: column
        "", #TODO: Units
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )

def dataversion():
    return DATAVERSION


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # intial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown

    df = reshape_single_lane_df(bamqc, initial["runs"], initial["instruments"],
                                initial["projects"], initial["references"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className='body', children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("File a ticket",
                                          ids['general-jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title)),
                sidebar_utils.jira_button("File a ticket about these runs",
                                          ids['jira-issue-with-runs-button'],
                                          {"display": "none"}, "")]),
            html.Div(className='row flex-container', children=[
                html.Div(className='sidebar four columns', children=[
                    html.Button('Update', id=ids['update-button-top'], className="update-button"),
                    sidebar_utils.approve_run_button(ids['approve-run-button']),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_runs(ids["all-runs"],
                                            ids["run-id-list"], ALL_RUNS,
                                            query["req_runs"]),

                    sidebar_utils.run_range_input(ids["date-range"],
                                               query["req_start"],
                                                query["req_end"]),

                    sidebar_utils.hr(),

                    sidebar_utils.select_projects(ids["all-projects"],
                                                ids["projects-list"],
                                                ALL_PROJECTS),

                    sidebar_utils.select_reference(ids["all-references"],
                                                   ids["references-list"],
                                                   ALL_REFERENCES),

                    sidebar_utils.select_kits(ids["all-kits"], ids["kits-list"],
                                            ALL_KITS),

                    sidebar_utils.select_instruments(ids["all-instruments"],
                                                    ids["instruments-list"],
                                                    ILLUMINA_INSTRUMENT_MODELS),

                    sidebar_utils.select_library_designs(
                        ids["all-library-designs"], ids["library-designs-list"],
                        ALL_LIBRARY_DESIGNS),

                    sidebar_utils.select_with_select_all(
                        "All Templates", 
                        ids['all-templates'], 
                        "Filter by Template", 
                        ids['templates-list'], 
                        ALL_TEMPLATES
                    ),

                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(ids['first-sort'],
                                                    initial["first_sort"]),

                    sidebar_utils.select_second_sort(
                        ids['second-sort'],
                        initial["second_sort"],
                        [
                                {"label": "Total Reads",
                                "value": BAMQC_COL.TotalReads},
                                {"label": "Unmapped Reads",
                                "value": BAMQC_COL.UnmappedReads},
                                {"label": "Non-primary Reads",
                                "value": BAMQC_COL.NonPrimaryReads},
                                {"label": "On-target Reads",
                                "value": BAMQC_COL.ReadsOnTarget},
                                {"label": "Mean Insert Size",
                                "value": BAMQC_COL.InsertMean}
                        ]
                    ),

                    sidebar_utils.select_colour_by(ids['colour-by'],
                                                shape_colour.dropdown(),
                                                initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids['shape-by'],
                                                shape_colour.dropdown(),
                                                initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                          []),
                    
                    sidebar_utils.show_data_labels_input_single_lane(ids['show-data-labels'],
                                                        initial["shownames_val"],
                                                        'ALL LABELS',
                                                        ids['show-all-data-labels']),

                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.total_reads_cutoff_input(
                        ids['passed-filter-reads-cutoff'], initial[cutoff_pf_reads]),
                    sidebar_utils.insert_mean_cutoff(
                        ids['insert-size-mean-cutoff'], initial[cutoff_insert_mean]),
                    
                    html.Br(),
                    html.Button('Update', id=ids['update-button-bottom'], className="update-button"),
                ]),

                # Graphs + Tables tabs
                html.Div(className="seven columns", 
                children=[
                    core.Tabs([
                        # Graphs tab
                        core.Tab(label="Graphs",
                        children=[
                            core.Graph(id=ids['on-target-reads-various-bar'],
                                figure=generate_on_target_reads_bar(df, initial)
                            ),
                            core.Graph(id=ids['average-coverage-scatter'],
                                figure=generate_average_coverage_scatter(df, initial)
                            ),
                            core.Graph(id=ids['on-target-reads-sars-cov-2-scatter'],
                                figure=generate_on_target_reads_scatter(df, initial)
                            ),
                            core.Graph(id=ids['coverage-percentiles-line'],
                                figure=generate_coverage_percentiles_line(df, initial)
                            ),
                            core.Graph(id=ids['coverage-uniformity-scatter'],
                                figure=generate_coverage_uniformity_scatter(df, initial)
                            ), 
                        ]),
                        # Tables tab
                        core.Tab(label="Tables",
                        children=[
                            table_tabs(
                                ids["failed-samples"],
                                ids["data-table"],
                                df,
                                ex_table_columns,
                                [
                                    (cutoff_insert_mean_label, BAMQC_COL.InsertMean, initial[cutoff_insert_mean],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_pf_reads_label,
                                    special_cols["Total Reads (Passed Filter)"], initial[cutoff_pf_reads],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                ]
                            )
                        ])
                    ]) # End Tabs
                ]) # End Div
            ]) # End Div
        ]) # End Div
    ]) # End Loading


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["approve-run-button"], "href"),
            Output(ids["approve-run-button"], "style"),
            Output(ids['on-target-reads-various-bar'], 'figure'),
            Output(ids['average-coverage-scatter'], 'figure'),
            Output(ids['on-target-reads-sars-cov-2-scatter'], 'figure'),
            Output(ids['coverage-percentiles-line'], 'figure'),
            Output(ids['coverage-uniformity-scatter'], 'figure'),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids['data-table'], 'data'),
            Output(ids["search-sample"], "options"),
            Output(ids["jira-issue-with-runs-button"], "href"),
            Output(ids["jira-issue-with-runs-button"], "style"),
        ],
        [Input(ids['update-button-top'], 'n_clicks'),
        Input(ids['update-button-bottom'], 'n_clicks')],
        [
            State(ids['run-id-list'], 'value'),
            State(ids['instruments-list'], 'value'),
            State(ids['projects-list'], 'value'),
            State(ids['references-list'], 'value'),
            State(ids['kits-list'], 'value'),
            State(ids['library-designs-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['search-sample'], 'value'), 
            State(ids['show-data-labels'], 'value'),
            State(ids["date-range"], 'start_date'),
            State(ids["date-range"], 'end_date'),
            State('url', 'search'),
        ]
    )
    def update_pressed(click,
            click2,
            runs,
            instruments,
            projects,
            references,
            kits,
            library_designs,
            first_sort, 
            second_sort, 
            colour_by,
            shape_by,
            searchsample,
            show_names,
            start_date,
            end_date,
            search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)

        df = reshape_single_lane_df(bamqc, runs, instruments, projects, references, kits, library_designs,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        (approve_run_href, approve_run_style) = sidebar_utils.approve_run_url(runs)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            cutoff_pf_reads: total_reads_cutoff,
            cutoff_insert_mean: insert_mean_cutoff
        }

        dd = defaultdict(list)
        (failure_df, failure_columns ) = cutoff_table_data_ius(df, [
                (cutoff_insert_mean_label, BAMQC_COL.InsertMean, insert_mean_cutoff,
                 (lambda row, col, cutoff: row[col] < cutoff)),
                (cutoff_pf_reads_label, special_cols["Total Reads (Passed "
                                                    "Filter)"], total_reads_cutoff,
                 (lambda row, col, cutoff: row[col] < cutoff)),
            ])

        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        (jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)

        return [
            approve_run_href,
            approve_run_style,
            generate_on_target_reads_bar(df, graph_params),
            generate_average_coverage_scatter(df, graph_params),
            generate_on_target_reads_scatter(df, graph_params),
            generate_coverage_percentiles_line(df, graph_params),
            generate_coverage_uniformity_scatter(df, graph_params),
            failure_columns,
            failure_df.to_dict('records'),
            df.to_dict('records', into=dd),
            [{'label': x, 'value': x} for x in new_search_sample],
            jira_href,
            jira_style
        ]

    @dash_app.callback(
        Output(ids['run-id-list'], 'value'),
        [Input(ids['all-runs'], 'n_clicks')]
    )
    def all_runs_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_RUNS]

    @dash_app.callback(
        Output(ids['instruments-list'], 'value'),
        [Input(ids['all-instruments'], 'n_clicks')]
    )
    def all_instruments_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ILLUMINA_INSTRUMENT_MODELS]

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]

    @dash_app.callback(
        Output(ids['references-list'], 'value'),
        [Input(ids['all-references'], 'n_clicks')]
    )
    def all_references_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_REFERENCES]

    @dash_app.callback(
        Output(ids['kits-list'], 'value'),
        [Input(ids['all-kits'], 'n_clicks')]
    )
    def all_kits_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_KITS]

    @dash_app.callback(
        Output(ids['library-designs-list'], 'value'),
        [Input(ids['all-library-designs'], 'n_clicks')]
    )
    def all_library_designs_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_LIBRARY_DESIGNS]

    @dash_app.callback(
        Output(ids['show-data-labels'], 'value'),
        [Input(ids['show-all-data-labels'], 'n_clicks')],
        [State(ids['show-data-labels'], 'options')]
    )
    def all_data_labels_requested(click, avail_options):
        sidebar_utils.update_only_if_clicked(click)
        return [x['value'] for x in avail_options]
