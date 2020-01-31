from typing import Dict, List, Tuple

import dash_core_components as core
import dash_html_components as html
import dash_table as tabl
import numpy
from pandas import DataFrame
import pinery


def build_table(table_id: str, columns: List[str], df: DataFrame):
    return tabl.DataTable(
        id=table_id,
        columns=[{"name": col, "id": col} for col in columns],
        data=df.to_dict('records'),
        export_format="csv",
        include_headers_on_copy_paste=True,
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


def cutoff_table_data_ius(data: DataFrame, limits: List[Tuple[str, str, float, bool
]]) -> Tuple[DataFrame, List[Dict[str, str]]]:
    ius_cols = [
        pinery.column.SampleProvenanceColumn.SampleName,
        pinery.column.SampleProvenanceColumn.SequencerRunName,
        pinery.column.SampleProvenanceColumn.LaneNumber,
        pinery.column.SampleProvenanceColumn.IUSTag]
    return _calculate_cutoff_table_data(data, limits, ius_cols)


def cutoff_table_data_merged(data: DataFrame, limits: List[Tuple[str, str, float, bool
]]) -> Tuple[DataFrame, List[Dict[str, str]]]:
    merged_cols = [
        pinery.column.SampleProvenanceColumn.RootSampleName,
        pinery.column.SampleProvenanceColumn.GroupID,
        pinery.column.SampleProvenanceColumn.LibrarySourceTemplateType,
        pinery.column.SampleProvenanceColumn.TissueOrigin,
        pinery.column.SampleProvenanceColumn.TissueType]
    return _calculate_cutoff_table_data(data, limits, merged_cols)

def _calculate_cutoff_table_data(data: DataFrame, limits: List[Tuple[str, str, float, bool
]], cols_to_add: List[str]) -> Tuple[DataFrame, List[Dict[str, str]]]:
    output = []
    for _, row in data.iterrows():
        failures = {}
        has_failures = False
        for (name, column, cutoff, fail_below) in limits:
            if cutoff is None:
                failures[name] = "Passed ({:.3f})".format(row[column])
            elif numpy.isnan(row[column]):
                failures[name] = "Missing"
                has_failures = True
            elif (fail_below and row[column] < cutoff) or (
                    not fail_below and row[column] > cutoff):
                failures[name] = "Failed ({:.3f})".format(row[column])
                has_failures = True
            else:
                failures[name] = "Passed ({:.3f})".format(row[column])
        if has_failures:
            for col in cols_to_add:
                failures[col] = row[col]
            output.append(failures)

    return (DataFrame(output), [{"name": col, "id": col} for col in cols_to_add]
                                +
                                [*({"name": "{} ({})".format(name,
                                                            printable_cutoff(
                                                                cutoff)),
                                   "id": name} for (name, _, cutoff, _
                                                    ) in limits)])


def printable_cutoff(cutoff: float) -> str:
    if cutoff:
        return "{:.3f}".format(cutoff)
    else:
        return "No valid cutoff given"


def cutoff_table(table_id: str, data: DataFrame, limits: List[Tuple[str, str,
                                                                    float,
                                                                    bool]]):
    (failure_df, columns) = cutoff_table_data_ius(data, limits)
    return tabl.DataTable(
        id=table_id,
        columns=columns,
        data=failure_df.to_dict('records'),
        export_format="csv",
        include_headers_on_copy_paste=True,
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


def table_tabs(failed_id: str, data_id: str, empty_data: DataFrame, table_columns: List[str],
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
                                empty_data)]),
                ])])
