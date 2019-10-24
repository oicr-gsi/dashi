import importlib

prefix = 'application.dash_application.'

pagenames = [
]

pages = []

for name in pagenames:
    pages.append(importlib.import_module(prefix + name))
