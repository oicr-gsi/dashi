import dash_html_components as html
import dash_core_components as dcc

layout = html.Div([
    html.H1('Reporting Heaven'),

    html.H2('BamQC'),

    html.H3(
        dcc.Link(
            'Gigabases produced over time', href='/bamqc/gbovertime'
        )
    ),

    html.H2('RNASeQC'),

    html.H3(
        dcc.Link(
            'RNASeQC stats over time', href='/rnaseqc/over_time'
        )
    ),
])
