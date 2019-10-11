from typing import List, Dict, Callable

from pandas import DataFrame

import sd_material_ui

import dash_html_components as html
import dash_core_components as dcc
import dash_table


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
    ):
        self.df_func = df
        self.id_prefix = id_prefix
        self.columns_to_plot = columns_to_plot
        self.colour_columns = colour_columns
        self.shape_columns = shape_columns
        self.project_column_name = project_column_name
        self.kit_column_name = kit_column_name
        self.date_column_name = date_column_name

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
                        dcc.Dropdown(
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
                        dcc.Dropdown(
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
                        dcc.DatePickerRange(
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
                        dcc.Dropdown(
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
                                        dcc.Dropdown(
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
                                        dcc.Dropdown(
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
                dcc.Loading(
                    id=self.id_loader_graph,
                    children=[
                        sd_material_ui.Paper([dcc.Graph(id=self.id_plot)])
                    ],
                ),
                dcc.Loading(
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
