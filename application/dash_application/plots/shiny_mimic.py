from typing import List, Dict, Callable, Union

import pandas
from pandas import DataFrame

import sd_material_ui

import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Output, Input, State
import dash.exceptions
import dash_table
import dash

from application.dash_application.plots.plot_scatter_subplot import create_subplot


class ShinyMimic:
    ID_BUTTON_OPTIONS = "options_button"
    ID_BUTTON_UPDATE = "update_button"
    ID_DATA_TABLE = "data_table"
    ID_DATE_PICKER = "date_picker"
    ID_DRAWER = "project_drawer"
    ID_LOADER_DATATABLE = "datatable_loader"
    ID_LOADER_GRAPH = "graph_loader"
    ID_MULTISELECT_KIT = "kit_multi_select"
    ID_MULTISELECT_PLOTS = "plots_multi_select"
    ID_MULTISELECT_PROJECT = "project_multi_select"
    ID_PLOT = "plot"
    ID_SELECT_COLOUR = "colour_by"
    ID_SELECT_SHAPE = "shape_by"

    def __init__(
        self,
        df: Callable[[], DataFrame],
        id_prefix: str,
        columns_to_plot: List[str],
        colour_columns: List[Dict[str, str]],
        shape_columns: List[Dict[str, str]],
        project_column_name: str,
        kit_column_name: str,
        date_column_name: str,
        library_column_name: str,
    ):
        self.df_func = df
        self.id_prefix = id_prefix
        self.columns_to_plot = columns_to_plot
        self.colour_columns = colour_columns
        self.shape_columns = shape_columns
        self.project_column_name = project_column_name
        self.kit_column_name = kit_column_name
        self.date_column_name = date_column_name
        self.library_column_name = library_column_name

    def get_sorted_column(self, column_name) -> list:
        return list(self.df_func()[column_name].sort_values().unique())

    def generate_id(self, name: str):
        return f"{self.id_prefix}_{name}"

    def generate_layout(
        self,
        n_plot_at_startup: int,
        default_colour_column: str,
        default_shape_column: str,
        data_table_columns: List[Dict[str, str]],
    ) -> html.Div:
        return html.Div(
            children=[
                self.generate_drawer_layout(
                    n_plot_at_startup,
                    default_colour_column,
                    default_shape_column,
                ),
                self.generate_main_window(data_table_columns),
            ]
        )

    def generate_drawer_layout(
        self,
        n_plot_at_startup: int,
        default_colour_column: str,
        default_shape_column: str,
    ) -> sd_material_ui.Drawer:
        return sd_material_ui.Drawer(
            id=self.id_drawer,
            open=False,
            docked=False,
            width="50%",
            children=[
                html.Div(
                    children=[
                        html.Label("Project:"),
                        core.Dropdown(
                            id=self.id_multiselect_project,
                            multi=True,
                            options=[
                                {"label": x, "value": x}
                                for x in self.get_sorted_column(
                                    self.project_column_name
                                )
                            ],
                            value=self.get_sorted_column(
                                self.project_column_name
                            ),
                        ),
                        html.Br(),
                        html.Label("Kits:"),
                        core.Dropdown(
                            id=self.id_multiselect_kit,
                            multi=True,
                            options=[
                                {"label": x, "value": x}
                                for x in self.get_sorted_column(
                                    self.kit_column_name
                                )
                            ],
                            value=self.get_sorted_column(self.kit_column_name),
                        ),
                        html.Br(),
                        html.Label("Dates: "),
                        core.DatePickerRange(
                            id=self.id_date_picker,
                            display_format="YYYY-MM-DD",
                            min_date_allowed=min(
                                self.df_func()[self.date_column_name]
                            ),
                            max_date_allowed=max(
                                self.df_func()[self.date_column_name]
                            ),
                            start_date=min(
                                self.df_func()[self.date_column_name]
                            ),
                            end_date=max(self.df_func()[self.date_column_name]),
                        ),
                        html.Br(),
                        html.Br(),
                        html.Label("Show Graphs:"),
                        core.Dropdown(
                            id=self.id_multiselect_plots,
                            multi=True,
                            options=[
                                {"label": x, "value": x}
                                for x in self.columns_to_plot
                            ],
                            value=self.columns_to_plot[:n_plot_at_startup],
                        ),
                        html.Br(),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Label("Colour by:"),
                                        core.Dropdown(
                                            id=self.id_select_colour,
                                            options=[
                                                {
                                                    "label": x["name"],
                                                    "value": x["id"],
                                                }
                                                for x in self.colour_columns
                                            ],
                                            value=default_colour_column,
                                        ),
                                    ],
                                    style={
                                        "width": "45%",
                                        "display": "inline-block",
                                    },
                                ),
                                html.Div(
                                    [
                                        html.Label("Shape by:"),
                                        core.Dropdown(
                                            id=self.id_select_shape,
                                            options=[
                                                {
                                                    "label": x["name"],
                                                    "value": x["id"],
                                                }
                                                for x in self.shape_columns
                                            ],
                                            value=default_shape_column,
                                        ),
                                    ],
                                    style={
                                        "width": "45%",
                                        "display": "inline-block",
                                        "float": "right",
                                    },
                                ),
                            ]
                        ),
                    ],
                    style={"margin": "23px"},
                )
            ],
        )

    def assign_callbacks(self, app: dash.Dash):
        @app.callback(
            Output(self.id_button_update, "n_clicks"),
            [Input(self.id_data_table, "data")],
            [State(self.id_button_update, "n_clicks")],
        )
        def click_update_graph_button(_data, n_clicks):
            """ A programmatic way to click the button when the data_table data
            changes, which causes the graphs to be rendered.

            This function is necessary because rendering the graphs when the
            data_table data changes does not work. See the rendering function
            for more details.

            Args:
                _data: Causes the button to be clicked, but not used
                n_clicks: The previous number of clicks on the button

            Returns: The incremented click number

            """
            n_clicks = 0 if n_clicks is None else n_clicks + 1
            return n_clicks

        @app.callback(
            Output(self.id_data_table, "data"),
            [Input(self.id_drawer, "open")],
            [
                State(self.id_multiselect_project, "value"),
                State(self.id_multiselect_kit, "value"),
                State(self.id_date_picker, "start_date"),
                State(self.id_date_picker, "end_date"),
            ],
        )
        def populate_data_table(
            drawer_open: bool,
            projects: List[str],
            kits: List[str],
            start_date: str,
            end_date: str,
        ):
            """
            Given the filtering options in the side drawer, create the data
            table with the filtered data.

            Args:
                drawer_open: Has the drawer been opened (False is it was closed)
                projects: Which projects to plot
                kits: Which kits to plot
                start_date: From which date to display (inclusive)
                end_date: Up to which date to display (inclusive)

            Returns: The data to put in the data table

            """
            if drawer_open:
                raise dash.exceptions.PreventUpdate(
                    "Drawer opening does not require recalculation"
                )

            to_table = self.df_func()[
                self.df_func()[self.project_column_name].isin(projects)
            ]
            to_table = to_table[to_table[self.kit_column_name].isin(kits)]
            to_table = to_table[
                to_table[self.date_column_name]
                >= pandas.to_datetime(start_date)
            ]
            to_table = to_table[
                to_table[self.date_column_name] <= pandas.to_datetime(end_date)
            ]

            return to_table.to_dict("records")

        @app.callback(
            Output(self.id_plot, "figure"),
            [Input(self.id_button_update, "n_clicks")],
            [
                State(self.id_data_table, "derived_virtual_data"),
                State(self.id_multiselect_plots, "value"),
                State(self.id_select_colour, "value"),
                State(self.id_select_shape, "value"),
                State(self.id_data_table, "sort_by"),
            ],
        )
        def graph_subplot(
            _clicks: int,
            data_to_plot: list,
            graphs: List[str],
            colour_by: str,
            shape_by: str,
            sort_by: Union[None, list],
        ):
            """
            Plots the data from the data table, preserving all sorting and
            filtering applied.

            The button that fires this callback had to be used. The simpler
            option would have been to fire it when the data table body is
            updated, but the `derived_virtual_data` property was linked to the
            body data and was not updated fast enough

            Args:
                _clicks: The click fires the callback, but is never used
                data_to_plot: This is the sorted and filtered data table data,
                    which will be used for plots
                graphs: Which columns to plot
                colour_by: The column that determines data colour
                shape_by: The column that determines data shape
                sort_by: The columns on which data is sorted. The content does
                    not matter for this function. If there is anything in this
                    variable, the data will be plotted in order it is found in
                    the input DataFrame

            Returns: The figures to plot

            """
            to_plot = pandas.DataFrame(data_to_plot)

            # The variable can be None or an empty list when no sorting is done
            order = True if sort_by else False

            if len(to_plot) > 0:
                return create_subplot(
                    to_plot,
                    graphs,
                    self.date_column_name,
                    self.library_column_name,
                    colour_by,
                    shape_by,
                    order,
                )
            else:
                return {}

        @app.callback(
            Output(self.id_drawer, "open"),
            [Input(self.id_button_options, "n_clicks")],
        )
        def open_project_drawer(n_clicks: Union[int, None]) -> bool:
            """
            Open the drawer when the Open Drawer button is clicked

            Args:
                n_clicks: How often has the button been clicked. None if it has
                    never been clicked

            Returns: Should the drawer be opened

            """
            # Do no open if the button has never been clicked, otherwise open
            return n_clicks is not None

    def generate_main_window(
        self, data_table_columns: List[Dict[str, str]]
    ) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    [
                        html.Div(
                            sd_material_ui.RaisedButton(
                                id=self.id_button_options, label="Options"
                            ),
                            style={"display": "inline-block"},
                        ),
                        html.Div(
                            sd_material_ui.RaisedButton(
                                id=self.id_button_update, label="Update Graphs"
                            ),
                            style={
                                "display": "inline-block",
                                "margin-left": "15px",
                            },
                        ),
                    ],
                    style={"margin-bottom": "5px"},
                ),
                core.Loading(
                    id=self.id_loader_graph,
                    children=[
                        sd_material_ui.Paper([core.Graph(id=self.id_plot)])
                    ],
                ),
                core.Loading(
                    id=self.id_loader_data_table,
                    children=[
                        sd_material_ui.Paper(
                            [
                                dash_table.DataTable(
                                    id=self.id_data_table,
                                    columns=data_table_columns,
                                    data=self.df_func().to_dict("records"),
                                    page_size=50,
                                    sort_action="native",
                                    sort_mode="multi",
                                    export_format="csv",
                                )
                            ]
                        )
                    ],
                    type="circle",
                ),
            ]
        )

    @property
    def id_button_options(self) -> str:
        return self.generate_id(self.ID_BUTTON_OPTIONS)

    @property
    def id_button_update(self) -> str:
        return self.generate_id(self.ID_BUTTON_UPDATE)

    @property
    def id_data_table(self) -> str:
        return self.generate_id(self.ID_DATA_TABLE)

    @property
    def id_date_picker(self) -> str:
        return self.generate_id(self.ID_DATE_PICKER)

    @property
    def id_drawer(self) -> str:
        return self.generate_id(self.ID_DRAWER)

    @property
    def id_loader_data_table(self) -> str:
        return self.generate_id(self.ID_LOADER_DATATABLE)

    @property
    def id_loader_graph(self) -> str:
        return self.generate_id(self.ID_LOADER_GRAPH)

    @property
    def id_multiselect_kit(self) -> str:
        return self.generate_id(self.ID_MULTISELECT_KIT)

    @property
    def id_multiselect_plots(self) -> str:
        return self.generate_id(self.ID_MULTISELECT_PLOTS)

    @property
    def id_multiselect_project(self) -> str:
        return self.generate_id(self.ID_MULTISELECT_PROJECT)

    @property
    def id_plot(self) -> str:
        return self.generate_id(self.ID_PLOT)

    @property
    def id_select_colour(self) -> str:
        return self.generate_id(self.ID_SELECT_COLOUR)

    @property
    def id_select_shape(self) -> str:
        return self.generate_id(self.ID_SELECT_SHAPE)
