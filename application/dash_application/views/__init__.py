import dash_bootstrap_components as dbc


def navbar(current):
    return dbc.NavbarSimple(
        children=[
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem("Exome", href="exome", style={"fontSize": "12pt"}),
                    dbc.DropdownMenuItem("Pre-Exome", href="preexome", style={"fontSize": "12pt"}),
                    dbc.DropdownMenuItem("sWGS", href="swgs", style={"fontSize": "12pt"}),
                    dbc.DropdownMenuItem("Pre-WGS", href="prewgs", style={"fontSize": "12pt"}),
                    dbc.DropdownMenuItem("CFMEDIP", href="cfmedip", style={"fontSize": "12pt"}),
                ],
                nav=True,
                in_navbar=True,
                style={"fontSize": "12pt"},
                label="Modules",
            ),
        ],
        brand=current,
        brand_style={"fontSize": "14pt"},
        color="light",
        dark=False,
        sticky="top",
    )
