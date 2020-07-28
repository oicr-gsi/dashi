import importlib

prefix = "application.dash_application.views."

# An array of module names as strings, one per page
# These are for the modules that Dash can graph
pagenames = [
    # "bamqc_gbovertime",
    # "bamqc_overtime",
    "bcl2barcode",
    "call_ready_ts",
    "call_ready_rna",
    "call_ready_wgs",
    # "poolqc",
    "single_lane_ts",
    "single_lane_rna",
    "single_lane_wgs",
    # "rnaseqc",
    # "runreport",
    # "runscanner",
    "SARS-CoV-2",
    'single_lane_cfmedip'
]

# Please do not edit this array
# https://media2.giphy.com/media/DkaZuJGcwwN32/200.webp?cid=790b761109288a37049d763e1175d0e4ca6307eee3351333&rid=200.webp
pages = []

# Please do not edit this loop
for name in pagenames:
    pages.append(importlib.import_module(prefix + name))

# TODO: Maybe move the user-defined array to another file and import it into a scarier-sounding file
