import dash_html_components as html
import dash_core_components as dcc
import dash.dependencies as dep

# The server is necessary, as gunicorn calls this to start Flask instance
from app import app, server
from home import layout as home_layout
from bamqc.gbovertime import layout as gbovertime_layout
from bamqc.over_time import layout as bamqc_over_time
from bcl2fastq.index_summary import (
    generate_layout as bcl2fastq_generate_layout,
    assign_callbacks as bcl2fastq_assign_callbacks,
)
from rnaseqc.over_time import layout as rnaseqc_overtime_layout
from runreport.proj_hist import layout as runreport_projhist_layout
from runscanner.yield_over_time import (
    layout as runscanner_yield_over_time_layout,
)
from poolqc.pooling_qc_sample import layout as pooling_qc_layout

app.layout = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-content")]
)


@app.callback(
    dep.Output("page-content", "children"), [dep.Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/":
        return home_layout
    elif pathname == "/bamqc/gbovertime":
        return gbovertime_layout
    elif pathname == "/bamqc/shiny":
        return bamqc_over_time
    elif pathname == "/bcl2fastq/indexinfo":
        return bcl2fastq_generate_layout()
    elif pathname == "/rnaseqc/over_time":
        return rnaseqc_overtime_layout
    elif pathname == "/runreport/proj_hist":
        return runreport_projhist_layout
    elif pathname == "/runscanner/sum_over_time":
        return runscanner_yield_over_time_layout
    elif pathname == "/pooling_qc":
        return pooling_qc_layout
    else:
        return "404"


bcl2fastq_assign_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True)
