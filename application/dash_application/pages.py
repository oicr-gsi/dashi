import importlib

prefix = 'application.dash_application.'

# Array of module names as string, one per page
pagenames = [
]

pages = []

for name in pagenames:
    pages.append(importlib.import_module(prefix + name))
