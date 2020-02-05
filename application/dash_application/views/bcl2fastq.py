import dash_html_components as html
import dash_core_components as core
import dash_table
from dash.dependencies import Input, Output

from ..utility import df_manipulation as util
from ..dash_id import init_ids

import gsiqcetl.bcl2fastq
import gsiqcetl.column


page_name = "bcl2fastq-index-qc"
title = "Bcl2Fastq Index QC"

ids = init_ids(
    [
        "error",
        "run_select",
        "bcl2fastq_url",
        "known_index_bar",
        "known_unknown_pie",
        "known_fraction",
        "unknown_index_bar",
        "known_data_table",
        "unknown_data_table",
        "tabs_data_table",
    ]
)

# There can be many unknown indices in each run. Only display top N
MAX_UNKNOWN_DISPLAY = 30

DATAVERSION = util.cache.versions(["bcl2fastq"])
index = util.get_bcl2fastq_known()
index_col = gsiqcetl.column.Bcl2FastqKnownColumn

unknown = util.get_bcl2fastq_unknown()
un_col = gsiqcetl.column.Bcl2FastqUnknownColumn

all_runs = index[index_col.Run].sort_values(ascending=False).unique()

COL_LIBRARY = "library"
COL_INDEX = "index"

KNOWN_DATA_TABLE_COLS = [
    {"name": "Library", "id": "library"},
    {"name": "Index 1", "id": "Index1"},
    {"name": "Index 2", "id": "Index2"},
    {"name": "Library PF Clusters", "id": "ReadCount"},
    {"name": "Lane", "id": "Lane Number"},
    {"name": "Lane PF Clusters", "id": "LaneClusterPF"},
]

UNKNOWN_DATA_TABLE_COLS = [
    {"name": "Index 1", "id": "Index1"},
    {"name": "Index 2", "id": "Index2"},
    {"name": "Count", "id": "Count"},
    {"name": "Lane", "id": "Lane Number"},
]


""" Sample_run_hidden holds json split format of "Known" columns:
"FlowCell","Index1","Index2","LIMS IUS SWID","LaneClusterPF","LaneClusterRaw",
"LaneNumber","LaneYield","QualityScoreSum","ReadNumber","Run","RunNumber","SampleID",
"SampleName","SampleNumberReads","SampleYield","TrimmedBases","Yield","YieldQ30"

 pruned_unknown_hidden holds json split format of "unknown" columns:
 "Count","LaneNumber","Index1","Index2","Run","LIMS IUS SWID
 """

def dataversion():
    return DATAVERSION

def layout(qs):
    return html.Div(
        children=[
            core.Dropdown(
                id=ids["run_select"],
                #   Options is concantenated string versions of all_runs.
                options=[{"label": r, "value": r} for r in all_runs],
                value=all_runs[0],
                clearable=False,
            ),
            core.Graph(id=ids["known_index_bar"]),
            html.Div(
                [
                    html.Div(
                        [
                            core.Graph(id=ids["known_unknown_pie"]),
                            core.Textarea(
                                id=ids["known_fraction"],
                                style={"width": "100%"},
                                readOnly=True,
                                # This is the textbox at the bottom, hover over to see title
                                title=(
                                    "Assumptions are made about which indexes are known "
                                    "or unknown. This is due to multiple bcl2fastq analyses "
                                    "being used on one run. This number should be 100%."
                                ),
                            ),
                        ],
                        style={"width": "25%", "display": "inline-block"},
                    ),
                    html.Div(
                        [core.Graph(id=ids["unknown_index_bar"])],
                        style={"width": "75%", "display": "inline-block", "float": "right"},
                    ),
                ]
            ),
            html.Br(),
            core.Tabs(id=ids['tabs_data_table'], children=[
                core.Tab(label='Known Barcodes', children=[
                    dash_table.DataTable(
                        id=ids["known_data_table"],
                        columns=KNOWN_DATA_TABLE_COLS,
                        export_format='csv',
                        export_headers='names',
                        sort_action='native',
                    )
                ]),
                core.Tab(label='Unknown Barcodes', children=[
                    dash_table.DataTable(
                        id=ids["unknown_data_table"],
                        columns=UNKNOWN_DATA_TABLE_COLS,
                        export_format='csv',
                        export_headers='names',
                        sort_action='native',
                    )
                ])
            ]),
        ]
    )


def init_callbacks(dash_app):
    @dash_app.callback(
        [
            Output(ids["known_index_bar"], "figure"),
            Output(ids["unknown_index_bar"], "figure"),
            Output(ids["known_unknown_pie"], "figure"),
            Output(ids["known_fraction"], "value"),
            Output(ids["known_data_table"], "data"),
            Output(ids["unknown_data_table"], "data")
        ],
        [
            Input(ids["run_select"], "value")
        ],
    )
    def update_layout(run_alias):
        """
        When input(run dropdown) is changed, known index bar, unknown index bar,
        piechart and textarea are updated

        Parameter:
            run_alias: user-selected run name from dropdown
        Returns:
            functions update_known_index_bar, update_unknown_index_bar,
            update_pie_chart's data value, and update_pie_chart's fraction value
        """

        run = index[index[index_col.Run] == run_alias]
        run = run[run[index_col.ReadNumber] == 1]
        run = run[~run[index_col.SampleID].isna()]
        run = run.drop_duplicates([index_col.SampleID, index_col.Lane])
        # TODO: Replace with join from Pinery (on Run, Lane, Index1, Index2)
        #  10X index (SI-GA-H11) will have to be converted to nucleotide
        run[COL_LIBRARY] = run[index_col.SampleID].str.extract(
            r"SWID_\d+_(\w+_\d+_.*_\d+_[A-Z]{2})_"
        )
        run[COL_INDEX] = run[index_col.Index1].str.cat(
            run[index_col.Index2].fillna(""), sep=" "
        )

        pruned = gsiqcetl.bcl2fastq.prune_unknown_index_from_run(
            run_alias, index, unknown
        )
        pruned[COL_INDEX] = pruned[un_col.Index1].str.cat(
            pruned[un_col.Index2].fillna(""), sep=" "
        )
        pruned = pruned.sort_values(un_col.Count, ascending=False)

        total_clusters = gsiqcetl.bcl2fastq.total_clusters_for_run(
            run_alias, index
        )

        pie_data, textarea_fraction = create_pie_chart(run, pruned, total_clusters)

        return (
            create_known_index_bar(run),
            create_unknown_index_bar(pruned),
            pie_data,
            textarea_fraction,
            run.to_dict("records"),
            pruned.to_dict("records")
        )


def create_known_index_bar(run):
    """ Function to create known index bar according to user selected run
           Parameters:
               run: Dataframe filtered and cleaned by 'update_layout'
           Returns:
              data and values for the layout of stacked bar graph of sample indices
              creates bar graph "known_index_bar"
       """
    data_known = []
    #   Multiple libraries can use the same index, data must be grouped by both index and libraries
    #   to prevent duplicate counts
    for inx, d in run.groupby([COL_INDEX, COL_LIBRARY]):
        data_known.append(
            {
                "x": list(d[COL_LIBRARY].unique()),
                # One library can be run on multiple lanes. Sum them together.
                "y": [d[index_col.ReadCount].sum()],
                "type": "bar",
                "name": inx[0],
                "marker": {"line": {"width": 2, "color": "rgb(255,255, 255)"}},
            }
        )
    return {
        "data": data_known,
        "layout": {
            "barmode": "stack",
            "title": "Sample Indices",
            "xaxis": {"title": COL_LIBRARY, "automargin": True},
            "yaxis": {"title": "Clusters"},
        },
    }


def create_unknown_index_bar(pruned):
    """ Function to create unknown index bar  according to user selected run
            Parameters:
                pruned: Dataframe of unknown indices filtered and cleaned by 'update_layout'
            Returns:
                data and layout values for stacked bar graph for unknown indices
                creates unknown_index_bar bar graph
              """

    pruned = pruned.head(MAX_UNKNOWN_DISPLAY)

    data_unknown = []

    for lane, d in pruned.groupby(un_col.Lane):
        data_unknown.append(
            {
                "x": list(d[COL_INDEX]),
                "y": list(d[un_col.Count]),
                "type": "bar",
                "name": lane,
            }
        )
    return {
        "data": data_unknown,
        "layout": {
            "barmode": "stack",
            "title": "Unknown Indices",
            "xaxis": {"title": COL_INDEX},
            "yaxis": {"title": "Clusters"},
        },
    }


def create_pie_chart(run, pruned, total_clusters):
    """ Function to create pie chart and known fraction according to user selected run
             Parameters:
                  run: Dataframe filtered and cleaned by 'update_layout'
                  pruned: Dataframe of unknown indices filtered and cleaned by 'update_layout'
                  total_clusters: Denominator for known/unknown indices.
             Returns:
                  pie chart "known_unknown_pie" with known and unknown indices ratio over total cluster
                  creates value of known_fraction
     """
    known_count = run[index_col.ReadCount].sum()
    pruned_count = pruned[un_col.Count].sum()
    fraction = (known_count + pruned_count) / total_clusters * 100
    return (
        {
            "data": [
                {
                    "labels": ["Known", "Unknown"],
                    "values": [known_count, pruned_count],
                    "type": "pie",
                    "marker": {"colors": ["#349600", "#ef963b"]},
                }
            ],
            "layout": {"title": "Flow Cell Composition of Known/Unknown Indices"},
        },
        ("Predicted clusters / produced clusters: {}%".format(str(round(fraction, 1)))),
    )
