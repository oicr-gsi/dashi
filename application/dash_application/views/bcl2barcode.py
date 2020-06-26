import dash_html_components as html
import dash_core_components as core
import dash_table
from dash.dependencies import Input, Output
import numpy
import pandas
import os

from ..utility import df_manipulation as util
from ..dash_id import init_ids

import gsiqcetl.column

page_name = "bcl2barcode-index-qc"
title = "Bcl2Barcode Index QC - 🚧 WIP"

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


def trim(row, index_name, len_name):
    if pandas.isna(row[index_name]) or pandas.isna(row[len_name]):
        return numpy.nan

    return row[index_name][:int(row[len_name])]

DATAVERSION = util.cache.versions(["bcl2barcode"])
bcl2barcode = util.get_bcl2barcode()
bcl2barcode_col = gsiqcetl.column.Bcl2BarcodeColumn
pinery = util.get_pinery_samples()
PINERY_COL = util.PINERY_COL

barcode_expansions = pandas.read_csv(os.getenv("BARCODES_STREXPAND"), sep="\t", header=None).melt(id_vars=0).drop(labels="variable", axis="columns").set_axis(['Index', 'Sequence'], axis="columns", inplace=False)

# Expand pinery to include 4 rows for every 1 10X barcode
pinery_with_expanded_barcodes = pandas.merge(pinery, barcode_expansions, left_on='iusTag', right_on='Index', how='left')

# Where there is no 10X barcode, fill in with the iusTag
pinery_with_expanded_barcodes['Sequence'] = pinery_with_expanded_barcodes['Sequence'].fillna(pinery_with_expanded_barcodes['iusTag'])

# Split up Index 1 and 2 into their own columns
pinery_with_expanded_barcodes['Index1'] = pinery_with_expanded_barcodes['Sequence'].fillna(pinery_with_expanded_barcodes['iusTag'])
pinery_with_expanded_barcodes['Index2'] = pinery_with_expanded_barcodes['Index1'].apply(lambda s: numpy.nan if len(s.split("-")) == 1 else s.split("-")[1])
pinery_with_expanded_barcodes['Index1'] = pinery_with_expanded_barcodes['Index1'].apply(lambda s: s.split("-")[0])
pinery_with_expanded_barcodes.loc[pinery_with_expanded_barcodes['Index1'] == 'NoIndex', 'Index1'] = numpy.nan

# Remove Pinery records that don't have Index 1 or Index 2
pinery_with_expanded_barcodes = pinery_with_expanded_barcodes[~(pinery_with_expanded_barcodes['Index1'].isna() & pinery_with_expanded_barcodes['Index1'].isna())]

# Calculate mininum index length per run/lane
min_index1_length = pinery_with_expanded_barcodes.groupby(['sequencerRunName', 'laneNumber'])['Index1'].apply(lambda x: x.str.len().min()).reset_index().rename(columns={'Index1': 'Index1 min length'})
min_index2_length = pinery_with_expanded_barcodes.groupby(['sequencerRunName', 'laneNumber'])['Index2'].apply(lambda x: x.str.len().min()).reset_index().rename(columns={'Index2': 'Index2 min length'})
pinery_with_expanded_barcodes = pinery_with_expanded_barcodes.merge(min_index1_length, how='left')
pinery_with_expanded_barcodes = pinery_with_expanded_barcodes.merge(min_index2_length, how='right')

# Trim each index to the minimum length for that lane
pinery_with_expanded_barcodes['Index1 Trimmed'] = pinery_with_expanded_barcodes.apply(lambda x: trim(x, 'Index1', 'Index1 min length'), axis=1)
pinery_with_expanded_barcodes['Index2 Trimmed'] = pinery_with_expanded_barcodes.apply(lambda x: trim(x, 'Index2', 'Index2 min length'), axis=1)

# For bcl2barcode, split Index 1 and 2, add Pinery mininum index lengths, and trim
bcl2barcode['Index1'] = bcl2barcode['Barcodes'].apply(lambda s: s.split("-")[0])
bcl2barcode['Index2'] = bcl2barcode['Barcodes'].apply(lambda s: numpy.nan if len(s.split("-")) == 1 else s.split("-")[1])
bcl2barcode = bcl2barcode.merge(
    min_index1_length,
    how='left',
    left_on=['Run Alias', 'Lane Number'],
    right_on=['sequencerRunName', 'laneNumber']
)
bcl2barcode = bcl2barcode.merge(
    min_index2_length,
    how='left',
    left_on=['Run Alias', 'Lane Number'],
    right_on=['sequencerRunName', 'laneNumber'],
    suffixes=['', '_del']
)
bcl2barcode = bcl2barcode.drop(['sequencerRunName_del', 'laneNumber_del'], axis=1)

bcl2barcode['Index1 Trimmed'] = bcl2barcode.apply(lambda x: trim(x, 'Index1', 'Index1 min length'), axis=1)
bcl2barcode['Index2 Trimmed'] = bcl2barcode.apply(lambda x: trim(x, 'Index2', 'Index2 min length'), axis=1)

# Get single and dual index info using trimmed index
pinery_single_index = pinery_with_expanded_barcodes[pinery_with_expanded_barcodes['Index2'].isna()]
single_index = bcl2barcode.merge(
    pinery_single_index, how='left',
    right_on=['sequencerRunName', 'laneNumber', 'Index1 Trimmed'],
    left_on=['sequencerRunName', 'laneNumber', 'Index1 Trimmed'],
    suffixes=('', "_pinery")
)

# Unknown barcodes will have all Pinery columns NaN. Picked study title to check
known = single_index[~single_index['studyTitle'].isna()]
unknown = single_index[single_index['studyTitle'].isna()][bcl2barcode.columns]

pinery_dual_index = pinery_with_expanded_barcodes[~pinery_with_expanded_barcodes['Index2'].isna()]
dual_index = bcl2barcode.merge(
    pinery_dual_index, how='left',
    right_on=['sequencerRunName', 'laneNumber', 'Index1 Trimmed', 'Index2 Trimmed'],
    left_on=['sequencerRunName', 'laneNumber', 'Index1 Trimmed', 'Index2 Trimmed'],
    suffixes=('', "_pinery")
)
known_dual_index = dual_index[~dual_index['studyTitle'].isna()]

dual_unknown = dual_index[dual_index['studyTitle'].isna()][bcl2barcode.columns]

# Use inner merge to find barcode that are unknown in both single and dual index
unknown_data_table = unknown.merge(
    dual_unknown,
    how="inner",
    left_on=["Barcodes", "Lane Number", "Run Alias"],
    right_on=["Barcodes", "Lane Number", "Run Alias"],
    suffixes=("", "_y")
)

# TODO: This may contain duplicates (one from single the other from dual index)
#  Have warning if one bcl2barcode is assigned to multiple libraries
known_data_table = pandas.concat([known, known_dual_index])
all_runs = known_data_table[bcl2barcode_col.Run].sort_values(ascending=False).unique()

KNOWN_DATA_TABLE_COLS = [
    {"name": "Library", "id": PINERY_COL.SampleName},
    {"name": "Index 1", "id": "Index1"},
    {"name": "Index 2", "id": "Index2"},
    {"name": "Library PF Clusters", "id": bcl2barcode_col.Count},
    {"name": "Lane", "id": PINERY_COL.LaneNumber},
    # {"name": "Lane PF Clusters", "id": "LaneClusterPF"},
]

UNKNOWN_DATA_TABLE_COLS = [
    {"name": "Index 1", "id": "Index1"},
    {"name": "Index 2", "id": "Index2"},
    {"name": "Count", "id": bcl2barcode_col.Count},
    {"name": "Lane", "id": bcl2barcode_col.Lane},
]

def dataversion():
    return DATAVERSION

def layout(qs):
    return html.Div(
        children=[
            core.Dropdown(
                id=ids["run_select"],
                #   Options is concatenated string versions of all_runs.
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
        known_run = known_data_table[known_data_table[bcl2barcode_col.Run] == run_alias]
        known_run = known_run[~known_run[PINERY_COL.SampleProvenanceID].isna()]
        
        unknown_run = unknown_data_table[unknown_data_table[bcl2barcode_col.Run] == run_alias]
        # unknown_run = unknown_run[~unknown_run[PINERY_COL.SampleProvenanceID].isna()]

        return (
            create_known_index_bar(known_run),
            create_unknown_index_bar(unknown_run),
            create_pie_chart(known_run, unknown_run),
            known_run.to_dict("records"),
            unknown_run.to_dict("records")
        )


def create_known_index_bar(run):
    """ Function to create known index bar according to user selected run
           Parameters:
               run: Dataframe filtered and cleaned by 'update_layout'
           Returns:
              data and values for the layout of stacked bar graph of sample indices
              creates bar graph "known_index_bar"
       """
    data = []
    # TODO: Show Barcodes from Pinery to avoid showing dual index if single index library
    for i, d in run.groupby(['Barcodes', PINERY_COL.SampleName]):
        data.append({
            "x": list(d[PINERY_COL.SampleName].unique()),
            # One library can be run on multiple lanes. Sum them together.
            "y": [d[bcl2barcode_col.Count].sum()],
            "type": "bar",
            "name": i[0],
            "marker": {"line": {"width": 2, "color": "rgb(255,255, 255)"}},
        })
    
    return {
        "data": data,
        "layout": {
            "barmode": "stack",
            "title": "Sample Indices",
            "xaxis": {"title": "Library", "automargin": True},
            "yaxis": {"title": "Clusters"},
            "showlegend": True
        },
    }


def create_unknown_index_bar(run):
    """ Function to create unknown index bar  according to user selected run
            Parameters:
                pruned: Dataframe of unknown indices filtered and cleaned by 'update_layout'
            Returns:
                data and layout values for stacked bar graph for unknown indices
                creates unknown_index_bar bar graph
              """
    run = run.sort_values(bcl2barcode_col.Count, ascending=False)
    run = run.head(30)
    data = []

    for lane, d in run.groupby(bcl2barcode_col.Lane):
        data.append({
            "x": list(d[bcl2barcode_col.Barcodes]),
            "y": list(d[bcl2barcode_col.Count]),
            "type": "bar",
            "name": lane
        })
    
    return {
        "data": data,
        "layout": {
            "barmode": "stack",
            "title": "Unknown Indices",
            "xaxis": {"title": "Index"},
            "yaxis": {"title": "Clusters"},
            "showlegend": True
        },
    }


def create_pie_chart(known_run, unknown_run):
    """ Function to create pie chart and known fraction according to user selected run
             Parameters:
                  run: Dataframe filtered and cleaned by 'update_layout'
                  pruned: Dataframe of unknown indices filtered and cleaned by 'update_layout'
                  total_clusters: Denominator for known/unknown indices.
             Returns:
                  pie chart "known_unknown_pie" with known and unknown indices ratio over total cluster
                  creates value of known_fraction
     """
    known_count = known_run[bcl2barcode_col.Count].sum() ##Is sum() needed now?
    unknown_count = unknown_run[bcl2barcode_col.Count].sum()
    
    return (
        {
            "data": [
                {
                    "labels": ["Known", "Unknown"],
                    "values": [known_count, unknown_count],
                    "type": "pie",
                    "marker": {"colors": ["#349600", "#ef963b"]},
                }
            ],
            "layout": {"title": "Flow Cell Composition of Known/Unknown Indices"},
        }
    )

