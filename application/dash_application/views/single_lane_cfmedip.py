from collections import defaultdict

import dash_html_components as html
from dash.dependencies import Input, Output, State
from ..dash_id import init_ids
from ..utility.plot_builder import *
from ..utility.table_builder import table_tabs_single_lane, cutoff_table_data_ius
from ..utility import df_manipulation as util
from ..utility import sidebar_utils
from ..utility import log_utils
from gsiqcetl.column import CfMeDipQcColumn
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
    'all-institutes',
    'institutes-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'search-sample-ext',
    'show-data-labels',
    'show-all-data-labels',
    'minimum-clusters-cutoff',
    'relative-cpg-enrichment-cutoff',
    'at-dropout-cutoff',
    'percent-thaliana-cutoff',
    'methylation-beta-cutoff',
    "date-range",

    #Graphs
    "graphs",

    #Data table
    'failed-samples',
    'data-table',
    'failed-count',
    'data-count'
])

PINERY_COL = pinery.column.SampleProvenanceColumn
INSTRUMENT_COLS = pinery.column.InstrumentWithModelColumn
RUN_COLS = pinery.column.RunsColumn
CFMEDIP_COL = CfMeDipQcColumn

special_cols = {
    "Total Reads (Passed Filter)": "Total Reads PassedFilter",
}

initial = get_initial_cfmedip_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = CFMEDIP_COL.RelativeCpGFrequencyEnrichment
initial["institutes"] = []
# Set initial values for graph cutoff lines
cutoff_minimum_clusters_label = sidebar_utils.clusters_per_sample_cutoff_label
initial["cutoff_minimum_clusters"] = 0
cutoff_relative_cpg_enrichment_label = "Relative CpG Enrichment 🚧 NO EFFECT"
initial["cutoff_relative_cpg_enrichmnet"] = 0
cutoff_at_dropout_label = "AT Dropout 🚧 NO EFFECT"
initial["cutoff_at_dropout"] = 0
cutoff_percent_thaliana_label = "% Thaliana minimum"
initial["cutoff_percent_thaliana"] = 0
cutoff_methylation_beta_label = "Methylation Beta 🚧 NO EFFECT"
initial["cutoff_methylation_beta"] = 0

def get_cfmedip_data():
    cfmedip_df = util.get_cfmedip()
    cfmedip_df[special_cols["Total Reads (Passed Filter)"]] = round(
        cfmedip_df[CFMEDIP_COL.TotalReads] / 1e6, 3
    )

    pinery_samples = util.get_pinery_samples()

    cfmedip_df = util.df_with_pinery_samples_ius(cfmedip_df, pinery_samples, util.cfmedip_ius_columns)

    cfmedip_df = util.df_with_instrument_model(cfmedip_df, PINERY_COL.SequencerRunName)

    return cfmedip_df, util.cache.versions(["cfmedipqc"])


(cfmedip, DATAVERSION) = get_cfmedip_data()


# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(cfmedip, PINERY_COL.StudyTitle)
ALL_RUNS = util.unique_set(cfmedip, PINERY_COL.SequencerRunName, True) # reverse order
ALL_KITS = util.unique_set(cfmedip, PINERY_COL.PrepKit)
ALL_TISSUE_MATERIALS = util.unique_set(cfmedip, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(cfmedip, PINERY_COL.TissueOrigin)
ILLUMINA_INSTRUMENT_MODELS = util.get_illumina_instruments(cfmedip)
ALL_SAMPLE_TYPES = util.unique_set(cfmedip, util.sample_type_col)
ALL_REFERENCES = util.unique_set(cfmedip, CFMEDIP_COL.Reference)
ALL_INSTITUTES = util.unique_set(cfmedip, PINERY_COL.Institute)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "references": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_REFERENCES, "all_references"),
}

# Specify which columns to display in the DataTable
first_col_set = [
    PINERY_COL.SampleName, PINERY_COL.StudyTitle,
]
most_cfmedip_cols = [*CFMEDIP_COL.values()]
later_col_set = [
    PINERY_COL.PrepKit, PINERY_COL.TissuePreparation,
    PINERY_COL.LibrarySourceTemplateType, PINERY_COL.ExternalName,
    PINERY_COL.GroupID, PINERY_COL.TissueOrigin, PINERY_COL.TissueType,
    PINERY_COL.TargetedResequencing, PINERY_COL.Institute,
    INSTRUMENT_COLS.ModelName
]
cfmedip_table_columns = [*first_col_set, *most_cfmedip_cols, *later_col_set]


shape_colour = ColourShapeCfMeDIP(
    ALL_PROJECTS, 
    ALL_RUNS,
    ALL_INSTITUTES, 
    ALL_SAMPLE_TYPES,
    ALL_TISSUE_MATERIALS,
    ALL_TISSUE_ORIGIN,
    ALL_REFERENCES
)
# Add shape, colour, and size cols to dataframe 
cfmedip = add_graphable_cols(cfmedip, initial, shape_colour.items_for_df())

SORT_BY = sidebar_utils.default_first_sort + [
    {"label": "Project",
     "value": PINERY_COL.StudyTitle},
    {"label": "Institute",
     "value": PINERY_COL.Institute},
    {"label": "Sample Type",
     "value": util.sample_type_col},
    {"label": "Tissue Type",
     "value": PINERY_COL.TissueType},
    {"label": "Run",
     "value": PINERY_COL.SequencerRunName},
    {"label": "Relative CpG Frequency Enrichment",
     "value": CFMEDIP_COL.RelativeCpGFrequencyEnrichment},
    {"label": "Observed to Expected Enrichment",
     "value": CFMEDIP_COL.ObservedToExpectedEnrichment},
    {"label": "PERCENT_DUPLICATION",
     "value": CFMEDIP_COL.PercentDuplication},
    {"label": "Sample Name",
     "value": PINERY_COL.SampleName}
]

def generate_number_windows(current_data, graph_params):
    return SingleLaneSubplot(
        "Log10 # Windows at 1, 10, 50, 100x",
        current_data,
        [
            lambda d: d[CFMEDIP_COL.NumWindowsWith1Reads], 
            lambda d: d[CFMEDIP_COL.NumWindowsWith10Reads],
            lambda d: d[CFMEDIP_COL.NumWindowsWith50Reads],
            lambda d: d[CFMEDIP_COL.NumWindowsWith100Reads]
        ],
        "Log10 Coverage",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_percent_pf_reads_aligned(current_data, graph_params):
    return SingleLaneSubplot(
        "PF Reads Aligned (%)",
        current_data,
        lambda d: d[CFMEDIP_COL.PercentPassedFilterAlignedReads] * 100,
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )


def generate_percent_duplcation(current_data, graph_params):
    return SingleLaneSubplot(
        "Duplication (%)",
        current_data,
        lambda d: d[CFMEDIP_COL.PercentDuplication],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"]
    )


def generate_relative_cpg_frequency_enrichment(current_data, graph_params):
    return SingleLaneSubplot(
        "Relative CpG Frequency Enrichment",
        current_data,
        lambda d: d[CFMEDIP_COL.RelativeCpGFrequencyEnrichment],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        # cutoff_lines=[(cutoff_relative_cpg_label, graph_params["cutoff_relative_cpg_enrichment"])]
    )

def generate_observed_to_expected_enrichment(current_data, graph_params):
    return SingleLaneSubplot(
        "Observed to Expected Enrichment",
        current_data,
        lambda d: d[CFMEDIP_COL.ObservedToExpectedEnrichment],
        "", 
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )

def generate_at_dropout(current_data, graph_params):
    return SingleLaneSubplot(
        "AT Dropout (%)",
        current_data,
        lambda d: d[CFMEDIP_COL.ATDropout], 
        "%", 
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        # cutoff_lines=[(cutoff_at_dropout_label, graph_params["cutoff_at_dropout"])]
    )

def generate_percent_thaliana(current_data, graph_params):
    return SingleLaneSubplot(
        "Thaliana (%)",
        current_data,
        lambda d: d[CFMEDIP_COL.PercentageAthaliana],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_percent_thaliana_label, graph_params["cutoff_percent_thaliana"])]
    )

def generate_methylation_beta(current_data, graph_params):
    return SingleLaneSubplot(
        "Methylation Beta",
        current_data,
        lambda d: d[CFMEDIP_COL.MethylationBeta],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        # cutoff_lines=[(cutoff_methylation_beta_label, graph_params["cutoff_methylation_beta"])]
    )


GRAPHS = [
    generate_number_windows,
    generate_percent_pf_reads_aligned,
    generate_percent_duplcation,
    generate_relative_cpg_frequency_enrichment,
    generate_observed_to_expected_enrichment,
    generate_at_dropout,
    generate_percent_thaliana,
    generate_methylation_beta,
]

def dataversion():
    return DATAVERSION


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # initial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]

    df = reshape_cfmedip_df(cfmedip, initial["runs"], initial["instruments"],
                                initial["projects"], initial["references"], initial["kits"],
                                initial["institutes"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className='body', children=[
            html.Div(className="row jira-buttons", children=[
                sidebar_utils.jira_button("Open an issue",
                                          ids['general-jira-issue-button'],
                                          {"display": "inline-block"},
                                          sidebar_utils.construct_jira_link([], title)),
                sidebar_utils.jira_button("Open an issue about these runs",
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
                                                ALL_PROJECTS,
                                                query["req_projects"]),

                    sidebar_utils.select_reference(ids["all-references"],
                                                   ids["references-list"],
                                                   ALL_REFERENCES),

                    sidebar_utils.select_kits(ids["all-kits"], ids["kits-list"],
                                            ALL_KITS),

                    sidebar_utils.select_instruments(ids["all-instruments"],
                                                    ids["instruments-list"],
                                                    ILLUMINA_INSTRUMENT_MODELS),

                    sidebar_utils.select_with_select_all("All Institutes", ids['all-institutes'],
                                  "Filter by Institute", ids['institutes-list'],
                                  ALL_INSTITUTES),

                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(
                        ids['first-sort'],
                        initial["first_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_second_sort(
                        ids['second-sort'],
                        initial["second_sort"],
                        SORT_BY,
                    ),

                    sidebar_utils.select_colour_by(ids['colour-by'],
                                                shape_colour.dropdown(),
                                                initial["colour_by"]),

                    sidebar_utils.select_shape_by(ids['shape-by'],
                                                shape_colour.dropdown(),
                                                initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                          []),

                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(ids['search-sample-ext'],
                                                          None),
                    
                    sidebar_utils.show_data_labels_input_single_lane(ids['show-data-labels'],
                                                        initial["shownames_val"],
                                                        'ALL LABELS',
                                                        ids['show-all-data-labels']),

                    sidebar_utils.hr(),

                    # Cutoffs
                    # sidebar_utils.cutoff_input(cutoff_minimum_clusters_label,
                    #     ids['minimum-clusters-cutoff'], initial["cutoff_minimum_clusters"]),
                    # sidebar_utils.cutoff_input(cutoff_relative_cpg_enrichment_label,
                    #     ids['relative-cpg-enrichment-cutoff'], initial["cutoff_relative_cpg_enrichment"]),
                    # sidebar_utils.cutoff_input(cutoff_at_dropout_label,
                    #     ids['at-dropout-cutoff'], initial["cutoff_at_dropout"]),
                    sidebar_utils.cutoff_input(cutoff_percent_thaliana_label,
                        ids['percent-thaliana-cutoff'], initial["cutoff_percent_thaliana"]),
                    # sidebar_utils.cutoff_input(cutoff_methylation_beta_label,
                    #     ids['methylation-beta-cutoff'], initial["cutoff_methylation_beta"]),
                    
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
                            create_graph_element_with_subplots(ids["graphs"], df, initial, GRAPHS),
                        ]),
                        # Tables tab
                        core.Tab(label="Tables",
                        children=[
                            table_tabs_single_lane(
                                ids["failed-samples"],
                                ids["data-table"],
                                ids["failed-count"],
                                ids["data-count"],
                                df,
                                cfmedip_table_columns,
                                [
                                    # (cutoff_minimum_clusters_label,
                                    # ???, initial["cutoff_minimum_clusters"],
                                    # (lambda row, col, cutoff: row[col] < cutoff)),
                                    # (cutoff_relative_cpg_enrichment_label,
                                    # CFMEDIP_COL.RelativeCpGFrequencyEnrichment, initial["cutoff_relative_cpg_enrichment"],
                                    # (lambda row, col, cutoff: row[col] < cutoff)),
                                    # (cutoff_at_dropout_label,
                                    # CFMEDIP_COL.ATDropout, initial["cutoff_at_dropout"],
                                    # (lambda row, col, cutoff: row[col] < cutoff)),
                                    (cutoff_percent_thaliana_label,
                                    CFMEDIP_COL.PercentageAthaliana, initial["cutoff_percent_thaliana"],
                                    (lambda row, col, cutoff: row[col] < cutoff)),
                                    # (cutoff_methylation_beta_label,
                                    # CFMEDIP_COL.MethylationBeta, initial["cutoff_methylation_beta"],
                                    # (lambda row, col, cutoff: row[col] < cutoff)),
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
            Output(ids['graphs'], 'figure'),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids['data-table'], 'data'),
            Output(ids["failed-count"], "children"),
            Output(ids["data-count"], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids["search-sample-ext"], "options"),
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
            State(ids['institutes-list'], 'value'),
            State(ids['first-sort'], 'value'),
            State(ids['second-sort'], 'value'),
            State(ids['colour-by'], 'value'),
            State(ids['shape-by'], 'value'),
            State(ids['search-sample'], 'value'), 
            State(ids['search-sample-ext'], 'value'),
            State(ids['show-data-labels'], 'value'),
            # State(ids['minimum-clusters-cutoff'], 'value'),
            # State(ids['relative-cpg-enrichment-cutoff'], 'value'),
            # State(ids['at-dropout-cutoff'], 'value'),
            State(ids['percent-thaliana-cutoff'], 'value'),
            # State(ids['methylation-beta-cutoff'], 'value'),
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
            institutes,
            first_sort, 
            second_sort, 
            colour_by,
            shape_by,
            searchsample,
            searchsampleext,
            show_names,
            # minimum_clusters_cutoff,
            # relative_cpg_enrichment_cutoff,
            # at_dropout_cutoff,
            percent_thaliana_cutoff,
            # methylation_beta_cutoff,
            start_date,
            end_date,
            search_query):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if searchsample and searchsampleext:
            searchsample += searchsampleext
        elif not searchsample and searchsampleext:
            searchsample = searchsampleext
        df = reshape_cfmedip_df(cfmedip, runs, instruments, projects, references, kits, institutes,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        (approve_run_href, approve_run_style) = sidebar_utils.approve_run_url(runs)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            # "cutoff_minimum_clusters": minimum_clusters_cutoff,
            # "cutoff_relative_cpg_enrichment": relative_cpg_enrichment_cutoff,
            # "cutoff_at_dropout": at_dropout_cutoff,
            "cutoff_percent_thaliana": percent_thaliana_cutoff,
            # "cutoff_methylation_beta": methylation_beta_cutoff,
        }

        dd = defaultdict(list)
        (failure_df, failure_columns ) = cutoff_table_data_ius(df, [
                # (cutoff_minimum_clusters_label,
                #     ???, minimum_clusters_cutoff,
                #     (lambda row, col, cutoff: row[col] < cutoff)),
                # (cutoff_relative_cpg_enrichment_label,
                #     CFMEDIP_COL.RelativeCpGFrequencyEnrichment, relative_cpg_enrichment_cutoff,
                #     (lambda row, col, cutoff: row[col] < cutoff)),
                # (cutoff_at_dropout_label,
                #     CFMEDIP_COL.ATDropout, at_dropout_cutoff,
                #     (lambda row, col, cutoff: row[col] < cutoff)),
                (cutoff_percent_thaliana_label,
                    CFMEDIP_COL.PercentageAthaliana, percent_thaliana_cutoff,
                    (lambda row, col, cutoff: row[col] < cutoff)),
                # (cutoff_methylation_beta_label,
                #     CFMEDIP_COL.MethylationBeta, methylation_beta_cutoff,
                #     (lambda row, col, cutoff: row[col] < cutoff)),
            ])

        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        (jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)

        return [
            approve_run_href,
            approve_run_style,
            generate_subplot_from_func(df, graph_params, GRAPHS),
            failure_columns,
            failure_df.to_dict('records'),
            df.to_dict('records', into=dd),
            "Rows: {0}".format(len(failure_df.index)),
            "Rows: {0}".format(len(df.index)),
            [{'label': x, 'value': x} for x in new_search_sample],
            [{'label': d[PINERY_COL.ExternalName], 'value': d[PINERY_COL.SampleName]} for i, d in df[[PINERY_COL.ExternalName, PINERY_COL.SampleName]].iterrows()],
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
        Output(ids['institutes-list'], 'value'),
        [Input(ids['all-institutes'], 'n_clicks')]
    )
    def all_institutes_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_INSTITUTES]

    @dash_app.callback(
        Output(ids['show-data-labels'], 'value'),
        [Input(ids['show-all-data-labels'], 'n_clicks')],
        [State(ids['show-data-labels'], 'options')]
    )
    def all_data_labels_requested(click, avail_options):
        sidebar_utils.update_only_if_clicked(click)
        return [x['value'] for x in avail_options]

def reshape_cfmedip_df(df, runs, instruments, projects, references, kits, institutes,
        start_date, end_date, first_sort, second_sort, colour_by, shape_by,
        shape_or_colour_values, searchsample) -> DataFrame:
    """
    This performs dataframe manipulation based on the input filters, and gets the data into a
    graph-friendly form.
    """
    if not runs and not instruments and not projects and not kits and not institutes and not references:
        df = DataFrame(columns=df.columns)

    if runs:
        df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs)]
    if instruments:
        df = df[df[pinery.column.InstrumentWithModelColumn.ModelName].isin(instruments)]
    if projects:
        df = df[df[pinery.column.SampleProvenanceColumn.StudyTitle].isin(projects)]
    if references:
        df = df[df[COMMON_COL.Reference].isin(references)]
    if kits:
        df = df[df[pinery.column.SampleProvenanceColumn.PrepKit].isin(kits)]
    if institutes:
        df = df[df[pinery.column.SampleProvenanceColumn.Institute].isin(
            institutes)]
    df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs_in_range(start_date, end_date))]
    sort_by = [first_sort, second_sort]
    df = df.sort_values(by=sort_by)
    df["SampleNameExtra"] = df[PINERY_COL.SampleName].str.cat(
        [str(x) for x in range(len(df))], sep=".")
    df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = fill_in_colour_col(df, colour_by, shape_or_colour_values, searchsample)
    df = fill_in_size_col(df, searchsample)
    return df