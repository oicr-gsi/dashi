import importlib

prefix = 'application.dash_application.'

pagenames = [
    'dash_multipage_index',
    'dash_multipage_1',
    'dash_multipage_2',
    'dash_multipage_3'
]

pages = []

for name in pagenames:
    pages.append(importlib.import_module(prefix + name))
