from typing import Callable, Dict, List, Tuple

from dash import dcc as core
from dash import html
from dash import dash_table as tabl
from pandas import DataFrame
import pinery
from .Mode import Mode
import logging

logger = logging.getLogger(__name__)

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
    '''
    `limits` lambdas are used to calculate what is INCLUDED in the table, ie what has FAILED, not what has passed.
    '''
    ius_cols = [
        pinery.column.SampleProvenanceColumn.SampleName,
        pinery.column.SampleProvenanceColumn.SequencerRunName,
        pinery.column.SampleProvenanceColumn.LaneNumber,
        pinery.column.SampleProvenanceColumn.IUSTag]
    return _calculate_cutoff_table_data(data, limits, ius_cols)


def cutoff_table_data_merged(data: DataFrame, limits: List[Tuple[str, str, Callable
]]) -> Tuple[DataFrame, List[Dict[str, str]]]:
    '''
    `limits` lambdas are used to calculate what is INCLUDED in the table, ie what has FAILED, not what has passed.
    '''
    merged_cols = [
        pinery.column.SampleProvenanceColumn.StudyTitle,
        pinery.column.SampleProvenanceColumn.RootSampleName,
        pinery.column.SampleProvenanceColumn.GroupID,
        pinery.column.SampleProvenanceColumn.LibrarySourceTemplateType,
        pinery.column.SampleProvenanceColumn.TissueOrigin,
        pinery.column.SampleProvenanceColumn.TissueType]
    return _calculate_cutoff_table_data(data, limits, merged_cols)

def _calculate_cutoff_table_data(data: DataFrame, limits: List[Tuple[str, str, Callable
]], cols_to_add: List[str]) -> Tuple[DataFrame, List[Dict[str, str]]]:
    output = []
    for _, row in data.iterrows():
        failures = {}
        has_failures = False
        for (name, column, cutoff, fail_fn) in limits:
            if fail_fn is None:
                failures[name] = "Passed ({:.3f})".format(row[column])
            else:
                maybe_failed = fail_fn(row, column, cutoff)
                if maybe_failed is None:
                    failures[name] = "N/A"  # should happen when e.g. cutoff is for tumour but sample is normal
                elif maybe_failed:
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


def printable_cutoff(cutoff) -> str:
    # Previously this tested 'if cutoff', however a cutoff of 0 would fail the test
    if type(cutoff) == float or type(cutoff) == int:
        return "{:.3f}".format(cutoff)
    else:
        return "No valid cutoff given"


def cutoff_table(table_id: str, data: DataFrame, limits: List[Tuple[str, str,
                                                                    float,
                                                                    bool]], mode):
    if mode == Mode.IUS:
        (failure_df, columns) = cutoff_table_data_ius(data, limits)
    elif mode == Mode.MERGED:
        (failure_df, columns) = cutoff_table_data_merged(data, limits)
    else:
        logger.error("Unrecognized Mode in cutoff_table: {0}".format(mode))
        raise NotImplementedError
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


def _table_tabs(failed_id: str, all_id: str, data_id: str, failed_count_id, all_count_id, data_count_id, empty_data: DataFrame, all_columns: List[str], table_columns: List[str],
               limits: List[Tuple[str, str, float, bool]], mode):
    return core.Tabs(id=failed_id+data_id+"tabs",
        children=[
            core.Tab(
                id=failed_id+"_tab",
                label="Failed Samples",
                children=[
                    html.Div(
                        className='data-table',
                        children=[
                            cutoff_table(
                                failed_id,
                                empty_data,
                                limits,
                                mode)]),
                    html.Br(),
                    html.P(id=failed_count_id, children=["Rows: {0}".format(len(empty_data.index))])
                ]),
            core.Tab(
                id=all_id+"_tab",
                label="All Samples",
                children=[
                    html.Div(
                        className='data-table',
                        children=[
                            build_table(
                                all_id,
                                all_columns,
                                empty_data)]),
                    html.Br(),
                    html.P(id=all_count_id, children=["Rows: {0}".format(len(empty_data.index))])
                ]),
            core.Tab(
                id=data_id+"_tab",
                label="🐌 Raw Data 🐌",
                children=[
                    html.Div(
                        className='data-table',
                        children=[
                            build_table(
                                data_id,
                                table_columns,
                                empty_data)]),
                    html.Br(),
                    html.P(id=data_count_id, children=["Rows: {0}".format(len(empty_data.index))])
                ])])

def table_tabs_single_lane(failed_id: str, all_id: str, data_id: str, failed_count_id, all_count_id, row_count_id, empty_data: DataFrame, all_columns: List[str], table_columns: List[str],
               limits: List[Tuple[str, str, float, bool]]):
    return _table_tabs(failed_id, all_id, data_id, failed_count_id, all_count_id, row_count_id, empty_data, all_columns, table_columns, limits, Mode.IUS)

def table_tabs_call_ready(failed_id: str, all_id: str, data_id: str, failed_count_id, all_count_id, row_count_id, empty_data: DataFrame, all_columns: List[str], table_columns: List[str],
               limits: List[Tuple[str, str, float, bool]]):
    return _table_tabs(failed_id, all_id, data_id, failed_count_id, all_count_id, row_count_id, empty_data, all_columns, table_columns, limits, Mode.MERGED)
