import urllib.parse

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash.dependencies as dep

import gsiqcetl.load
from gsiqcetl.bcl2fastq.constants import SamplesSchema, UnknownIndexSchema
import gsiqcetl.bcl2fastq.utility


index = gsiqcetl.load.bcl2fastq_known_samples(SamplesSchema.v1)
index_col = gsiqcetl.load.bcl2fastq_known_samples_columns(SamplesSchema.v1)

unknown = gsiqcetl.load.bcl2fastq_unknown_index(UnknownIndexSchema.v1)
un_col = gsiqcetl.load.bcl2fastq_unknown_index_columns(UnknownIndexSchema.v1)

all_runs = index[index_col.Run].sort_values(ascending=False).unique()

COL_LIBRARY = "library"
COL_INDEX = "index"

""" Sample_run_hidden holds json split format of "Known" columns:
"FlowCell","Index1","Index2","LIMS IUS SWID","LaneClusterPF","LaneClusterRaw",
"LaneNumber","LaneYield","QualityScoreSum","ReadNumber","Run","RunNumber","SampleID",
"SampleName","SampleNumberReads","SampleYield","TrimmedBases","Yield","YieldQ30"

 pruned_unknown_hidden holds json split format of "unknown" columns:
 "Count","LaneNumber","Index1","Index2","Run","LIMS IUS SWID
 """


def generate_layout(qs) -> html.Div:
    """
    Within the main layout division there are 3 groups:
    1. Top: Bar graphs showing each known index count
    2. Bottom left: Pie chart and text box
        a) Pie chart shows proportion of known and unknown indices
        b) Text box measures how well multiple analyses were combined (see
            below)
    3. Bottom right: Bar graph breaking down count of each unknown index

    In many instances, multiple bcl2fastq analyses are performed for one run. It
    is necessary to combine them to obtain meaningful statistics of unknown
    indices, but due to one run combining single/dual and different length
    indices, the calculations do have to make certain assumptions. The ratio
    displayed in the text box is of the calculated read count divided by the
    machine produced read count.

    Args:
        qs: The query string that modifying the layout. "run" parameter sets
        the run selected on layout load

    Returns: The Div of the complete layout with the defaults set from the
        passed query string

    """

    if qs:
        qs = qs[1:]

    qs = urllib.parse.parse_qs(qs)

    if "run" in qs and qs["run"][0] in all_runs:
        default_run = qs["run"][0]
    else:
        default_run = all_runs[0]

    return html.Div(
        children=[
            dcc.Dropdown(
                id="run_select",
                #   Options is concantenated string versions of all_runs.
                options=[{"label": r, "value": r} for r in all_runs],
                value=default_run,
                clearable=False,
            ),
            dcc.Graph(id="known_index_bar"),
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(id="known_unknown_pie"),
                            dcc.Textarea(
                                id="known_fraction",
                                style={"width": "100%"},
                                readOnly=True,
                                # This is hover text
                                title="Assumptions are made about which indexes"
                                " are known or unknown. This is due to "
                                "multiple bcl2fastq analyses being used "
                                "on one run. This number should be 100%.",
                            ),
                        ],
                        style={"width": "25%", "display": "inline-block"},
                    ),
                    html.Div(
                        [dcc.Graph(id="unknown_index_bar")],
                        style={
                            "width": "75%",
                            "display": "inline-block",
                            "float": "right",
                        },
                    ),
                ]
            ),
        ]
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

    data_unknown = []
    for lane, d in pruned.groupby(un_col.LaneNumber):
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
            "layout": {
                "title": "Flow Cell Composition of Known/Unknown Indices"
            },
        },
        (
            "Predicted clusters / produced clusters: {}%".format(
                str(round(fraction, 1))
            )
        ),
    )


def assign_callbacks(app: dash.Dash):
    @app.callback(
        [
            dep.Output("known_index_bar", "figure"),
            dep.Output("unknown_index_bar", "figure"),
            dep.Output("known_unknown_pie", "figure"),
            dep.Output("known_fraction", "value"),
        ],
        [dep.Input("run_select", "value")],
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
        run = run.drop_duplicates([index_col.SampleID, index_col.LaneNumber])
        # TODO: Replace with join from Pinery (on Run, Lane, Index1, Index2)
        #  10X index (SI-GA-H11) will have to be converted to nucleotide
        run[COL_LIBRARY] = run[index_col.SampleID].str.extract(
            r"SWID_\d+_(\w+_\d+_.*_\d+_[A-Z]{2})_"
        )
        run[COL_INDEX] = run[index_col.Index1].str.cat(
            run[index_col.Index2].fillna(""), sep=" "
        )

        pruned = gsiqcetl.bcl2fastq.utility.prune_unknown_index_from_run(
            run_alias, index, unknown
        )
        pruned[COL_INDEX] = pruned[un_col.Index1].str.cat(
            pruned[un_col.Index2].fillna(""), sep=" "
        )
        pruned = pruned.sort_values(un_col.Count, ascending=False)
        pruned = pruned.head(30)

        total_clusters = gsiqcetl.bcl2fastq.utility.total_clusters_for_run(
            run_alias, index
        )

        pie_data, textarea_fraction = create_pie_chart(
            run, pruned, total_clusters
        )

        return (
            create_known_index_bar(run),
            create_unknown_index_bar(pruned),
            pie_data,
            textarea_fraction,
        )


if __name__ == "__main__":
    import dash

    stand_alone = dash.Dash(__name__)
    stand_alone.layout = html.Div(
        [
            dcc.Location(id="url", refresh=False),
            html.Div(id="debug", children=[generate_layout(None)]),
        ]
    )
    assign_callbacks(stand_alone)

    @stand_alone.callback(
        dep.Output("debug", "children"), [dep.Input("url", "search")]
    )
    def query_string(search):
        return generate_layout(search)

    stand_alone.run_server(debug=True)
