import dash_html_components as html
import dash_core_components as dcc
import dash.dependencies as dep

from app import app
from home import layout as home_layout
from bamqc.gbovertime import layout as gbovertime_layout
from rnaseqc.over_time import layout as rnaseqc_overtime_layout

app.layout = html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
])


@app.callback(
    dep.Output('page-content', 'children'), [dep.Input('url', 'pathname')]
)
def display_page(pathname):
    if pathname == '/':
        return home_layout
    elif pathname == '/bamqc/gbovertime':
        return gbovertime_layout
    elif pathname == '/rnaseqc/over_time':
        return rnaseqc_overtime_layout
    else:
        return '404'


if __name__ == '__main__':
    app.run_server(debug=True)
