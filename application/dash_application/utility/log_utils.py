from collections import Counter
from typing import List

import datetime
import logging
import json

compare = lambda s, t: Counter(s) == Counter(t)

def collapse_if_all_selected(selected_items: List[str], all_items: List[str], all_title: str) -> List[str]:
    if compare(selected_items, all_items):
        return [all_title] # Array for the sake of consistency 
    else:
        return selected_items


def collapse_all_params(params, collapsing_functions):
    """ Iterate over params values and simplify them if possible """
    for key in collapsing_functions.keys():
        params[key] = collapsing_functions[key](params[key])
    return params


def log_filters(params, collapsing_functions, logger):
    collapse_all_params(params, collapsing_functions)
    del params['click']
    if datetime.datetime.strptime(params['end_date'].split("T")[0], '%Y-%m-%d').date() == datetime.date.today():
        del params['end_date']
    logger.info(json.dumps(params))