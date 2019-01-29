import pandas
import dash
import dash_table

rr = pandas.read_hdf('./run_report_cache.hd5')

# There is a dash_table bug that prevents filtering with whitespace
rr = rr.rename(mapper=lambda x: x.replace(' ', '_'), axis='columns')

print(rr.columns)

app = dash.Dash()

app.layout = dash_table.DataTable(
    id='table',
    columns=[{"name": i, "id": i} for i in rr.columns],
    data=rr.to_dict('rows'),
    sorting=True,
    # sorting_type='multi',
    filtering=True,
    row_selectable='multi',
    selected_rows=[],
    style_cell_conditional=[
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)',
        },
    ],
    css=[{
        'selector': '.dash-cell div.dash-cell-value',
        'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
    }],
    style_cell={
        'whiteSpace': 'no-wrap',
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
        'minWidth': 50,
    },
)

if __name__ == '__main__':
    app.run_server(debug=True)
