from typing import Dict, List, Tuple

import dash_core_components as core
import dash_html_components as html
import dash_table as tabl
import numpy
from pandas import DataFrame
import pinery


def build_table(table_id: str, columns: List[str], df: DataFrame, filter_on:
                str):
    # Filter out records with NA values in the given column (should indicate
    # we have no QC data for these records
    df = df[~df[filter_on].isna()]
    return tabl.DataTable(
        id=table_id,
        columns=[{"name": col, "id": col} for col in columns],
        data=df.to_dict('records'),
        export_format="csv",
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ],
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold"
        }
    )


def cutoff_table_data(data: DataFrame, limits: List[Tuple[str, str, float, bool
]]) -> Tuple[DataFrame, List[Dict[str, str]]]:
    output = []
    for _, row in data.iterrows():
        failures = {}
        has_failures = False
        for (name, column, cutoff, fail_below) in limits:
            if numpy.isnan(row[column]):
                failures[name] = "Missing"
                has_failures = True
            elif (fail_below and row[column] < cutoff) or (
                    not fail_below and row[column] > cutoff):
                failures[name] = "Failed ({0:.3f})".format(row[column])
                has_failures = True
            else:
                failures[name] = "Passed ({0:.3f})".format(row[column])
        if has_failures:
            failures[pinery.column.SampleProvenanceColumn.SampleName] = row[
                pinery.column.SampleProvenanceColumn.SampleName]
            failures[pinery.column.SampleProvenanceColumn.SequencerRunName] = row[
                pinery.column.SampleProvenanceColumn.SequencerRunName]
            failures[pinery.column.SampleProvenanceColumn.LaneNumber] = row[
                pinery.column.SampleProvenanceColumn.LaneNumber]
            failures[pinery.column.SampleProvenanceColumn.IUSTag] = row[pinery.column.SampleProvenanceColumn.IUSTag]
            output.append(failures)

    return (DataFrame(output), [{"name": pinery.column.SampleProvenanceColumn.SampleName,
                                 "id": pinery.column.SampleProvenanceColumn.SampleName},
                                {"name": pinery.column.SampleProvenanceColumn.SequencerRunName,
                                 "id": pinery.column.SampleProvenanceColumn.SequencerRunName},
                                {"name": pinery.column.SampleProvenanceColumn.LaneNumber,
                                 "id": pinery.column.SampleProvenanceColumn.LaneNumber},
                                {"name": pinery.column.SampleProvenanceColumn.IUSTag,
                                 "id": pinery.column.SampleProvenanceColumn.IUSTag},
                                *({"name": "%s (%d)" % (name, cutoff),
                                   "id": name} for (name, _, cutoff, _
                                                    ) in limits)])


def cutoff_table(table_id: str, data: DataFrame, limits: List[Tuple[str, str,
                                                                    float,
                                                                    bool]]):
    (failure_df, columns) = cutoff_table_data(data, limits)
    return tabl.DataTable(
        id=table_id,
        columns=columns,
        data=failure_df.to_dict('records'),
        export_format="csv",
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            },
            *({
                "if": {"column_id": name, "filter_query": "{%s} contains 'Failed'" % name},
                "backgroundColor": "mistyrose"

            } for (name, *_) in limits),
            *({
                "if": {"column_id": name, "filter_query": "{%s} = 'Missing'" % name},
                "backgroundColor": "papayawhip"

            } for (name, *_) in limits),
        ],
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold"
        }
    )


def table_tabs(failed_id: str, data_id: str, empty_data: DataFrame, table_columns: List[str], filter_on: str,
               limits: List[Tuple[str, str, float, bool]]):
    return core.Tabs(
        [
            core.Tab(
                label="Failed Samples",
                children=[
                    html.Div(
                        className='data-table',
                        children=[
                            cutoff_table(
                                failed_id,
                                empty_data,
                                limits)]),
                ]),
            core.Tab(
                label="Raw Data",
                children=[
                    html.Div(
                        className='data-table',
                        children=[
                            build_table(
                                data_id,
                                table_columns,
                                empty_data,
                                filter_on)]),
                ])])
