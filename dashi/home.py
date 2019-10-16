import dash_html_components as html
import dash_core_components as dcc

layout = html.Div(
    [
        html.H1("Dashi"),
        html.H2("BamQC"),
        html.H3(
            dcc.Link("Gigabases produced over time", href="/bamqc/gbovertime")
        ),
        html.H3(dcc.Link("Shiny", href="/bamqc/shiny")),
        html.H2("bcl2fastq"),
        html.H3(
            dcc.Link(
                "Known and unknown indexes per run", href="/bcl2fastq/indexinfo"
            )
        ),
        html.H2("RNASeQC"),
        html.H3(dcc.Link("RNASeQC stats over time", href="/rnaseqc/over_time")),
        html.H2("Run Report"),
        html.H3(dcc.Link("Project Histograms", href="/runreport/proj_hist")),
        html.H2("Run Scanner"),
        html.H3(
            dcc.Link(
                "Pass filter yield over time", href="/runscanner/sum_over_time"
            )
        ),
        html.H2("QC Reports "),
        html.H3(dcc.Link("Pool Balancing QC", href="/pooling_qc")),
    ]
)
