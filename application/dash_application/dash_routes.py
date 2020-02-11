import dash_bootstrap_components
from dash import Dash

index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Dashi</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Adds Dash to provided Flask server
def add_dash(server, debug):
    # Create Dash instance using Flask object as server
    dash_app = Dash(__name__, server=server, external_stylesheets=[
                    dash_bootstrap_components.themes.BOOTSTRAP])
    dash_app.enable_dev_tools(debug=debug)
    dash_app.index_string = index_string

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
