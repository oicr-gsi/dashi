import dash_html_components as html
import dash_core_components as core
import dash_table
from dash.dependencies import Input, Output
import pandas
import os

from ..utility import df_manipulation as util
from ..dash_id import init_ids

import gsiqcetl.bcl2barcode
import gsiqcetl.column
import pdb

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

def expand(b):
  return barcode_expansions.get(b, [b])

def maybe_index2(s):
    try:
        return s.split("-")[1]
    except IndexError:
        return ""

# There can be many unknown indices in each run. Only display top N
MAX_UNKNOWN_DISPLAY = 30

DATAVERSION = util.cache.versions(["bcl2barcode"])
bcl2barcode = util.get_bcl2barcode()
bcl2barcode_col = gsiqcetl.column.Bcl2BarcodeColumn
pinery = util.get_pinery_samples()
PINERY_COL = util.PINERY_COL

barcode_expansions = pandas.DataFrame(columns=['Index', 'Sequence'])
with open(os.getcwd() + "/application/dash_application/assets/expand_index.strexpand", 'r') as strexpand:
    for l in strexpand.readlines():
        x = l.split("\t")
        for i in range(1,5):
            barcode_expansions = barcode_expansions.append({'Index': x[0], 'Sequence': x[i].replace("\n", "")}, ignore_index=True)

pdb.set_trace()
pinery_with_expanded_barcodes = pandas.merge(pinery, barcode_expansions, left_on='iusTag', right_on='Index', how='left')
pinery_with_expanded_barcodes = pinery_with_expanded_barcodes['Sequence'].fillna(pinery_with_expanded_barcodes['iusTag'])

bcl2barcode_with_pinery = pandas.merge(bcl2barcode, pinery_with_expanded_barcodes, left_on='Run Alias', right_on='sequencerRunName', how='left')
bcl2barcode_with_pinery['Index1'] = bcl2barcode_with_pinery['Sequence'].apply(lambda s: s.split("-")[0])
bcl2barcode_with_pinery['Index2'] = bcl2barcode_with_pinery['Sequence'].apply(lambda s: maybe_index2(s))



# for tenx_barcode in barcode_expansions.keys():
#     print(tenx_barcode)
#     new_row = bcl2barcode_with_pinery.loc[bcl2barcode_with_pinery[bcl2barcode_col.Barcodes] == tenx_barcode]
#     if new_row.empty: continue
#     for new_index in expand(tenx_barcode):
#         print(new_index)
#         new_row_copy = new_row.copy(deep=True)
#         pdb.set_trace()
#         new_row_copy['Index1'] = new_index
#         new_row_copy[bcl2barcode_col.Barcodes] = new_index
#         bcl2barcode_with_pinery.append(new_row_copy)
#     bcl2barcode_with_pinery = bcl2barcode_with_pinery[bcl2barcode_with_pinery[bcl2barcode_col.Barcodes] != tenx_barcode]
# print("All done!")

unknown_data_table = bcl2barcode_with_pinery.loc[bcl2barcode_with_pinery['studyTitle'].isnull()]
known_data_table = bcl2barcode_with_pinery.loc[bcl2barcode_with_pinery['studyTitle'].notnull()]

all_runs = known_data_table[bcl2barcode_col.Run].sort_values(ascending=False).unique()

KNOWN_DATA_TABLE_COLS = [

]

UNKNOWN_DATA_TABLE_COLS = [

]

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
        known_run = known_data_table[known_data_table[bcl2barcode_col.Run] == run_alias]
        known_run = known_run[~known_run[bcl2barcode_col.FileSWID].isna()]
        known_run = known_run.drop_duplicates([bcl2barcode_col.FileSWID, bcl2barcode_col.Lane])
        
        unknown_run = unknown_data_table[unknown_data_table[bcl2barcode_col.Run] == run_alias]
        unknown_run = unknown_run[~unknown_run[bcl2barcode_col.FileSWID].isna()]
        unknown_run = unknown_run.drop_duplicates([bcl2barcode_col.FileSWID, bcl2barcode_col.Lane])

        pie_data, textarea_fraction = create_pie_chart(known_run, unknown_run)

        return (
            create_known_index_bar(known_run),
            create_unknown_index_bar(unknown_run),
            pie_data,
            textarea_fraction,
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
    for i, d in run.groupby([bcl2barcode_col.Barcodes, PINERY_COL.SampleName]):
        data.append({
            "x": list(d[PINERY_COL.SampleName].unique()),
            "y": d[bcl2barcode_col.Count],
            "type": "bar",
            "name": i[0],
            "marker": {"line": {"width": 2, "color": "rgb(255,255, 255)"}},
        })
    
    return {
        "data": data,
        "layout": {
            "barmode": "stack",
            "title": "Sample Indices",
            "xaxis": {"title": "Sample", "automargin": True},
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
    fraction = 100 ##idk what you want from me

    
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
        },
        ("Predicted clusters / produced clusters: {}%".format(str(round(fraction, 1)))),
    )

