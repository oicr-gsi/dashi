import importlib

prefix = "application.dash_application.views."

# An array of module names as strings, one per page
# These are for the modules that Dash can graph
pagenames = [
    "bamqc_gbovertime",
    "bamqc_overtime",
    "bcl2fastq",
    "poolqc",
    "rnaseqc",
    "runreport",
    "runscanner",
]

# Please do not edit this array
pages = []

# Please do not edit this loop
for name in pagenames:
    pages.append(importlib.import_module(prefix + name))

# TODO: Maybe move the user-defined array to another file and import it into a scarier-sounding file
