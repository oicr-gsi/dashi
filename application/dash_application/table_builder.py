from typing import List

import dash_table as tabl
from pandas import DataFrame


def build_table(table_id: str, columns: List[str], df: DataFrame, filter_on:
                str):
    # Filter out records with NA values in the given column (should indicate
    # we have no QC data for these records
    df = df[~df[filter_on].isna()]
    return tabl.DataTable(
        id=table_id,
        columns=[{"name": col, "id": col} for col in columns],
        data=df.to_dict('records'),
        export_format="csv",
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ],
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold"
        }
    )
