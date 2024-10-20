import datetime
import re
import urllib.parse
import json
import os
from typing import List, Dict, Union, Any

from dash import dcc as core
from dash import html
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from pandas import Series, Timestamp

import pinery.column
import gsiqcetl.column
from . import df_manipulation as df_tools

insert_mean_cutoff_label = "Mean Insert Size minimum"
insert_median_cutoff_label = "Median Insert Size minimum"
percent_duplication_cutoff_label = "% Duplication maximum"
clusters_per_sample_cutoff_label = "Clusters per Sample (* 10^6) minimum"
rrna_contamination_cutoff_label = "rRNA Contamination maximum"


PINERY_COL = pinery.column.SampleProvenanceColumn
RUNS_COL = pinery.column.RunsColumn
COMMON_COL = gsiqcetl.column.ColumnNames
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
        all_label_text: str, all_id: str, all_items: List[str],
        preselected: List[str] = [], help_link = None) -> core.Loading:
    help_button = None
    if help_link:
        help_button = html.A(href=help_link, className="helpbutton", target="_blank", children="📖")
    return core.Loading(type="circle", children=[
        html.Button(select_all_text, id=select_all_id, className="inline"),
        html.Label([
            all_label_text,
            help_button,
            core.Dropdown(
                id=all_id,
                options=[{"label":x, "value":x} for x in all_items],
                value=preselected,
                multi=True)
        ])
    ])


def select_runs(all_runs_id: str, runs_id: str, runs: List[str], requested_runs: List[str]) -> core.Loading:
    return select_with_select_all("All Runs", all_runs_id,
                                  "Filter by Runs", runs_id,
                                  runs, requested_runs)


def start_and_end_dates(start_date: str = None, end_date: str = None):
    start = start_date if start_date else ALL_RUNS[pinery.column.RunsColumn.StartDate].min(skipna=True)
    end = end_date if end_date else Timestamp.today(tz="UTC")
    return (start, end)


def run_range_input(run_range_id: str, start_date: str=None, end_date: str=None) -> html.Label:
    return html.Label(["Filter by Run Start Date:",
                       html.Br(),
                       core.DatePickerRange(id=run_range_id,
                                            day_size=50,
                                            min_date_allowed=start_date,
                                            start_date=start_date,
                                            max_date_allowed=end_date,
                                            end_date=end_date,
                                            initial_visible_month=end_date,
                                            display_format="YYYY-MMM-DD",
                                            clearable=True),
                       html.Br(),
                       ])


def runs_in_range(start_date: str, end_date: str) -> Series:
    start, end = start_and_end_dates(start_date, end_date)
    allowed_runs = ALL_RUNS[(ALL_RUNS[pinery.column.RunsColumn.StartDate] >=
                          start) & (
        ALL_RUNS[pinery.column.RunsColumn.CompletionDate] <= end)]
    return allowed_runs[pinery.column.RunsColumn.Name]


def approve_run_button(approve_run_id: str) -> html.A:
    return html.A("View Run in MISO",
                  id=approve_run_id,
                  className="button approve-run",
                  target="_blank",
                  style={"display": "none"})


def approve_run_url(runs: List[str]):
    if len(runs) == 1:
        return [os.getenv("MISO_URL") + "run/alias/" + runs[0], {"display": "inline-block"}]

    else:
        return ["", {"display": "none"}]


def select_instruments(all_instruments_id: str, instruments_id: str,
                       instruments: List[str]) -> core.Loading:
    return select_with_select_all("All Instruments", all_instruments_id,
                                  "Filter by Instruments", instruments_id,
                                  instruments)


def select_projects(all_projects_id: str, projects_id: str, projects: List[
        str], requested_projects) -> core.Loading:
    return select_with_select_all("All Projects", all_projects_id,
                                  "Filter by Projects", projects_id, projects,
                                  requested_projects, os.getenv("MISO_URL") + "projects")


def select_reference(all_references_id: str, references_id: str, references: List[
    str]) -> core.Loading:
    return select_with_select_all("All References", all_references_id,
                                  "Filter by Reference", references_id, references)


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


def select_sample_types(all_sample_types_id: str, sample_types_id: str,
                        sample_types: List[str]) -> core.Loading:
    return select_with_select_all("All Sample Types",
                                  all_sample_types_id,
                                  "Filter by Sample Type",
                                  sample_types_id, sample_types)


def select_tissue_materials(all_tissue_materials_id: str, tissue_preps_id: str,
                            tissue_materials: List[str]) -> core.Loading:
    return select_with_select_all("All Tissue Materials",
                                  all_tissue_materials_id,
                                  "Filter by Tissue Material",
                                  tissue_preps_id, tissue_materials)


default_first_sort = [
    {"label": "Project",
     "value": PINERY_COL.StudyTitle},
    {"label": "Run",
     "value": PINERY_COL.SequencerRunName},
    {"label": "Reference",
     "value": COMMON_COL.Reference},
]


def select_first_sort(first_sort_id: str, selected_value: str,
        first_sort_options: List[Dict]=default_first_sort) -> html.Label:
    return html.Label([
        "Sort:",
        core.Dropdown(id=first_sort_id,
                      options=first_sort_options,
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


# GR-1065 is why this is disabled in call-ready graphs
def select_colour_by(colour_by_id: str, colour_by_options: List[Dict],
                     selected_value: str, disabled: bool=False) -> html.Label:
    return core.Loading(type="circle", children=[
        html.Label([
            "Colour by:",
            core.Dropdown(id=colour_by_id,
                      options=colour_by_options,
                      value=selected_value,
                      searchable=False,
                      clearable=False,
                      disabled=disabled
                      )
        ])
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
        "Highlight Samples by Sample Name:",
        core.Dropdown(id=search_samples_id,
                      options=[{'label': x, 'value': x} for x in all_samples],
                      multi=True
                      )
    ])

def highlight_samples_by_ext_name_input_single_lane(search_samples_ext_id: str, df) -> \
        html.Label:
    if df is None:
        return html.Label([
        "Highlight Samples by External Name:",
        core.Dropdown(id=search_samples_ext_id,
                      options=[],
                      multi=True
                      )
        ])
    return html.Label([
        "Highlight Samples by External Name:",
        core.Dropdown(id=search_samples_ext_id,
                      options= [{'label': d[PINERY_COL.ExternalName], 'value': d[PINERY_COL.SampleName]} for i, d in df[[PINERY_COL.ExternalName, PINERY_COL.SampleName]].iterrows()],
                      multi=True
                      )
    ])


def highlight_run(run_dropdown_id: str, all_runs: List[str]) -> html.Label:
    return html.Label([
        "Highlight Runs:",
        core.Dropdown(
            id=run_dropdown_id,
            options=[{'label': x, 'value': x} for x in all_runs],
            multi=True
        )
    ])


def _show_data_labels_input(show_names_id: str, selected_value: Union[None, str],
        select_all_text: str, select_all_id: str, options: List[dict]
) -> core.Loading:
    return core.Loading(type="circle", children=[
        html.Button(select_all_text, id=select_all_id, className="inline"),
        html.Label([
            "Show Data Labels",
            core.Dropdown(
                id=show_names_id,
                options=options,
                value=selected_value,
                searchable=False,
                multi=True,
            )
        ])
    ])


def show_data_labels_input_single_lane(
        show_names_id: str, selected_value: Union[None, str],
        select_all_text: str, select_all_id: str) -> core.Loading:
    return _show_data_labels_input(show_names_id, selected_value,
        select_all_text, select_all_id, [
            {'label': 'External Name', 'value': PINERY_COL.ExternalName},
            {'label': 'Group ID', 'value': PINERY_COL.GroupID},
            {'label': 'Kit', 'value': PINERY_COL.PrepKit},
            {'label': 'Reference', 'value': COMMON_COL.Reference},
            {'label': 'Run', 'value': PINERY_COL.SequencerRunName},
            {'label': 'Sample', 'value': PINERY_COL.SampleName},
            {'label': 'Tissue Origin', 'value': PINERY_COL.TissueOrigin},
            {'label': 'Tissue Preparation', 'value': PINERY_COL.TissuePreparation},
            {'label': 'Tissue Type', 'value': PINERY_COL.TissueType},
            {'label': 'Run Start Date', 'value': RUNS_COL.StartDate},
            {'label': 'Run End Date', 'value': RUNS_COL.CompletionDate},
        ])


def show_data_labels_input_call_ready(show_names_id: str,
        selected_value: Union[None, str], select_all_text: str,
        select_all_id: str) -> core.Loading:
    return _show_data_labels_input(show_names_id, selected_value,
        select_all_text, select_all_id, [
            {'label': 'External Name', 'value': PINERY_COL.ExternalName},
            {'label': 'Reference', 'value': COMMON_COL.Reference},
            {'label': 'Group ID', 'value': PINERY_COL.GroupID},
            {'label': 'Sample', 'value': PINERY_COL.RootSampleName},
            {'label': 'Library Design', 'value': PINERY_COL.LibrarySourceTemplateType},
            {'label': 'Tissue Preparation', 'value': PINERY_COL.TissuePreparation},
            {'label': 'Tissue Origin', 'value': PINERY_COL.TissueOrigin},
            {'label': 'Tissue Type', 'value': PINERY_COL.TissueType},
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


def parse_query(query) -> Dict[str, Any]:
    query_dict = parse_query_string(query[1:])  # slice off the leading question mark
    queries = {
        "req_start": None,
        "req_end": None,
        "req_runs": [],
        "req_projects": []
    }
    if "last" in query_dict:
        queries["req_start"], queries["req_end"] = get_requested_run_date_range(query_dict["last"][0])
    if "run" in query_dict:
        queries["req_runs"] = query_dict["run"]
    if "project" in query_dict:
        queries["req_projects"] = query_dict["project"]
    return queries


def jira_button(button_text: str, button_id: str, style: Dict, href: str) -> html.A:
    return html.A(button_text,
                  id=button_id,
                  className="button",
                  target="_blank",
                  style=style,
                  href=href)


def construct_jira_link_general(description, summary="") -> str:
    # JIRA requires a login, so we make all JIRA URLs a login with a self-redirect
    parameters = {
        "summary": summary,
        "issuetype": 3,
        "pid": 11684,
        "priority": 10000,
        "labels": "dashi",
        "description": description
    }

    root_parameters = {
        "permissionViolation": "true",
        "page_caps": "",
        "user_role": "",
        "os_destination": "/secure/CreateIssueDetails!init.jspa?" + urllib.parse.urlencode(parameters)
    }
    return "https://jira.oicr.on.ca/login.jsp?" + urllib.parse.urlencode(root_parameters)


def construct_jira_link(runs, page_name) -> str:
    description = "Report: " + page_name + "\n"
    if runs:
        description += "Runs: " + ", ".join(str(run) for run in runs)

    return construct_jira_link_general(description)


def jira_display_button(runs: List[str], page_title: str):
    """ Don't display "File a ticket about these runs" button if more than 100 runs are selected.
     This prevents an HTTP 400 "Request Header Too Large" error """
    if 0 < len(runs) <= 100:
        return [construct_jira_link(runs, page_title),
                {"display": "inline-block"}]
    else:
        return ["", {"display": "none"}]


def update_only_if_clicked(click):
    """ Callbacks fire on page load, which can be a problem if the callback is on a button
    which hasn't actually been clicked. If the button hasn't been clicked, raise an error
    to cancel further action in this callback. """
    if click is None: raise PreventUpdate

def miso_qc_button(body_id, button_id):
    """
    Different IDs for the HTTP body and the button (for controlling visibility) are required.
    """
    return html.Form(children=[
        core.Input(id=body_id, type="hidden", name="data", value=json.dumps("{}")),
        
        # button text subject to change
        core.Input(id=button_id, value="QC in MISO", type="submit", className="miso-qc-button")
    ],
    method="POST",
    action=os.getenv("MISO_URL")+"runlibraries/metrics",
    target="_blank"
    )


def unknown_run_alert(alert_id: str, picked_runs: List[str], all_runs: List[str]):
    """
    Generate Alert HTML element if at least one user supplied run does not exist

    Args:
        alert_id: ID of Dash object
        picked_runs: The runs the user picked
        all_runs: All the available runs

    Returns:

    """
    unknown_runs = [x for x in picked_runs if x not in all_runs]
    return dbc.Alert(
        "No data for requested run(s): {}".format(', '.join(unknown_runs)),
        alert_id,
        color="danger",
        dismissable=True,
        is_open=len(unknown_runs) > 0
    )
