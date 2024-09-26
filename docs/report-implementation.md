# Report Implementation

Dashi is built on top of Dash, which is designed for single-page applications. To accomodate this limitation, we swap out page contents and URLs dynamically to mimic multiple pages. For more information on this process, please see [Architecture](./architecture.md). 

[known_pages_router.py](../application/dash_application/known_pages_router.py) provides a skeleton including the navbar, foot, and URL of a report (Dash considers the URL to be part of the layout object). Reports in Dashi therefore require specific functions to be implemented in each report in order for known_pages_router to hook in. 

## Required Elements
### Page Name & Title

Each report is known by two names, and they must be defined at the top of the python file.

```python
page_name = 'single-lane-tar'
title = "Single-Lane Targeted Sequencing"
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

**page_name** is used in the page URL.

**title** is the full name used for display within Dashi, eg in the navbar, Reports dropdown.

*Some legacy reports have file names that don't match their page_name. All new reports should have their page_name match their file name, aside from swapping '-' and '_'.

### ids Dictionary
Dash requires that any element with which a user will interact have a globally unique ID. Dashi includes utility functions to create globally unique IDs with only locally-unique names, to make this more manageable.

[dash_id.py](../application/dash_application/dash_id.py) has a function *init_ids()* which takes an array of strings and returns a dictionary mapping those strings to unique IDs which will be used under the hood. Store this dictionary under the name 'ids'.

```python
ids = init_ids([
    # Buttons
    'jira-issue-with-runs-button',
    'general-jira-issue-button',
    'update-button-top',
    'update-button-bottom',
    'approve-run-button',

    # Alerts
    "alerts-unknown-run",

    # Sidebar controls
    'all-runs',
    'run-id-list',
    'all-instruments',
    'instruments-list',
    'all-projects',
    'projects-list',
    "all-references",
    "references-list",
    'all-kits',
    'kits-list',
    'all-library-designs',
    'library-designs-list',
    'first-sort',
    'second-sort',
    'colour-by',
    'shape-by',
    'search-sample',
    'search-sample-ext',
    'show-data-labels',
    'show-all-data-labels',
    'insert-size-median-cutoff',
    'passed-filter-clusters-cutoff',
    "date-range",

    #Graphs
    "graphs",

    #Data table
    'failed-samples',
    'data-table',
    'failed-count',
    'data-count'
])
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

In the report layout and callbacks, elements are always referred to using `ids['element-name']`. **The exception** is the id 'url', which is defined once for all reports in known_pages_router.

### ALL sets and initial values dictionary

Each report will have multiple dropdowns, multi-selects, and threshold controls. Each of these elements requires that their initial contents be defined ahead of time, in the data pre-processing section of the report file. 

To enable the 'All Runs', 'All Projects', etc buttons, each set must be predefined. The constant set is passed to the element for display when defining layout or when updating the element in a callback. Similarly, the default initial value for thresholds, etc must be defined.

```python
# Build lists of attributes for sorting, shaping, and filtering on
ALL_PROJECTS = util.unique_set(bamqc, PINERY_COL.StudyTitle)
ALL_RUNS = util.unique_set(bamqc, PINERY_COL.SequencerRunName, True) # reverse order
ALL_KITS = util.unique_set(bamqc, PINERY_COL.PrepKit)
```

```python
shape_colour = ColourShapeSingleLane(
    ALL_PROJECTS, ALL_RUNS, ALL_KITS, ALL_TISSUE_MATERIALS, ALL_TISSUE_ORIGIN,
    ALL_LIBRARY_DESIGNS, ALL_REFERENCES,
)
# Add shape, colour, and size cols to dataframe 
bamqc = add_graphable_cols(bamqc, initial, shape_colour.items_for_df())

SORT_BY = sidebar_utils.default_first_sort + [
    {"label": "Total Clusters",
     "value": special_cols["Total Clusters (Passed Filter)"]},
    {"label": "Unmapped Reads",
     "value": special_cols["Unmapped Reads (%)"]},
```

```python
initial = get_initial_single_lane_values()

# Set additional initial values for dropdown menus
initial["second_sort"] = special_cols["Total Clusters (Passed Filter)"]
# Set initial values for graph cutoff lines
cutoff_pf_clusters_label = sidebar_utils.clusters_per_sample_cutoff_label
initial["cutoff_pf_clusters"] = 0.01
cutoff_insert_median_label = sidebar_utils.insert_median_cutoff_label
initial["cutoff_insert_median"] = 150
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)


### DATAVERSION
The `DATAVERSION` constant is required by known_pages_router for display in the footer of the page. This helps inform the user about the integrity of the QC data. This is retrieved from gsi-qc-etl via [df_manipulation.py](../application/dash_application/utility/df_manipulation.py)'s 'cache' object, eg `util.cache.versions(["bamqc4"])`.

### The Layout Function

The report layout is stored in a function so that known_pages_router can swap between different page's layouts, and pass values from the URL into it, to mimic page-based navigation.

The layout function gets passed information about the URL from known_pages_router, and opens with parsing the values from that string and overwrites default values with anything requested in the URL:

```python
def layout(query_string):
    query = sidebar_utils.parse_query(query_string)
    # initial runs: should be empty unless query requests otherwise:
    #  * if query.req_run: use query.req_run
    #  * if query.req_start/req_end: use all runs, so that the start/end filters will be applied
    if "req_runs" in query and query["req_runs"]:
        initial["runs"] = query["req_runs"]
    elif "req_start" in query and query["req_start"]:
        initial["runs"] = ALL_RUNS
        query["req_runs"] = ALL_RUNS  # fill in the runs dropdown
    if "req_projects" in query and query["req_projects"]:
        initial["projects"] = query["req_projects"]
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

The layout function then calls a utility function from [plot_builder.py](../application/dash_application/utility/plot_builder.py), based on whether the report is based on single-lane or call-ready data, which filters the dataframe based on the contents of the initial values dictionary. Note that said initial values may have just been overwritten by the process detailed above.

```python
df = reshape_single_lane_df(bamqc, initial["runs"], initial["instruments"], initial["projects"], initial["references"], initial["kits"], initial["library_designs"], initial["start_date"], initial["end_date"], initial["first_sort"], initial["second_sort"], initial["colour_by"], initial["shape_by"], shape_colour.items_for_df(), [])
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

The layout function returns the entire report layout as a nested Dash `Loading` layout element object. For an introduction to these objects see [the Dash tutorial on layouts](https://dash.plotly.com/layout), though note that Dashi requires this layout function rather than just a layout object. 

This object will make heavy use of [sidebar_utils.py](../application/dash_application/utility/sidebar_utils.py) to standardize the sidebar controls with the other reports.

```python
return core.Loading(fullscreen=True, type="dot", children=[
    html.Div(className='body', children=[
        html.Div(className="row jira-buttons", children=[
            sidebar_utils.jira_button("Open an issue",
                                        ids['general-jira-issue-button'],
                                        {"display": "inline-block"},
                                        sidebar_utils.construct_jira_link([], title)),
            sidebar_utils.jira_button("Open an issue about these runs",
                                        ids['jira-issue-with-runs-button'],
                                        {"display": "none"}, ""),
            sidebar_utils.unknown_run_alert(
                ids['alerts-unknown-run'],
                initial["runs"],
                ALL_RUNS
            ),
        ]),
        html.Div(className='row flex-container', children=[
            html.Div(className='sidebar four columns', children=[
                html.Button('Update', id=ids['update-button-top'], className="update-button"),
                sidebar_utils.approve_run_button(ids['approve-run-button']),
                html.Br(),
                html.Br(),
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

It's a good idea to use an existing report's layout as a reference for the order and functions to call to set up all the sidebar widgets and the graph and tables tabs:

Set up filter widgets on sidebar:
```python
# Filters
sidebar_utils.select_runs(ids["all-runs"],
    ids["run-id-list"], ALL_RUNS,
    query["req_runs"]),

sidebar_utils.run_range_input(ids["date-range"],
    query["req_start"],
    query["req_end"]),

sidebar_utils.hr(),

sidebar_utils.select_projects(ids["all-projects"],
    ids["projects-list"],
    ALL_PROJECTS,
    query["req_projects"]),
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Set up sorts, colour and shape selectors:
```python
# Sort, colour, and shape
sidebar_utils.select_first_sort(
    ids['first-sort'],
    initial["first_sort"],
    SORT_BY,
),

sidebar_utils.select_second_sort(
    ids['second-sort'],
    initial["second_sort"],
    SORT_BY,
),

sidebar_utils.select_colour_by(ids['colour-by'],
    shape_colour.dropdown(),
    initial["colour_by"]),
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Set up cutoff threshold widgets:
```python
# Cutoffs
sidebar_utils.cutoff_input(cutoff_pf_clusters_label,
    ids['passed-filter-clusters-cutoff'], initial["cutoff_pf_clusters"]),
    sidebar_utils.cutoff_input(cutoff_insert_median_label,
    ids['insert-size-median-cutoff'], initial["cutoff_insert_median"]),
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

When the sidebar is done, define the graphs and tables tabs and their contents. The graphs are programmatically generated from the `GRAPHS` list you will define in the 'Graph Generation' section. 

```python
# Graphs + Tables tabs
html.Div(className="seven columns", 
    children=[
        core.Tabs([
            # Graphs tab
            core.Tab(label="Graphs",
            children=[
                create_graph_element_with_subplots(ids["graphs"], df, initial, GRAPHS),
            ]),
            # Tables tab
            core.Tab(label="Tables",
            children=[
                table_tabs_single_lane(
                    ids["failed-samples"],
                    ids["data-table"],
                    ids["failed-count"],
                    ids["data-count"],
                    df,
                    ex_table_columns,
                    [
                        (cutoff_insert_median_label, BAMQC_COL.InsertMedian, initial["cutoff_insert_median"],
                        (lambda row, col, cutoff: row[col] < cutoff)),
                        (cutoff_pf_clusters_label,
                        special_cols["Total Clusters (Passed Filter)"], initial["cutoff_pf_clusters"],
                        (lambda row, col, cutoff: row[col] < cutoff)),
                    ]
                ),
            ])
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

### init_callbacks()
Every report requires a function with the signature `def init_callbacks(dash_app)`. This function will contain all of the Dash callbacks you will add in the Interaction section. known_pages_router uses this function to load callbacks from multiple pages at startup.

## Data Preprocessing

Add import functions to [df_manipulation.py](../application/dash_application/utility/df_manipulation.py) ("util") if necessary, then call this function to import your data into the report, and merge your data in a function at the top of your report file. This is generally the most complex and report-specific part of the report file. Custom merges require some [pandas](https://pandas.pydata.org/docs/) knowledge.

```python
bamqc_df = util.get_dnaseqqc_and_bamqc4()
bamqc_df = util.df_with_fastqc_data(bamqc_df, [BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes])

[...]

pinery_samples = util.get_pinery_samples()

bamqc_df = util.df_with_pinery_samples_ius(bamqc_df, pinery_samples, util.bamqc4_ius_columns)

bamqc_df = util.df_with_run_info(bamqc_df, PINERY_COL.SequencerRunName)

bamqc_df = util.filter_by_library_design(bamqc_df, util.ex_lib_designs)
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Single-Lane reports use 'ius' pinery function calls, and Call-Ready reports use 'merged' pinery function calls.

## Graph Generation

Every graph that will appear in your report needs a function defining it. These most often call utility functions in [plot_builder.py](../application/dash_application/utility/plot_builder.py), generally *SingleLaneSubplot()* or *CallReadySubplot()*. 

These functions standardize the look and feel of the Dashi graphs, and abstract out the logic needed to enforce the shared x-axis across the report. In general, the signatures of the utility functions ask the report developer to specify graph and y-axis titles, pass in the dataframe that's been manipulated by the update callback, and specify a lambda for calculating y-axis values.

```python
def generate_total_clusters(df, graph_params):
    return SingleLaneSubplot(
        "Total Clusters (Passed Filter)", # graph title
        df, # dataframe parameter
        lambda d: d[special_cols["Total Clusters (Passed Filter)"]], # y-axis calculation
        "# PF Clusters X 10^6", # y-axis title
        graph_params["colour_by"], 
        graph_params["shape_by"],
        graph_params["shownames_val"],
        cutoff_lines=[(cutoff_pf_clusters_label, graph_params["cutoff_pf_clusters"])]
    )
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

After all of your graph generation functions are defined, they need to go into a `GRAPHS` list. This list gets passed to a utility function in the layout definition which draws all the graphs in the list onto the page.

```python
GRAPHS = [
    generate_total_clusters,
    generate_deduplicated_coverage,
    generate_deduplicated_coverage_per_gb,
    generate_unmapped_reads,
    generate_nonprimary_reads,
    generate_on_target_reads,
    generate_median_insert_size,
]
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

## Interaction 

### collapsing_functions dictionary

A dictionary of string to lambda calling [log_utils.py](../application/dash_application/utility/log_utils.py)'s *collapse_if_all_selected()* called *collapsing_functions* is required for the sake of shortening the logs sent to Loki when users press the 'update' button on the sidebar. This function detects when the selected set is the same as the ALL set (defined in section above) and truncates the log line. This dictionary will be used in the update button's callback.

```python
# N.B. The keys in this object must match the argument names for
# the `update_pressed` function in the views.
collapsing_functions = {
    "projects": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_PROJECTS, "all_projects"),
    "runs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_RUNS, "all_runs"),
    "kits": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_KITS, "all_kits"),
    "instruments": lambda selected: log_utils.collapse_if_all_selected(selected, ILLUMINA_INSTRUMENT_MODELS, "all_instruments"),
    "library_designs": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_LIBRARY_DESIGNS, "all_library_designs"),
    "references": lambda selected: log_utils.collapse_if_all_selected(selected, ALL_REFERENCES, "all_references"),
}
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

### Dash callbacks
Dash provides interaction with layout elements using callback functions with annotations unique to Dash. These annotations use layout elements `id` attribute to refer to layout elements, which we previously set up using the `ids` dictionary. Dash then provides further attributes per element which can be read or written to, such as `value` or `options`. The general format is:

```python
@dash_app.callback(
    Output(id_of_element_1, 'attribute'),
    [Input(id_of_element_2, 'attribute')],
    [State(id_of_element_3, 'attribute')]
)
def callback_for_when_attribute_of_element_2_changes(
    element_2_attribute,
    element_3_attribute):
    # Do any logic you need, here
    return element_1_attribute_new_value
)
```

Each attribute of an element can only be *Output* by one callback, however a callback function may have unlimited Outputs, the Output line of the callback parameters just needs to be made a list like Input and State are. Input and State must be lists even if they only have one element, and they must have function parameters to map to. Dash does this in order from top to bottom. 

This function is run when *any* attribute name by an Input is changed, e.g. Button elements have an `n_clicks` attribute which increment when a button is pressed, this increment triggers the callback to run. 

States are used to get the current value of an attribute into the function's memory scope, however changes to these attributes in the browser do not trigger the callback.

More information on Dash callbacks is available at the [Dash Callbacks tutorial](https://dash.plotly.com/basic-callbacks) however please note that Dashi requires that all callbacks be defined inside the *init_callbacks* function you defined earlier, rather than at the root of the file.

`update_pressed` is the most significant callback in any Dashi report. It will trigger when either the top or bottom Update button on the sidebar is clicked, and it re-processes the preprocessed dataframe based on all of the filters used in the sidebar. It then Outputs all of the graphs, data tables, and visibility information for context-specific buttons. 

In the body of the update_pressed callback, the developer logs the filters currently selected for observability purposes, while passing in the previously defined `collapsing_functions` to keep long messages a reasonable length.

```python
log_utils.log_filters(locals(), collapsing_functions, logger)
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Then, the Highlighted Sample sets are merged, and [plot_builder.py](../application/dash_application/utility/plot_builder.py)'s `reshape_single_lane_df` or `reshape_call_ready_df` is called as appropriate, to apply all the filters selected in the sidebar to the dataframe:

```python
if searchsample and searchsampleext:
    searchsample += searchsampleext
elif not searchsample and searchsampleext:
    searchsample = searchsampleext
df = reshape_single_lane_df(bamqc, runs, instruments, projects, references, kits, library_designs, start_date, end_date, first_sort, second_sort, colour_by, shape_by, shape_colour.items_for_df(), searchsample)
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

`df` now contains properly adjusted data, which the developer can use to calculate failure table contents. [table_builder.py](../application/dash_application/utility/table_builder.py) contains utility functions for this purpose:

```python
(failure_df, failure_columns ) = cutoff_table_data_ius(df, [
    (cutoff_insert_median_label, BAMQC_COL.InsertMedian, insert_median_cutoff,
    (lambda row, col, cutoff: row[col] < cutoff)),
    (cutoff_pf_clusters_label, special_cols["Total Clusters (Passed "
        "Filter)"], total_clusters_cutoff,
    (lambda row, col, cutoff: row[col] < cutoff)),
])
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Calculate the set of samples which should now be available through the *Highlight Samples* dropdowns:

```python
new_search_sample = util.unique_set(df, PINERY_COL.SampleName)
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Values for JIRA buttons are also set up using [sidebar_utils.py](../application/dash_application/utility/sidebar_utils.py) and [df_manipulation.py](../application/dash_application/utility/df_manipulation.py)("util"):

```python
(jira_href, jira_style) = sidebar_utils.jira_display_button(runs, title)
```
Source: [single_lane_tar.py](../application/dash_application/views/single_lane_tar.py)

Finally, return all of the newly-transformed data as a list in the same order they're promised in the Output list in the callback annotation.

## Serving Your Report
known_pages_router uses [pages.py](../application/dash_application/pages.py) as a directory of all the pages it can load. On startup, Dashi iterates over the `pagenames` list, appending the names to `application.dash_application.views.`, and importing the module by name. This automatically performs the data processing at the top of your report, makes the URL able to be navigated to, makes Dashi aware of the layout function so it can be called, and loads all the callbacks into memory.

You report file must be in `dashi/application/dash_application/views` for pages to pick it up. Add your reports *file name* (not `page_name`) to the `pagenames` list. 