import datetime
import re
import urllib.parse
from typing import List, Dict

import dash_core_components as core
import dash_html_components as html
from dash.exceptions import PreventUpdate
from pandas import DataFrame, Series

import pinery.column
from . import df_manipulation as df_tools


PINERY_COL = pinery.column.SampleProvenanceColumn
ALL_RUNS = df_tools.get_runs()

def frange(range_min, range_max, step):
    given_range = []
    i = range_min
    while i <= range_max:
        given_range.append(round(i, 2))
        i += step
    return given_range


def percentage_of(data, numerator_col, denominator_col):
    return (data[numerator_col] / data[denominator_col]) * 100


def select_with_select_all(select_all_text: str, select_all_id: str,
        all_label_text: str, all_id: str, all_items: List[str]) -> core.Loading:
    return core.Loading(type="circle", children=[
        html.Button(select_all_text, id=select_all_id, className="inline"),
        html.Label([
            all_label_text,
            core.Dropdown(
                id=all_id,
                options=[{"label": x, "value": x} for x in all_items],
                multi=True)
        ])
    ])


def select_runs(all_runs_id: str, runs_id: str, runs: List[str]) -> \
        core.Loading:
    return select_with_select_all("All Runs", all_runs_id, "Filter by Runs",
                                  runs_id, runs)


def run_range_input(run_range_id: str, start_date: str = None, end_date: str = None) -> html.Label:
    start = start_date if start_date else ALL_RUNS[pinery.column.RunsColumn.StartDate].min(skipna=True)
    end = end_date if end_date else datetime.date.today()
    return html.Label(["Filter by Run Start Date:",
                       html.Br(),
                       core.DatePickerRange(id=run_range_id,
                                            day_size=50,
                                            min_date_allowed=start,
                                            start_date=start,
                                            max_date_allowed=end,
                                            end_date=end,
                                            initial_visible_month=end,
                                            display_format="YYYY-MMM-DD"),
                       html.Br(),
                       ])


def runs_in_range(start_date: str, end_date: str) -> Series:
    allowed_runs = ALL_RUNS[(ALL_RUNS[pinery.column.RunsColumn.StartDate] >=
                          start_date) & (
        ALL_RUNS[pinery.column.RunsColumn.CompletionDate] <= end_date)]
    return allowed_runs[pinery.column.RunsColumn.Name]


def select_instruments(all_instruments_id: str, instruments_id: str,
                       instruments: List[str]) -> core.Loading:
    return select_with_select_all("All Instruments", all_instruments_id,
                                  "Filter by Instruments", instruments_id,
                                  instruments)


def select_projects(all_projects_id: str, projects_id: str, projects: List[
        str]) -> core.Loading:
    return select_with_select_all("All Projects", all_projects_id,
                                  "Filter by Projects", projects_id, projects)


def select_kits(all_kits_id: str, kits_id: str, kits: List[str]) -> \
        core.Loading:
    return select_with_select_all("All Kits", all_kits_id, "Filter by Kits",
                                  kits_id, kits)


def select_library_designs(all_library_designs_id: str, library_designs_id:
        str, library_designs: List[str]) -> core.Loading:
    return select_with_select_all("All Library Designs",
                                  all_library_designs_id,
                                  "Filter by Library Designs",
                                  library_designs_id, library_designs)


default_first_sort = [
    {"label": "Project",
     "value": PINERY_COL.StudyTitle},
    {"label": "Run",
     "value": PINERY_COL.SequencerRunName}
]


def select_first_sort(first_sort_id: str, selected_value: str,
        first_sort_options: List[Dict]=default_first_sort) -> html.Label:
    return html.Label([
        "Sort:",
        core.Dropdown(id=first_sort_id,
                      options = first_sort_options,
                      value=selected_value,
                      searchable=False,
                      clearable=False
        )
    ])


def select_second_sort(second_sort_id: str, selected_value: str,
                       second_sort_options: List[Dict]) -> html.Label:
    return html.Label([
        "Second Sort:",
        core.Dropdown(id=second_sort_id,
                      options=second_sort_options,
                      value=selected_value,
                      searchable=False,
                      clearable=False)
    ])


def select_colour_by(colour_by_id: str, colour_by_options: List[Dict],
                     selected_value: str) -> html.Label:
    return html.Label([
        "Colour by:",
        core.Dropdown(id=colour_by_id,
                      options=colour_by_options,
                      value=selected_value,
                      searchable=False,
                      clearable=False
                      )
    ])


def select_shape_by(shape_by_id: str, shape_by_options: List[Dict],
                    selected_value: str) -> html.Label:
    return html.Label([
        "Shape By:",
        core.Dropdown(id=shape_by_id,
                      options=shape_by_options,
                      value=selected_value,
                      searchable=False,
                      clearable=False
                      )
    ])


def highlight_samples_input(search_samples_id: str, all_samples: List[str]) -> \
        html.Label:
    return html.Label([
        "Highlight Samples:",
        core.Dropdown(id=search_samples_id,
                      options=[{'label': x, 'value': x} for x in all_samples],
                      multi=True
                      )
    ])


def show_names_input(show_names_id: str, selected_value: str) -> html.Label:
    return html.Label([
        "Show Names:",
        core.Dropdown(id=show_names_id,
                      options=[
                          {'label': 'Group ID', 'value': PINERY_COL.GroupID},
                          {'label': 'Kit', 'value': PINERY_COL.PrepKit},
                          {'label': 'Run', 'value': PINERY_COL.SequencerRunName},
                          {'label': 'Sample', 'value': PINERY_COL.SampleName},
                          {'label': 'Tissue Origin', 'value': PINERY_COL.TissueOrigin},
                          {'label': 'Tissue Preparation', 'value': PINERY_COL.TissuePreparation},
                          {'label': 'Tissue Type', 'value': PINERY_COL.TissueType},
                      ],
                      value=selected_value,
                      searchable=False,
                      multi=True,
        )
    ])


def cutoff_input(cutoff_label: str, cutoff_id: str, cutoff_value) -> \
        html.Label:
    return html.Label([
        cutoff_label,
        html.Br(),
        core.Input(id=cutoff_id,
                   type="number",
                   min=0,
                   value=cutoff_value)
    ])


def total_reads_cutoff_input(cutoff_id: str, cutoff_value) -> html.Label:
    return cutoff_input("Passed Filter Reads (* 10^6) cutoff",
                        cutoff_id, cutoff_value)


def insert_mean_cutoff(cutoff_id: str, cutoff_value) -> html.Label:
    return cutoff_input("Mean Insert Size cutoff", cutoff_id, cutoff_value)


def hr() -> html.Hr:
    # Horizontal rule
    return html.Hr(style={"margin": "1rem"})


def parse_query_string(query):
    return urllib.parse.parse_qs(query)


def get_requested_run_date_range(last_string) -> List[str]:
    xdays = re.compile(r'(\d+)days').match(last_string)
    if xdays and xdays.group(1):
        days_ago = int(xdays.group(1))
        end = datetime.date.today()
        start = end - datetime.timedelta(days=days_ago)
        return [start, end]
    else:
        return [None, None]


def parse_run_date_range(query) -> List[str]:
    query_dict = parse_query_string(query[1:]) # slice off the leading question mark
    if "last" in query_dict:
        return get_requested_run_date_range(query_dict["last"][0])
    else:
        return [None, None]

