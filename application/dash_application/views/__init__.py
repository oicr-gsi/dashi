import dash_bootstrap_components as dbc


def navbar(current):
    return dbc.NavbarSimple(
        children=[
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem("Pre-Exome", href="preqc-exome",
                                         style={"fontSize": "12pt"}),
                    dbc.DropdownMenuItem("Pre-WGS", href="preqc-wgs",
                                         style={"fontSize": "12pt"}),
                    dbc.DropdownMenuItem("Pre-RNA", href="preqc-rna",
                                         style={"fontSize": "12pt"})
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
