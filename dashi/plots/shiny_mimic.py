from typing import List, Dict

from pandas import DataFrame

import sd_material_ui

import dash_html_components as html
import dash_core_components as dcc


class ShinyMimic:
    ID_DATE_PICKER = "date_picker"
    ID_DRAWER = "project_drawer"
    ID_MULTISELECT_KIT = "kit_multi_select"
    ID_MULTISELECT_PLOTS = "plots_multi_select"
    ID_MULTISELECT_PROJECT = "project_multi_select"
    ID_SELECT_COLOUR = "colour_by"
    ID_SELECT_SHAPE = "shape_by"

    def __init__(
        self,
        df: DataFrame,
        id_prefix: str,
        columns_to_plot: List[str],
        colour_columns: List[Dict[str, str]],
        shape_columns: List[Dict[str, str]],
    ):
        self._df = df
        self.id_prefix = id_prefix
        self.columns_to_plot = columns_to_plot
        self.colour_columns = colour_columns
        self.shape_columns = shape_columns

    def get_sorted_column(self, column_name) -> list:
        return list(self._df[column_name].sort_values().unique())

    @property
    def id_date_picker(self) -> str:
        return f"{self.id_prefix}_{self.ID_DATE_PICKER}"

    @property
    def id_drawer(self) -> str:
        return f"{self.id_prefix}_{self.ID_DRAWER}"

    @property
    def id_multiselect_kit(self) -> str:
        return f"{self.id_prefix}_{self.ID_MULTISELECT_KIT}"

    @property
    def id_multiselect_plots(self) -> str:
        return f"{self.id_prefix}_{self.ID_MULTISELECT_PLOTS}"

    @property
    def id_multiselect_project(self) -> str:
        return f"{self.id_prefix}_{self.ID_MULTISELECT_PROJECT}"

    @property
    def id_select_colour(self) -> str:
        return f"{self.id_prefix}_{self.ID_SELECT_COLOUR}"

    @property
    def id_select_shape(self) -> str:
        return f"{self.id_prefix}_{self.ID_SELECT_SHAPE}"

    def generate_drawer_layout(
        self,
        project_column: str,
        kit_column: str,
        date_column: str,
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
                                for x in self.get_sorted_column(project_column)
                            ],
                            value=self.get_sorted_column(project_column),
                        ),
                        html.Br(),
                        html.Label("Kits:"),
                        dcc.Dropdown(
                            id=self.id_multiselect_kit,
                            multi=True,
                            options=[
                                {"label": x, "value": x}
                                for x in self.get_sorted_column(kit_column)
                            ],
                            value=self.get_sorted_column(kit_column),
                        ),
                        html.Br(),
                        html.Label("Dates: "),
                        dcc.DatePickerRange(
                            id=self.id_date_picker,
                            display_format="YYYY-MM-DD",
                            min_date_allowed=min(self._df[date_column]),
                            max_date_allowed=max(self._df[date_column]),
                            start_date=min(self._df[date_column]),
                            end_date=max(self._df[date_column]),
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
