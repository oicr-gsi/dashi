import importlib

prefix = 'application.dash_application.'

# Please create array of module names as string, one per page
# e.g., pagenames = ['myPage', 'myPage2']
pagenames = [
    'bcl2fastq'
]

# Please do not edit this array
pages = []

# Please do not edit this loop
for name in pagenames:
    pages.append(importlib.import_module(prefix + name))

# TODO: Maybe move the user-defined array to another file and import it into a scarier-sounding file