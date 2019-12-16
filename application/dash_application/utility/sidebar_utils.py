from typing import List, Dict

import dash_core_components as core
import dash_html_components as html

import pinery.column

PINERY_COL = pinery.column.SampleProvenanceColumn


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
                                  all_library_designs_id, "Filter by Library "
                                  "Designs", library_designs_id,
                                  library_designs)


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
                          {'label': 'Sample', 'value': PINERY_COL.SampleName},
                          {'label': 'Group ID', 'value': PINERY_COL.GroupID},
                          {'label': 'None', 'value': 'none'}
                      ],
                      value=selected_value,
                      searchable=False,
                      clearable=False
        )
    ])
