import dash_bootstrap_components as dbc


def navbar(current):
    return dbc.NavbarSimple(
        children=[
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem("Exome", href="exome"),
                    dbc.DropdownMenuItem("Pre-Exome", href="preexome"),
                    dbc.DropdownMenuItem("sWGS", href="swgs"),
                    dbc.DropdownMenuItem("Pre-WGS", href="prewgs"),
                    dbc.DropdownMenuItem("CFMEDIP", href="cfmedip"),
                ],
                nav=True,
                in_navbar=True,
                label="Modules",
            ),
        ],
        brand=current,
        brand_style={"fontSize": "14pt"},
        color="light",
        dark=False,
        sticky="top",
    )
