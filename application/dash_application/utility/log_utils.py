from collections import Counter

import datetime
import logging
import json

compare = lambda s, t: Counter(s) == Counter(t)

# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: sidebar_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: sidebar_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: sidebar_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: sidebar_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: sidebar_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
}

def collapse_if_all_selected(selected_items: List[str], all_items: List[str], all_title: str) -> List[str]:
    if compare(selected_items, all_items):
        return [all_title]
    else:
        return selected_items


def collapse_all_params(params):
    """ Iterate over params values and simplify them if possible """
    for key in collapsing_functions.keys():
        params[key] = collapsing_functions[key](params[key])
    return params


def log_filters(params, logger):
    collapse_all_params(params)
    del params['click']
    if datetime.datetime.strptime(params['end_date'], '%Y-%m-%d').date() == datetime.date.today():
        del params['end_date']
    logger.info(json.dumps(params))