"""
bcl2barcode detects and counts the indices of a run as soon as possible. To link the
bcl2barcode indices to that of Pinery (in order to give the indices a name) the following
points need to be addressed:

* 10X index: Pinery stores the name of the group of indices (SI-GA-A1), whereas
bcl2barcode has the nucleotide sequence
* Index length: Pinery has the actual index. In case of pools with indices of different
lengths, bcl2barcode will have truncated indices (to min length)
* Single/dual index: Pinery has the full index sequence. In case of pools with single
and dual indices, bcl2barcode will onto contain the first index
* Mismatches: bcl2barcode does not correct index sequence if it differs slightly
from Pinery known index sequence
* Collisions: bcl2barcode index matching more than one Pinery index
"""

import os
from typing import List

import dash_html_components as html
import dash_core_components as core
import dash_table
from dash.dependencies import Input, Output
import numpy
import pandas

from ..utility import df_manipulation as util
from ..dash_id import init_ids

import gsiqcetl.column

page_name = "bcl2barcode-index-qc"
title = "Bcl2Barcode Index QC"

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


def count_mismatches(s1: str, s2: str) -> int:
    """
    Count mismatches between two strings. If different lengths, use shortest.

    Args:
        s1: First string
        s2: Second string

    Returns:

    """
    if pandas.isna(s1) or pandas.isna(s2):
        return numpy.nan

    return sum(x[0] != x[1] for x in zip(s1, s2))


def find_matches(query: str, list_to_check: List[str], mismatches_allowed: int) -> List[str]:
    """
    Check for a match to a query string from a pool of strings. Allows for mismatches

    Args:
        query: The string to match against
        list_to_check: List of strings to match against query
        mismatches_allowed: How many mistmatches are allowed

    Returns:

    """
    result = []
    # Dealing with Pandas having NaN
    if type(list_to_check) == float:
        return result

    for check in list_to_check:
        if count_mismatches(query, check) <= mismatches_allowed:
            result.append(check)

    return result


def classify(row: pandas.Series) -> str:
    """
    Takes the various custom columns and decides if a bcl2barcode row contains
    known, unknown, or collision index.

    Args:
        row:

    Returns:

    """
    if row['IndexStrategy'] == 'SingleIndexOnly':
        if row['Index1MatchedCount'] == 0:
            return "Unknown"
        elif row['Index1MatchedCount'] == 1:
            return "Known"
        else:
            return "Collision"
    elif row['IndexStrategy'] == 'DualIndexOnly':
        if row['Index1MatchedCount'] == 0 or row['Index2MatchedCount'] == 0:
            return "Unknown"
        elif row['Index1MatchedCount'] == 1 and row['Index2MatchedCount'] == 1:
            return "Known"
        else:
            return "Collision"
    # Treat like Single Index
    elif row['IndexStrategy'] == 'MixedIndex':
        if row['Index1MatchedCount'] == 0:
            return "Unknown"
        elif row['Index1MatchedCount'] == 1:
            return "Known"
        else:
            return "Collision"
    else:
        raise ValueError('Unknown index strategy: {}'.format(row['IndexStrategy']))


DATAVERSION = util.cache.versions(["bcl2barcode"])
bcl2barcode = util.get_bcl2barcode()
bcl2barcode_run_summary = util.get_bcl2barcode_run_summary()
bcl2barcode_col = gsiqcetl.column.Bcl2BarcodeColumn
bcl2barcode_run_summary_col = gsiqcetl.column.Bcl2BarcodeRunSummaryColumn
pinery = util.get_pinery_samples()
PINERY_COL = util.PINERY_COL
# This needs to match what is set during de-multiplexing
BCL2FASTQ_MISMATCH = 1

barcode_expansions = pandas.read_csv(os.getenv("BARCODES_STREXPAND"), sep="\t", header=None).melt(id_vars=0).drop(labels="variable", axis="columns").set_axis(['Index', 'Sequence'], axis="columns", copy=False)
# Expand pinery to include 4 rows for every 1 10X barcode
# This allows for merging with the nucleotide sequence in bcl2barcode
pinery_with_expanded_barcodes = pandas.merge(pinery, barcode_expansions, left_on='iusTag', right_on='Index', how='left')

# Where there is no 10X barcode, fill in with the iusTag
pinery_with_expanded_barcodes['Sequence'] = pinery_with_expanded_barcodes['Sequence'].fillna(pinery_with_expanded_barcodes['iusTag'])

# Split up Index 1 and 2 into their own columns
# Allows for explicit merging on Index1 (single index) or Index1/2 (dual index)
pinery_with_expanded_barcodes['Index1'] = pinery_with_expanded_barcodes['Sequence'].fillna(pinery_with_expanded_barcodes['iusTag'])
pinery_with_expanded_barcodes['Index2'] = pinery_with_expanded_barcodes['Index1'].apply(lambda s: numpy.nan if len(s.split("-")) == 1 else s.split("-")[1])
pinery_with_expanded_barcodes['Index1'] = pinery_with_expanded_barcodes['Index1'].apply(lambda s: s.split("-")[0])
pinery_with_expanded_barcodes.loc[pinery_with_expanded_barcodes['Index1'] == 'NoIndex', 'Index1'] = numpy.nan

# Remove Pinery records that don't have Index 1 or Index 2
pinery_with_expanded_barcodes = pinery_with_expanded_barcodes[~(pinery_with_expanded_barcodes['Index1'].isna() & pinery_with_expanded_barcodes['Index1'].isna())]

# Collect all expected Index1 and Index2 for each Run/Lane
# These will be the ground truth against which bcl2barcode sequences will be compared
index1_expected = pinery_with_expanded_barcodes.groupby([PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber])['Index1'].apply(lambda x: list(set(x))).reset_index()
index2_expected = pinery_with_expanded_barcodes.groupby([PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber])['Index2'].apply(lambda x: list(set(x))).reset_index()

# Each Run/Lane can have one Index Strategy: Single Index, Dual Index
# Mixed lanes will be treated as Single Index
index2_expected['IndexStrategy'] = numpy.nan
index2_expected.loc[index2_expected['Index2'].apply(lambda x: all(pandas.isna(x))), 'IndexStrategy'] = 'SingleIndexOnly'
index2_expected.loc[index2_expected['Index2'].apply(lambda x: all(~pandas.isna(x))), 'IndexStrategy'] = 'DualIndexOnly'
index2_expected['IndexStrategy'] = index2_expected['IndexStrategy'].fillna('MixedIndex')

# Split up Index 1 and 2 into their own columns
# Allows for explicit merging on Index1 (single index) or Index1/2 (dual index)
bcl2barcode['Index1'] = bcl2barcode[bcl2barcode_col.Barcodes].apply(lambda s: s.split("-")[0])
bcl2barcode['Index2'] = bcl2barcode[bcl2barcode_col.Barcodes].apply(lambda s: numpy.nan if len(s.split("-")) == 1 else s.split("-")[1])

# Assign the expected Pinery indices to bcl2barcode
# If Pinery does not have that Run/Lane it will be excluded here
bcl2barcode = bcl2barcode.merge(
    index1_expected, how='inner',
    left_on=[bcl2barcode_col.Run, bcl2barcode_col.Lane],
    right_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber],
    suffixes=('', '_known')
)
bcl2barcode = bcl2barcode.merge(
    index2_expected, how='inner',
    left_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber],
    right_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber],
    suffixes=('', '_known')
)

# Expensive operation of matching bcl2barcode index to expected Pinery index
# After this, each bcl2barcode will have 0 or more indices matched to known Pinery index
bcl2barcode['Index1Matched'] = bcl2barcode.apply(lambda x: find_matches(x['Index1'], x['Index1_known'], BCL2FASTQ_MISMATCH), axis=1)
bcl2barcode['Index2Matched'] = bcl2barcode.apply(lambda x: find_matches(x['Index2'], x['Index2_known'], BCL2FASTQ_MISMATCH), axis=1)

# Count how many indices were matched and get their sequence
bcl2barcode['Index1MatchedCount'] = bcl2barcode['Index1Matched'].apply(len)
bcl2barcode['Index2MatchedCount'] = bcl2barcode['Index2Matched'].apply(len)
bcl2barcode['Index1MatchedSequence'] = bcl2barcode['Index1Matched'].apply(lambda x: x[0] if len(x) else '')
bcl2barcode['Index2MatchedSequence'] = bcl2barcode['Index2Matched'].apply(lambda x: x[0] if len(x) else '')

bcl2barcode["Classify"] = bcl2barcode.apply(classify, axis=1)

# bcl2barcode index is either unknown (no Pinery match), known (exactly one Pinery match), or collision (more than one Pinery match)
all_known = bcl2barcode[(bcl2barcode["Classify"] == "Known")]
# Sum all bcl2barcode counts that come from the same Pinery barcode
# Count of indices that differed slightly (BCL2FASTQ_MISMATCH) are collapsed here
all_known = all_known.groupby(
    [PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber, 'Index1MatchedSequence', 'Index2MatchedSequence', 'IndexStrategy']
)['count'].sum().reset_index()
all_known = all_known.rename(columns={
    'Index1MatchedSequence': 'Index1',
    'Index2MatchedSequence': 'Index2',
})

unknown_data_table = bcl2barcode[bcl2barcode["Classify"] == "Unknown"]

# Find known and unknown single index libraries
known_data_table_single = all_known[(all_known['IndexStrategy'] == 'SingleIndexOnly') | (all_known['IndexStrategy'] == 'MixedIndex')].merge(
    pinery_with_expanded_barcodes,
    how='left',
    left_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber, 'Index1'],
    right_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber, 'Index1'],
    suffixes=('', '_pinery'),
)
known_data_table = known_data_table_single[~known_data_table_single[PINERY_COL.StudyTitle].isna()]
unknown_data_table = pandas.concat([
    unknown_data_table,
    known_data_table_single[known_data_table_single[PINERY_COL.StudyTitle].isna()],
], join="inner")

known_data_table_dual = all_known[all_known['IndexStrategy'] == 'DualIndexOnly'].merge(
    pinery_with_expanded_barcodes,
    how='left',
    left_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber, 'Index1', 'Index2'],
    right_on=[PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber, 'Index1', 'Index2'],
    suffixes=('', '_pinery'),

)
known_data_table = pandas.concat([
    known_data_table,
    known_data_table_dual[~known_data_table_dual['studyTitle'].isna()]
])
unknown_data_table = pandas.concat([
    unknown_data_table,
    known_data_table_dual[known_data_table_dual[PINERY_COL.StudyTitle].isna()],
], join="inner")

# Don't display second index if Single Index library
unknown_data_table.loc[unknown_data_table['IndexStrategy'] == "SingleIndexOnly", 'Index2'] = numpy.nan
unknown_data_table['Sequence'] = unknown_data_table['Index1'].str.cat(unknown_data_table['Index2'], sep='-')
unknown_data_table['Sequence'] = unknown_data_table['Sequence'].fillna(unknown_data_table['Index1'])

all_runs = known_data_table[PINERY_COL.SequencerRunName].sort_values(ascending=False).unique()


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
        known_run = known_data_table[known_data_table[PINERY_COL.SequencerRunName] == run_alias]
        known_run = known_run[~known_run[PINERY_COL.SampleProvenanceID].isna()]
        
        unknown_run = unknown_data_table[unknown_data_table[PINERY_COL.SequencerRunName] == run_alias]
        # unknown_run = unknown_run[~unknown_run[PINERY_COL.SampleProvenanceID].isna()]

        return (
            create_known_index_bar(known_run),
            create_unknown_index_bar(unknown_run),
            create_pie_chart(run_alias),
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
    for i, d in run.groupby(['Sequence', PINERY_COL.SampleName]):
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
            # dtick ensures tick mark labels aren't elided
            # https://stackoverflow.com/questions/42187139/plotly-horizontal-bar-display-all-y-axis-labels
            "xaxis": {"title": "Library", "automargin": True, "dtick": 1},
            "yaxis": {"title": "Clusters"},
            "showlegend": True,
            "height": 600,
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

    for lane, d in run.groupby(PINERY_COL.LaneNumber):
        data.append({
            "x": list(d['Sequence']),
            "y": list(d[bcl2barcode_col.Count]),
            "type": "bar",
            "name": lane
        })
    
    return {
        "data": data,
        "layout": {
            "barmode": "stack",
            "title": "Unknown Indices",
            "xaxis": {"title": "Index", "automargin": True},
            "yaxis": {"title": "Clusters"},
            "showlegend": True
        },
    }


def create_pie_chart(run_alias):
    known_count = known_data_table[known_data_table[PINERY_COL.SequencerRunName] == run_alias][bcl2barcode_col.Count].sum()
    # bcl2barcode data doesn't include long tail of low-count barcodes. Get total from run summary to restore
    unknown_count = bcl2barcode_run_summary.loc[bcl2barcode_run_summary[bcl2barcode_run_summary_col.Run] == run_alias][bcl2barcode_run_summary_col.TotalClusters].sum() - known_count       
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

