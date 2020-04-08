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
from gsiqcetl.api import QCETLCache, QCETLColumns
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
    'data-table',
    # Cutoffs
    'average-coverage_cutoff', # TODO: Isn't this a hard limit ie, not user adjustable?
])

PINERY_COL = pinery.column.SampleProvenanceColumn

# TODO: Fake pinery columns are injected (change this to a merge when the time is right)
def add_fake_pinery_cols(df):
    df[PINERY_COL.StudyTitle] = 'CVD'
    df[PINERY_COL.PrepKit] = 'Kapa Virus'
    df[PINERY_COL.InstrumentName] = 'NovaSeq'
    df[PINERY_COL.TissuePreparation] = 'Virus'
    df[PINERY_COL.LibrarySourceTemplateType] = 'TS'
    df[PINERY_COL.SequencerRunName] = '200403_M00146_0174_000000000-D8CTN'
    df[PINERY_COL.SampleName] = 'OneSample'
    df[util.sample_type_col] = 'Normal'


# TODO: Local copy is loaded, as workflow does not exist
cache = QCETLCache('/home/avarsava/Workspace/dashi/cache_files/')
pinery_samples = util.get_pinery_samples()
# Mean Coverage and Coverage uniformity
BEDTOOLS_CALC_DF = cache.bedtools_sars_cov2.genomecov_calculations
add_fake_pinery_cols(BEDTOOLS_CALC_DF)

SAMTOOLS_STATS_COV2_HUMAN_DF = cache.samtools_stats_sars_cov2.human
add_fake_pinery_cols(SAMTOOLS_STATS_COV2_HUMAN_DF)

SAMTOOLS_STATS_COV2_DEPLETED_DF = cache.samtools_stats_sars_cov2.depleted
add_fake_pinery_cols(SAMTOOLS_STATS_COV2_DEPLETED_DF)

BEDTOOLS_COV_PERC_DF = cache.bedtools_sars_cov2.genomecov_coverage_percentile
add_fake_pinery_cols(BEDTOOLS_COV_PERC_DF)


BEDTOOLS_CALC_COL = QCETLColumns().bedtools_sars_cov2.genomecov_calculations
BEDTOOLS_PERCENTILE_COL = QCETLColumns().bedtools_sars_cov2.genomecov_coverage_percentile
SAMTOOLS_STATS_COV2_HUMAN_COL = QCETLColumns().samtools_stats_sars_cov2.human
SAMTOOLS_STATS_COV2_DEPLETED_COL = QCETLColumns().samtools_stats_sars_cov2.depleted

BEDTOOLS_PERCENTILE_DF = util.df_with_pinery_samples_ius(BEDTOOLS_COV_PERC_DF, pinery_samples, [BEDTOOLS_PERCENTILE_COL.Run, BEDTOOLS_PERCENTILE_COL.Lane, BEDTOOLS_PERCENTILE_COL.Barcodes])
stats_col = QCETLColumns().samtools_stats_sars_cov2.human
special_columns = ['reads mapped_human', 'reads unmapped_human', 'reads mapped_covid', 'reads unmapped_covid']
stats_merged = SAMTOOLS_STATS_COV2_HUMAN_DF.merge(SAMTOOLS_STATS_COV2_DEPLETED_DF, how="outer", on=[stats_col.Barcodes, stats_col.Run, stats_col.Lane], suffixes=['_human', '_covid'])
stats_merged = stats_merged[
    special_columns + [stats_col.Barcodes, stats_col.Run, stats_col.Lane]
]
stats_merged['total'] = stats_merged[special_columns].sum(axis=1)
for c in special_columns:
    stats_merged[c] = stats_merged[c] / stats_merged['total']
stats_merged = util.df_with_pinery_samples_ius(stats_merged, pinery_samples, [stats_col.Run, stats_col.Lane, stats_col.Barcodes])
add_fake_pinery_cols(stats_merged)

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(BEDTOOLS_CALC_DF, PINERY_COL.StudyTitle)
ALL_KITS = util.unique_set(BEDTOOLS_CALC_DF, PINERY_COL.PrepKit)
# TODO: Remove kludge and uncomment real line after Pinery is merged
ILLUMINA_INSTRUMENT_MODELS = util.unique_set(BEDTOOLS_CALC_DF, PINERY_COL.InstrumentName)
#ILLUMINA_INSTRUMENT_MODELS = list(util.get_illumina_instruments(RNA_DF))
ALL_TISSUE_MATERIALS = util.unique_set(BEDTOOLS_CALC_DF, PINERY_COL.TissuePreparation)
ALL_LIBRARY_DESIGNS = util.unique_set(BEDTOOLS_CALC_DF, PINERY_COL.LibrarySourceTemplateType)
ALL_RUNS = util.unique_set(BEDTOOLS_CALC_DF, PINERY_COL.SequencerRunName, True)  # reverse the list
ALL_SAMPLE_TYPES = util.unique_set(BEDTOOLS_CALC_DF, util.sample_type_col)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
}

cutoff_average_coverage = "Average Coverage Minimum"
average_coverage_cutoff = 20
initial = get_initial_single_lane_values()
initial["second_sort"] = BEDTOOLS_CALC_COL.MeanCoverage

shape_colour = ColourShapeSingleLane(ALL_PROJECTS, ALL_RUNS, ALL_KITS,
                                     ALL_TISSUE_MATERIALS, ALL_LIBRARY_DESIGNS, None)

def generate_on_target_reads_bar(current_data, graph_params):
    return generate_bar(
        current_data,
        special_columns,
        lambda d: d[stats_col.Run],
        lambda d, col: d[col] * 100,
        "On-Target (%)",
        "%"
    )


def generate_average_coverage_scatter(current_data, graph_params):
    return generate(
        "Average Coverage",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BEDTOOLS_CALC_COL.MeanCoverage],
        "Average Coverage",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        [(cutoff_average_coverage, average_coverage_cutoff)] # Should be unchanging, TODO: why won't this draw??
    )

def generate_on_target_reads_scatter(current_data, graph_params):
    return generate(
        "On Target Reads, SARS-CoV-2 (%)",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[None], #TODO: might have to come from Kraken?
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"] #TODO cutoff line
    )

def generate_coverage_percentiles_line(current_data, graph_params):
    return generate(
    "Coverage Percentile",
    current_data,
    lambda d: d[BEDTOOLS_PERCENTILE_COL.Coverage],
    lambda d: d[BEDTOOLS_PERCENTILE_COL.PercentGenomeCovered],
    "%",
    graph_params["colour_by"],
    graph_params["shape_by"],
    graph_params["shownames_val"],
    markermode="lines"
)

def generate_coverage_uniformity_scatter(current_data, graph_params):
    return generate(
        "Uniformity of Coverage",
        current_data,
        lambda d: d[PINERY_COL.SampleName],
        lambda d: d[BEDTOOLS_CALC_COL.CoverageUniformity] * 100,
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
    )

def dataversion():
    # TODO: Do it properly
    return "kludge_version"
    # return DATAVERSION


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

    df = reshape_single_lane_df(BEDTOOLS_CALC_DF, initial["runs"], initial["instruments"],
                                initial["projects"], None, initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"], initial["colour_by"],
                                initial["shape_by"], shape_colour.items_for_df(), [])

    stats_df = reshape_stats_df(stats_merged, initial["runs"], initial["instruments"],
                                initial["projects"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"], initial["first_sort"],
                                initial["second_sort"])

    percentile_df = reshape_percentile_df(BEDTOOLS_PERCENTILE_DF, initial["runs"], initial["instruments"],
                                initial["projects"], initial["kits"],
                                initial["library_designs"], initial["start_date"],
                                initial["end_date"])

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
                    sidebar_utils.select_first_sort(ids['first-sort'],
                                                    initial["first_sort"]),

                    sidebar_utils.select_second_sort(
                        ids['second-sort'],
                        initial["second_sort"],
                        [
                                {"label": "Total Reads",
                                "value": BEDTOOLS_CALC_COL.MeanCoverage},
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
                            # TODO: Add in all graphs
                            core.Graph(id=ids['on-target-reads-various-bar'],
                                figure=generate_on_target_reads_bar(stats_df, initial)
                            ),
                            core.Graph(id=ids['average-coverage-scatter'],
                                figure=generate_average_coverage_scatter(df, initial)
                            ),
                            # core.Graph(id=ids['on-target-reads-sars-cov-2-scatter'],
                            #     figure=generate_on_target_reads_scatter(df, initial)
                            # ),
                            core.Graph(id=ids['coverage-percentiles-line'],
                                figure=generate_coverage_percentiles_line(percentile_df, initial)
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
                                # TODO: Move this to the top of module
                                [BEDTOOLS_CALC_COL.MeanCoverage],
                                [
                                    (cutoff_average_coverage, BEDTOOLS_CALC_COL.MeanCoverage, average_coverage_cutoff,
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
            # Output(ids['on-target-reads-sars-cov-2-scatter'], 'figure'),
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

        df = reshape_single_lane_df(BEDTOOLS_CALC_DF, runs, instruments, projects, None, kits, library_designs,
                                    start_date, end_date, first_sort, second_sort, colour_by,
                                    shape_by, shape_colour.items_for_df(), searchsample)

        percentile_df = reshape_percentile_df(BEDTOOLS_PERCENTILE_DF, runs, instruments, projects, kits, library_designs,
                                    start_date, end_date)
        stats_df = reshape_stats_df(stats_merged, runs, instruments, projects, kits, library_designs,
                                    start_date, end_date, first_sort, second_sort)
        (approve_run_href, approve_run_style) = sidebar_utils.approve_run_url(runs)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
        }

        dd = defaultdict(list)
        (failure_df, failure_columns ) = cutoff_table_data_ius(df, [
                (cutoff_average_coverage, BEDTOOLS_CALC_COL.MeanCoverage, average_coverage_cutoff,
                 (lambda row, col, cutoff: row[col] < cutoff)),
            ])

        new_search_sample = util.unique_set(df, PINERY_COL.SampleName)

        (jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)

        return [
            approve_run_href,
            approve_run_style,
            generate_on_target_reads_bar(stats_df, graph_params),
            generate_average_coverage_scatter(df, graph_params),
            # generate_on_target_reads_scatter(df, graph_params),
            generate_coverage_percentiles_line(percentile_df, graph_params),
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

def reshape_percentile_df(df, runs, instruments, projects, kits, library_designs,
        start_date, end_date) -> DataFrame:
        
    """
    This performs dataframe manipulation based on the input filters, and gets the data into a
    graph-friendly form.
    """

    print("Starting with empty df: " + str(df.empty))
    if not runs and not instruments and not projects and not kits and not library_designs:
        df = DataFrame(columns=df.columns)
        print("empty df!")

    if runs:
        print(runs)
        print(df[pinery.column.SampleProvenanceColumn.SequencerRunName].unique())
        df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs)]
        print("Rearranged for runs:" + str(df.empty))
    if instruments:
        df = df[df[pinery.column.InstrumentWithModelColumn.ModelName].isin(instruments)]
        print("Rearranged for instruments:" + str(df.empty))
    if projects:
        df = df[df[pinery.column.SampleProvenanceColumn.StudyTitle].isin(projects)]
        print("Rearranged for projects:" + str(df.empty))
    if kits:
        df = df[df[pinery.column.SampleProvenanceColumn.PrepKit].isin(kits)]
        print("Rearranged for kits:" + str(df.empty))
    if library_designs:
        df = df[df[pinery.column.SampleProvenanceColumn.LibrarySourceTemplateType].isin(
            library_designs)]
        print("Rearranged for library designs:" + str(df.empty))
    df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs_in_range(start_date, end_date))]
    print("Filtered to dates:" + str(df.empty))
    df = fill_in_shape_col(df, initial["shape_by"], shape_colour.items_for_df())
    print("filled in shaped column:" + str(df.empty))
    df = fill_in_colour_col(df, initial["colour_by"], shape_colour.items_for_df(), None)
    print("filled in colour column:" + str(df.empty))
    df = fill_in_size_col(df, None)
    print("filled in size column:" + str(df.empty))
    return df

def reshape_stats_df(df, runs, instruments, projects, kits, library_designs,
        start_date, end_date, first_sort, second_sort) -> DataFrame:
        
    """
    This performs dataframe manipulation based on the input filters, and gets the data into a
    graph-friendly form.
    """
    print("starting with empty df:" + str(df.empty))
    if not runs and not instruments and not projects and not kits and not library_designs:
        df = DataFrame(columns=df.columns)
        print("empty df!")

    if runs:
        print(runs)
        print(df[pinery.column.SampleProvenanceColumn.SequencerRunName].unique())
        df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs)]
        print("Rearranged for runs:" + str(df.empty))
        
    if instruments:
        df = df[df[pinery.column.InstrumentWithModelColumn.ModelName].isin(instruments)]
        print("Rearranged for instruments:" + str(df.empty))
    if projects:
        df = df[df[pinery.column.SampleProvenanceColumn.StudyTitle].isin(projects)]
        print("Rearranged for projects:" + str(df.empty))
    if kits:
        df = df[df[pinery.column.SampleProvenanceColumn.PrepKit].isin(kits)]
        print("Rearranged for kits:" + str(df.empty))
    if library_designs:
        df = df[df[pinery.column.SampleProvenanceColumn.LibrarySourceTemplateType].isin(
            library_designs)]
        print("Rearranged for library designs:" + str(df.empty))
    df = df[df[pinery.column.SampleProvenanceColumn.SequencerRunName].isin(runs_in_range(start_date, end_date))]
    print("Rearranged for dates:" + str(df.empty))
    sort_by = [first_sort, second_sort]
    # df = df.sort_values(by=sort_by) TODO: This doesn't work without some weird merges. don't try for now
    df = fill_in_shape_col(df, initial["shape_by"], shape_colour.items_for_df())
    print("filled in shape col::" + str(df.empty))
    df = fill_in_colour_col(df, initial["colour_by"], shape_colour.items_for_df(), None)
    print("fiulled in colour col::" + str(df.empty))
    df = fill_in_size_col(df, None)
    print("filled in size col:" + str(df.empty))
    return df