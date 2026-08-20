import logging

from dash import html
from dash.dependencies import Input, Output, State

from ..dash_id import init_ids

from ..utility.plot_builder import *
from ..utility.table_builder import build_table, table_tabs_call_ready, cutoff_table_data_merged
from ..utility import df_manipulation as util
from ..utility import sidebar_utils, log_utils

logger = logging.getLogger(__name__)

"""
Call-Ready WGS report for ICA data.
"""
page_name = "call-ready-wgs-ica"
title = "Call-Ready WGS (ICA)"

ids = init_ids([
    # Buttons
    "update-button-top",
    "update-button-bottom",

    # Sidebar controls
    "all-projects",
    "projects-list",
    "all-tissue-materials",
    "tissue-materials-list",
    "all-sample-types",
    "sample-types-list",
    "first-sort",
    "second-sort",
    "colour-by",
    "shape-by",
    "search-sample",
    "search-sample-ext",
    "show-data-labels",
    "show-all-data-labels",
    "cutoff-coverage-tumour",
    "cutoff-coverage-normal",

    # Graphs
    "graphs",

    # Tables
    "failed-samples",
    "all-samples",
    "failed-count",
    "all-count",
])

ICA_COL = qcetl.column.ICAMetricsColumn
PINERY_COL = pinery.column.SampleProvenanceColumn


def dataversion():
    return DATAVERSION


def get_icametrics_data():
    ica_df = util.cache.load_same_version("icametrics").unique("icametrics").copy(deep=True)

    pinery_samples = util.get_pinery_samples(active_projects_only=False)
    pinery_cols = [
        PINERY_COL.SampleProvenanceID,
        PINERY_COL.StudyTitle,
        PINERY_COL.RootSampleName,
        PINERY_COL.GroupID,
        PINERY_COL.LibrarySourceTemplateType,
        PINERY_COL.TissuePreparation,
        PINERY_COL.TissueOrigin,
        PINERY_COL.TissueType,
        PINERY_COL.ExternalName,
        util.sample_type_col,
    ]
    ica_df = ica_df.merge(
        pinery_samples[pinery_cols],
        how="left",
        left_on=ICA_COL.PineryLimsID,
        right_on=PINERY_COL.SampleProvenanceID,
    )

    return ica_df, util.cache.versions(["icametrics"])


# Make the ICA dataframe
(ICA_DF, DATAVERSION) = get_icametrics_data()
ica_curated_columns = [
    ICA_COL.Project,
    ICA_COL.DeID,
    ICA_COL.Run,
    ICA_COL.PineryLimsID,
    PINERY_COL.ExternalName,
    PINERY_COL.GroupID,
    PINERY_COL.LibrarySourceTemplateType,
    PINERY_COL.TissuePreparation,
    PINERY_COL.TissueOrigin,
    PINERY_COL.TissueType,
    util.sample_type_col,
    ICA_COL.MeanCovGenome,
    ICA_COL.MeanCovFull,
    ICA_COL.MeanCovSub,
    ICA_COL.FailedRegion,
    ICA_COL.PctGenome,
    ICA_COL.UniCov,
    ICA_COL.PctMapped,
    ICA_COL.PctUnique,
    ICA_COL.MeanInsertLength,
    ICA_COL.MedInsertLength,
    ICA_COL.TiTvRatio,
    ICA_COL.PctAutosome,
    ICA_COL.CovUni,
    ICA_COL.DupDelRatio,
    ICA_COL.Sex,
    ICA_COL.ObsSex,
]


class ColourShapeICA:
    """
    Same idea as plot_builder.ColourShapeCallReady, scoped to the dimensions
    icametrics + the Pinery join actually provide (no Library Design/
    Institute/Reference here).
    """
    def __init__(self, projects, sample_types, tissue_materials, tissue_origin):
        self.projects = projects
        self.sample_types = sample_types
        self.tissue_materials = tissue_materials
        self.tissue_origin = tissue_origin

    @staticmethod
    def dropdown():
        return [
            {"label": "Project", "value": ICA_COL.Project},
            {"label": "Sample Type", "value": util.sample_type_col},
            {"label": "Tissue Material", "value": PINERY_COL.TissuePreparation},
            {"label": "Tissue Origin", "value": PINERY_COL.TissueOrigin},
        ]

    def items_for_df(self):
        return {
            ICA_COL.Project: self.projects,
            util.sample_type_col: self.sample_types,
            PINERY_COL.TissuePreparation: self.tissue_materials,
            PINERY_COL.TissueOrigin: self.tissue_origin,
        }


initial = {
    "projects": [],
    "tissue_materials": [],
    "sample_types": [],
    "first_sort": ICA_COL.Project,
    "second_sort": ICA_COL.DeID,
    "colour_by": ICA_COL.Project,
    "shape_by": util.sample_type_col,
    "shownames_val": None,
}
cutoff_coverage_tumour_label = "Coverage (Tumour) minimum"
initial["cutoff_coverage_tumour"] = 80
cutoff_coverage_normal_label = "Coverage (Normal) minimum"
initial["cutoff_coverage_normal"] = 30

# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(ICA_DF, ICA_COL.Project)
ALL_TISSUE_MATERIALS = util.unique_set(ICA_DF, PINERY_COL.TissuePreparation)
ALL_TISSUE_ORIGIN = util.unique_set(ICA_DF, PINERY_COL.TissueOrigin)
ALL_SAMPLE_TYPES = util.unique_set(ICA_DF, util.sample_type_col)

collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected,
                                                                    ALL_PROJECTS,
                                                                    "all_projects"),
    "tissue_materials": lambda selected: log_utils.collapse_if_all_selected(
        selected, ALL_TISSUE_MATERIALS, "all_tissue_materials"),
    "sample_types": lambda selected: log_utils.collapse_if_all_selected(
        selected, ALL_SAMPLE_TYPES, "all_sample_types"),
}

shape_colour = ColourShapeICA(
    ALL_PROJECTS, ALL_SAMPLE_TYPES, ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN
)
ICA_DF = add_graphable_cols(
    ICA_DF, initial, shape_colour.items_for_df(), None, ICA_COL.DeID
)

SORT_BY = shape_colour.dropdown() + [
    {"label": "Mean Coverage (Genome)", "value": ICA_COL.MeanCovGenome},
]


def reshape_ica_df(df, projects, tissue_materials, sample_types, first_sort,
        second_sort, colour_by, shape_by, shape_or_colour_values, searchsample):
    """
    This performs dataframe manipulation based on the input filters, and gets the data into a
    graph-friendly form.
    """
    if not projects and not tissue_materials and not sample_types:
        df = DataFrame(columns=df.columns)
    else:
        if projects:
            df = df[df[ICA_COL.Project].isin(projects)]
        if tissue_materials:
            df = df[df[PINERY_COL.TissuePreparation].isin(tissue_materials)]
        if sample_types:
            df = df[df[util.sample_type_col].isin(sample_types)]

    sort_by = [s for s in [first_sort, second_sort] if s]
    df = df.sort_values(by=sort_by)
    df = fill_in_shape_col(df, shape_by, shape_or_colour_values)
    df = fill_in_colour_col(
        df, colour_by, shape_or_colour_values, searchsample, ICA_COL.DeID
    )
    df = fill_in_size_col(df, searchsample, ICA_COL.DeID)
    return df


def generate_mean_coverage_genome(df, graph_params):
    return CallReadySubplot(
        "Mean Coverage (Genome)",
        df,
        lambda d: d[ICA_COL.MeanCovGenome],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
        cutoff_lines=[
            (cutoff_coverage_tumour_label, graph_params["cutoff_coverage_tumour"]),
            (cutoff_coverage_normal_label, graph_params["cutoff_coverage_normal"]),
        ],
    )


def generate_mean_coverage_full(df, graph_params):
    return CallReadySubplot(
        "Mean Coverage (Full)",
        df,
        lambda d: d[ICA_COL.MeanCovFull],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_mean_coverage_sub(df, graph_params):
    return CallReadySubplot(
        "Mean Coverage (Sub)",
        df,
        lambda d: d[ICA_COL.MeanCovSub],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_failed_region(df, graph_params):
    return CallReadySubplot(
        "Failed Region",
        df,
        lambda d: d[ICA_COL.FailedRegion],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_pct_genome(df, graph_params):
    return CallReadySubplot(
        "% Genome",
        df,
        lambda d: d[ICA_COL.PctGenome],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_uniformity_coverage(df, graph_params):
    return CallReadySubplot(
        "Uniformity of Coverage",
        df,
        lambda d: d[ICA_COL.UniCov],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_pct_mapped(df, graph_params):
    return CallReadySubplot(
        "% Mapped Reads",
        df,
        lambda d: d[ICA_COL.PctMapped],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_pct_unique(df, graph_params):
    return CallReadySubplot(
        "% Unique Reads",
        df,
        lambda d: d[ICA_COL.PctUnique],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_mean_insert_length(df, graph_params):
    return CallReadySubplot(
        "Mean Insert Length",
        df,
        lambda d: d[ICA_COL.MeanInsertLength],
        "Base Pairs",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_median_insert_length(df, graph_params):
    return CallReadySubplot(
        "Median Insert Length",
        df,
        lambda d: d[ICA_COL.MedInsertLength],
        "Base Pairs",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_ti_tv_ratio(df, graph_params):
    return CallReadySubplot(
        "Ti/Tv Ratio",
        df,
        lambda d: d[ICA_COL.TiTvRatio],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_pct_autosome_callability(df, graph_params):
    return CallReadySubplot(
        "% Autosome Callability",
        df,
        lambda d: d[ICA_COL.PctAutosome],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_coverage_uniformity(df, graph_params):
    return CallReadySubplot(
        "Coverage Uniformity",
        df,
        lambda d: d[ICA_COL.CovUni],
        "%",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


def generate_dup_del_ratio(df, graph_params):
    return CallReadySubplot(
        "Dup/Del Ratio",
        df,
        lambda d: d[ICA_COL.DupDelRatio],
        "",
        graph_params["colour_by"],
        graph_params["shape_by"],
        graph_params["shownames_val"],
        x_fn=lambda d: d[ICA_COL.DeID],
    )


GRAPHS = [
    generate_mean_coverage_genome,
    generate_mean_coverage_full,
    generate_mean_coverage_sub,
    generate_failed_region,
    generate_pct_genome,
    generate_uniformity_coverage,
    generate_pct_mapped,
    generate_pct_unique,
    generate_mean_insert_length,
    generate_median_insert_length,
    generate_ti_tv_ratio,
    generate_pct_autosome_callability,
    generate_coverage_uniformity,
    generate_dup_del_ratio,
]


def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]
    elif "req_start" in query and query["req_start"]:
        initial["projects"] = ALL_PROJECTS
        query["req_projects"] = ALL_PROJECTS  # fill in the projects dropdown

    df = reshape_ica_df(ICA_DF, initial["projects"], initial["tissue_materials"],
                        initial["sample_types"], initial["first_sort"],
                        initial["second_sort"], initial["colour_by"],
                        initial["shape_by"], shape_colour.items_for_df(), [])

    return core.Loading(fullscreen=True, type="dot", children=[
        html.Div(className="body", children=[
            html.Div(className="row flex-container", children=[
                html.Div(className="sidebar four columns", children=[
                    html.Button("Update", id=ids["update-button-top"], className="update-button"),
                    html.Br(),
                    html.Br(),

                    # Filters
                    sidebar_utils.select_projects(ids["all-projects"],
                                                  ids["projects-list"],
                                                  ALL_PROJECTS,
                                                  query["req_projects"]),
                    sidebar_utils.select_tissue_materials(
                        ids["all-tissue-materials"],
                        ids["tissue-materials-list"],
                        ALL_TISSUE_MATERIALS),
                    sidebar_utils.select_sample_types(ids["all-sample-types"],
                                                      ids["sample-types-list"],
                                                      ALL_SAMPLE_TYPES),
                    sidebar_utils.hr(),

                    # Sort, colour, and shape
                    sidebar_utils.select_first_sort(
                        ids["first-sort"], initial["first_sort"], SORT_BY),
                    sidebar_utils.select_second_sort(
                        ids["second-sort"], initial["second_sort"], SORT_BY),
                    sidebar_utils.select_colour_by(ids["colour-by"],
                                                   shape_colour.dropdown(),
                                                   initial["colour_by"]),
                    sidebar_utils.select_shape_by(ids["shape-by"],
                                                  shape_colour.dropdown(),
                                                  initial["shape_by"]),

                    sidebar_utils.highlight_samples_input(ids['search-sample'],
                                                          []),
                    sidebar_utils.highlight_samples_by_ext_name_input_single_lane(
                        ids['search-sample-ext'], None),

                    # Show Data Labels: hand-rolled instead of
                    # sidebar_utils.show_data_labels_input_call_ready, since
                    # that includes a "Reference" option we have no data for
                    core.Loading(type="circle", children=[
                        html.Button("ALL LABELS", id=ids["show-all-data-labels"], className="inline"),
                        html.Label([
                            "Show Data Labels",
                            core.Dropdown(
                                id=ids["show-data-labels"],
                                options=[
                                    {'label': 'External Name', 'value': PINERY_COL.ExternalName},
                                    {'label': 'Sample', 'value': ICA_COL.DeID},
                                    {'label': 'Group ID', 'value': PINERY_COL.GroupID},
                                    {'label': 'Library Design', 'value': PINERY_COL.LibrarySourceTemplateType},
                                    {'label': 'Tissue Preparation', 'value': PINERY_COL.TissuePreparation},
                                    {'label': 'Tissue Origin', 'value': PINERY_COL.TissueOrigin},
                                    {'label': 'Tissue Type', 'value': PINERY_COL.TissueType},
                                ],
                                value=initial["shownames_val"],
                                searchable=False,
                                multi=True,
                            )
                        ])
                    ]),

                    sidebar_utils.hr(),

                    # Cutoffs
                    sidebar_utils.cutoff_input(cutoff_coverage_tumour_label,
                                               ids["cutoff-coverage-tumour"],
                                               initial["cutoff_coverage_tumour"]),
                    sidebar_utils.cutoff_input(cutoff_coverage_normal_label,
                                               ids["cutoff-coverage-normal"],
                                               initial["cutoff_coverage_normal"]),

                    html.Br(),
                    html.Button("Update", id=ids["update-button-bottom"], className="update-button"),
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
                                              table_tabs_call_ready(
                                                  ids["failed-samples"],
                                                  ids['all-samples'],
                                                  ids["failed-count"],
                                                  ids['all-count'],
                                                  df,
                                                  ica_curated_columns,
                                                  [
                                                      (cutoff_coverage_tumour_label,
                                                       ICA_COL.MeanCovGenome,
                                                       initial["cutoff_coverage_tumour"],
                                                       (lambda row, col, cutoff:
                                                        row[col] < cutoff and util.is_tumour(row))),
                                                      (cutoff_coverage_normal_label,
                                                       ICA_COL.MeanCovGenome,
                                                       initial["cutoff_coverage_normal"],
                                                       (lambda row, col, cutoff:
                                                        row[col] < cutoff and util.is_normal(row))),
                                                  ]
                                              )
                                          ])
                             ])  # End Tabs
                         ])  # End Div
            ])  # End Div
        ])  # End Div
    ])  # End Loading


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["graphs"], "figure"),
            Output(ids["failed-samples"], "columns"),
            Output(ids["failed-samples"], "data"),
            Output(ids['all-samples'], "data"),
            Output(ids["failed-count"], "children"),
            Output(ids["all-count"], "children"),
            Output(ids["search-sample"], "options"),
            Output(ids['search-sample-ext'], 'options'),
        ],
        [Input(ids["update-button-top"], "n_clicks"),
        Input(ids["update-button-bottom"], "n_clicks")],
        [
            State(ids["projects-list"], "value"),
            State(ids["tissue-materials-list"], "value"),
            State(ids["sample-types-list"], "value"),
            State(ids["first-sort"], "value"),
            State(ids["second-sort"], "value"),
            State(ids["colour-by"], "value"),
            State(ids["shape-by"], "value"),
            State(ids["show-data-labels"], "value"),
            State(ids["search-sample"], "value"),
            State(ids['search-sample-ext'], 'value'),
            State(ids["cutoff-coverage-tumour"], "value"),
            State(ids["cutoff-coverage-normal"], "value"),
        ]
    )
    def update_pressed(click, click2, projects, tissue_materials, sample_types,
                       first_sort, second_sort, colour_by, shape_by, show_names,
                       search_sample, searchsampleext,
                       coverage_tumour_cutoff, coverage_normal_cutoff):
        log_utils.log_filters(locals(), collapsing_functions, logger)
        if search_sample and searchsampleext:
            search_sample += searchsampleext
        elif not search_sample and searchsampleext:
            search_sample = searchsampleext

        df = reshape_ica_df(ICA_DF, projects, tissue_materials, sample_types,
                            first_sort, second_sort, colour_by, shape_by,
                            shape_colour.items_for_df(), search_sample)

        graph_params = {
            "colour_by": colour_by,
            "shape_by": shape_by,
            "shownames_val": show_names,
            "cutoff_coverage_tumour": coverage_tumour_cutoff,
            "cutoff_coverage_normal": coverage_normal_cutoff,
        }

        (failure_df, failure_columns) = cutoff_table_data_merged(df, [
            (cutoff_coverage_tumour_label, ICA_COL.MeanCovGenome,
             coverage_tumour_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_tumour(row) else None)),
            (cutoff_coverage_normal_label, ICA_COL.MeanCovGenome,
             coverage_normal_cutoff,
             (lambda row, col, cutoff: row[col] < cutoff if util.is_normal(row) else None)),
        ])

        new_search_sample = util.unique_set(df, ICA_COL.DeID)

        return [
            generate_subplot_from_func(df, graph_params, GRAPHS),
            failure_columns,
            failure_df.to_dict("records"),
            df[ica_curated_columns].to_dict("records"),
            "Rows: {0}".format(len(failure_df.index)),
            "Rows: {0}".format(len(df.index)),
            [{'label': x, 'value': x} for x in new_search_sample],
            [{'label': d[PINERY_COL.ExternalName], 'value': d[ICA_COL.DeID]}
             for i, d in df[[PINERY_COL.ExternalName, ICA_COL.DeID]].iterrows()],
        ]

    @dash_app.callback(
        Output(ids['projects-list'], 'value'),
        [Input(ids['all-projects'], 'n_clicks')]
    )
    def all_projects_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_PROJECTS]

    @dash_app.callback(
        Output(ids['tissue-materials-list'], 'value'),
        [Input(ids['all-tissue-materials'], 'n_clicks')]
    )
    def all_tissue_materials_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_TISSUE_MATERIALS]

    @dash_app.callback(
        Output(ids['sample-types-list'], 'value'),
        [Input(ids['all-sample-types'], 'n_clicks')]
    )
    def all_sample_types_requested(click):
        sidebar_utils.update_only_if_clicked(click)
        return [x for x in ALL_SAMPLE_TYPES]

    @dash_app.callback(
        Output(ids["show-data-labels"], "value"),
        [Input(ids["show-all-data-labels"], "n_clicks")],
        [State(ids["show-data-labels"], "options")]
    )
    def all_data_labels_requested(click, avail_options):
        sidebar_utils.update_only_if_clicked(click)
        return [x["value"] for x in avail_options]
