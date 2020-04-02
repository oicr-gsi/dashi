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
from gsiqcetl.column import BamQc3Column, CfMeDipQcColumn
import pinery
import logging

logger = logging.getLogger(__name__)

page_name = 'single-lane-cfmedip'
title = "Single-Lane cfMeDIP"

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
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'show-data-labels',
    'show-all-data-labels',
    'insert-size-mean-cutoff',
    'passed-filter-reads-cutoff',
    "date-range",

    #Graphs
    'number-windows',
    'percent-pf-reads-aligned',
    'percent-duplication',
    'relative-cpg-freq-enrichment',
    'observed-to-expected-enrichment',
    'AT-dropout',
    'percent-thaliana',
    'methylation-beta',

    #Data table
    'failed-samples',
    'data-table'
])

BAMQC_COL = BamQc3Column
PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn
CFMEDIP_COL = CfMeDipQcColumn

special_cols = {
    "Total Reads (Passed Filter)": "Total Reads PassedFilter",
}

initial = get_initial_single_lane_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = BAMQC_COL.TotalReads
# Set initial values for graph cutoff lines
cutoff_pf_reads_label = "Total PF Reads minimum"
cutoff_pf_reads = "cutoff_pf_reads"
initial[cutoff_pf_reads] = 0.01
cutoff_insert_mean_label = "Insert Mean minimum"
cutoff_insert_mean = "cutoff_insert_mean"
initial[cutoff_insert_mean] = 150

def get_bamqc_data():
    bamqc_df = util.get_bamqc3()
    bamqc_df[special_cols["Total Reads (Passed Filter)"]] = round(
        bamqc_df[BAMQC_COL.TotalReads] / 1e6, 3)

    pinery_samples = util.get_pinery_samples()

    bamqc_df = util.df_with_pinery_samples_ius(bamqc_df, pinery_samples, util.bamqc_ius_columns)

    bamqc_df = util.df_with_instrument_model(bamqc_df, PINERY_COL.SequencerRunName)

    bamqc_df = util.filter_by_library_design(bamqc_df, util.ex_lib_designs)

    return bamqc_df, util.cache.versions(["bamqc"])


(bamqc, DATAVERSION) = get_bamqc_data()


# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(bamqc, PINERY_COL.StudyTitle)
ALL_RUNS = util.unique_set(bamqc, PINERY_COL.SequencerRunName, True) # reverse order
ALL_KITS = util.unique_set(bamqc, PINERY_COL.PrepKit)
ALL_TISSUE_MATERIALS = util.unique_set(bamqc, PINERY_COL.TissuePreparation)
ALL_LIBRARY_DESIGNS = util.unique_set(bamqc, PINERY_COL.LibrarySourceTemplateType)
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(bamqc)
ALL_SAMPLE_TYPES = util.unique_set(bamqc, util.sample_type_col)
ALL_REFERENCES = util.unique_set(bamqc, BAMQC_COL.Reference)

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

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
]
most_bamqc_cols = [*BAMQC_COL.values()]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.ExternalName,
    PINERY_COL.GroupID, PINERY_COL.TissueOrigin, PINERY_COL.TissueType,
    PINERY_COL.TargetedResequencing, PINERY_COL.Institute,
    INSTRUMENT_COLS.ModelName
]
ex_table_columns = [*first_col_set, *most_bamqc_cols, *later_col_set]


shape_colour = ColourShapeSingleLane( # TODO: add 'Centre'?
    ALL_PROJECTS, ALL_RUNS, ALL_KITS, ALL_TISSUE_MATERIALS, ALL_LIBRARY_DESIGNS,
    ALL_REFERENCES,
)
# Add shape, colour, and size cols to dataframe 
bamqc = add_graphable_cols(bamqc, initial, shape_colour.items_for_df())


def generate_number_windows(current_data, graph_params):
    #TODO this one is like 4 different columns?
    return None

    # return generate(
    #     "Log10 # Windows at 1, 10, 50, 100x",
    #     current_data,
    #     lambda d: d[PINERY_COL.SampleName],
    #     lambda d: sidebar_utils.percentage_of(d, BAMQC_COL.UnmappedReads, BAMQC_COL.TotalReads),
    #     "Log10 Coverage",
    #     graph_params["colour_by"],
    #     graph_params["shape_by"],
    #     graph_params["shownames_val"]
    # )


def generate_percent_pf_reads_aligned(current_data, graph_params):
    return generate(
        "PF Reads Aligned (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.PercentPassedFilterAlignedReads],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_percent_duplcation(current_data, graph_params):
    return generate(
        "Duplication (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.PercentDuplication],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_relative_cpg_frequency_enrichment(current_data, graph_params):
    return generate(
        "Relative CpG Frequency Enrichment",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.RelativeCpGFrequencyEnrichment],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])]
    )

def generate_observed_to_expected_enrichment(current_data, graph_params):
    return generate(
        "Observed to Expected Enrichment",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.ObservedToExpectedEnrichment],
        "", 
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])]
    )

def generate_at_dropout(current_data, graph_params):
    return generate(
        "AT Dropout (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.ATDropout], 
        "%", 
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])]
    )

def generate_percent_thaliana(current_data, graph_params):
    return generate(
        "Thaliana (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.PercentageAthaliana],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])]
    )

def generate_methylation_beta(current_data, graph_params):
    return generate(
        "Methylation Beta",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[CFMEDIP_COL.MethylationBeta],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_insert_mean_label, graph_params[cutoff_insert_mean])]
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

                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(
                        ids['first-sort'],
                        initial["first_sort"],
                        [
                            {"label": "Centre",
                            "value": None}, #TODO ???? not a column
                            {"label": "Sample Type",
                            "value": None}, #TODO where is this
                            {"label": "Tissue Type",
                            "value": None}, #TODO where is this
                        ]
                    ),

                    sidebar_utils.select_second_sort(
                        ids['second-sort'],
                        initial["second_sort"],
                        [
                            {"label": "enrichment.score.relH",
                            "value": None}, #TODO Not a column
                            {"label": "enrichment.score.GoGe",
                            "value": None}, #TODO not a column
                            {"label": "PERCENT_DUPLICATION",
                            "value": CFMEDIP_COL.PercentDuplication}
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
                            core.Graph(id=ids['number-windows'],
                                figure=generate_number_windows(df, initial)
                            ),
                            core.Graph(id=ids['percent-pf-reads-aligned'],
                                figure=generate_percent_pf_reads_aligned(df, initial)
                            ),
                            core.Graph(id=ids['percent-duplication'],
                                figure=generate_percent_duplcation(df,initial)
                            ),
                            core.Graph(id=ids['relative-cpg-freq-enrichment'],
                                figure=generate_relative_cpg_frequency_enrichment(df, initial)
                            ),
                            core.Graph(id=ids['observed-to-expected-enrichment'],
                                figure=generate_observed_to_expected_enrichment(df, initial)
                            ),
                            core.Graph(id=ids['AT-dropout'],
                                figure=generate_at_dropout(df, initial)
                            ),
                            core.Graph(id=ids['percent-thaliana'],
                                figure=generate_percent_thaliana(df, initial)
                            ),
                            core.Graph(id=ids['methylation-beta'],
                                figure=generate_methylation_beta(df, initial)
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
            Output(ids['number-windows'], 'figure'),
            Output(ids['percent-pf-reads-aligned'], 'figure'),
            Output(ids['percent-duplication'], 'figure'),
            Output(ids['relative-cpg-freq-enrichment'], 'figure'),
            Output(ids['observed-to-expected-enrichment'], 'figure'),
            Output(ids['AT-dropout'], 'figure'),
            Output(ids['percent-thaliana'], 'figure'),
            Output(ids['methylation-beta'], 'figure'),
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
            State(ids['insert-size-mean-cutoff'], 'value'),
            State(ids['passed-filter-reads-cutoff'], 'value'),
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
            insert_mean_cutoff,
            total_reads_cutoff,
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
            generate_number_windows(df, graph_params),
            generate_percent_pf_reads_aligned(df, graph_params),
            generate_percent_duplcation(df, graph_params),
            generate_relative_cpg_frequency_enrichment(df, graph_params),
            generate_observed_to_expected_enrichment(df, graph_params),
            generate_at_dropout(df, graph_params),
            generate_percent_thaliana(df, graph_params),
            generate_methylation_beta(df, graph_params),
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
