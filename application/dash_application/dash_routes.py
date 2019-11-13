from dash import Dash


# Adds Dash to provided Flask server
def add_dash(server):
    # Create Dash instance using Flask object as server
    dash_app = Dash(__name__, server=server)

    # Set initial Dash page's layout
    from . import known_pages_router
    known_pages_router.init_callbacks(dash_app)
    dash_app.layout = known_pages_router.layout

    # Load all callbacks into memory
    from . import pages
    for page in pages.pages:
        page.init_callbacks(dash_app)

    # Return the server object from Dash to overwrite Flask server object
    return dash_app.server
