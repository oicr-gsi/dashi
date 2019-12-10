import dash_bootstrap_components as dbc


def navbar(current):
    def menu_item(label, link):
        return dbc.DropdownMenuItem(label,
                                    href=link,
                                    external_link=True,
                                    disabled=current == label,
                                    style={"fontSize": "12pt"})
    return dbc.NavbarSimple(
        children=[
            dbc.DropdownMenu(
                children=[
                    menu_item("Pre-Exome", "preqc-exome"),
                    menu_item("Pre-WGS", "preqc-wgs"),
                    menu_item("Pre-RNA", "preqc-rna")
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
