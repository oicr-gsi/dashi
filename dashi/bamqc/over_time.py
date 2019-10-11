import pandas


import gsiqcetl.load
from gsiqcetl.bamqc.constants import CacheSchema
from gsiqcetl.pinery.sampleprovenance.constants import (
    CacheSchema as SampleProvenanceCacheSchema,
)

from dashi.plots.shiny_mimic import ShinyMimic


RNA_DF = gsiqcetl.load.bamqc(CacheSchema.v1)
RNA_COL = gsiqcetl.load.bamqc_columns(CacheSchema.v1)

COL_RUN_DATE = "Run Date"
PROJECT = "Project"
FRACTION_ON_TARGET = "Read Fraction on Target"
FRACTION_MAPPED = "Read Fraction Mapped"
FRACTION_SECONDARY = "Read Fraction Secondary"

# The Run Name is used to extract the date
RNA_DF[COL_RUN_DATE] = (
    RNA_DF[RNA_COL.Run].dropna().apply(lambda x: x.split("_")[0])
)
# Some runs do not have the proper format and will be excluded
RNA_DF = RNA_DF[RNA_DF[COL_RUN_DATE].str.isnumeric()]
RNA_DF[COL_RUN_DATE] = pandas.to_datetime(RNA_DF[COL_RUN_DATE], yearfirst=True)

RNA_DF[PROJECT] = RNA_DF[RNA_COL.Library].apply(lambda x: x.split("_")[0])

RNA_DF[FRACTION_ON_TARGET] = (
    RNA_DF[RNA_COL.ReadsOnTarget] / RNA_DF[RNA_COL.TotalReads]
)
RNA_DF[FRACTION_MAPPED] = (
    RNA_DF[RNA_COL.MappedReads] / RNA_DF[RNA_COL.TotalReads]
)
RNA_DF[FRACTION_SECONDARY] = (
    RNA_DF[RNA_COL.NonPrimaryReads] / RNA_DF[RNA_COL.TotalReads]
)

# Pull in meta data from Pinery
# noinspection PyTypeChecker
PINERY: pandas.DataFrame = gsiqcetl.load.pinery_sample_provenance(
    SampleProvenanceCacheSchema.v1
)
PINERY_COL = gsiqcetl.load.pinery_sample_provenance_columns(
    SampleProvenanceCacheSchema.v1
)

PINERY = PINERY[
    [
        PINERY_COL.SampleName,
        PINERY_COL.SequencerRunName,
        PINERY_COL.LaneNumber,
        PINERY_COL.PrepKit,
        PINERY_COL.LibrarySourceTemplateType,
        PINERY_COL.TissueOrigin,
        PINERY_COL.TissueType,
        PINERY_COL.TissuePreparation,
    ]
]

RNA_DF = RNA_DF.merge(
    PINERY,
    how="left",
    left_on=[RNA_COL.Library, RNA_COL.Run, RNA_COL.Lane],
    right_on=[
        PINERY_COL.SampleName,
        PINERY_COL.SequencerRunName,
        PINERY_COL.LaneNumber,
    ],
)

# NaN kits need to be changed to a str. Use the existing Unspecified
RNA_DF = RNA_DF.fillna({PINERY_COL.PrepKit: "Unspecified"})
RNA_DF = RNA_DF.fillna({PINERY_COL.LibrarySourceTemplateType: "Unknown"})
# NaN Tissue Origin is set to `nn`, which is used by MISO for unknown
RNA_DF = RNA_DF.fillna({PINERY_COL.TissueOrigin: "nn"})
# NaN Tissue Type is set to `n`, which is used by MISO for unknown
RNA_DF = RNA_DF.fillna({PINERY_COL.TissueType: "n"})
RNA_DF = RNA_DF.fillna({PINERY_COL.TissuePreparation: "Unknown"})

# Which metrics can be plotted
METRICS_TO_GRAPH = (
    FRACTION_ON_TARGET,
    FRACTION_MAPPED,
    RNA_COL.InsertMean,
    RNA_COL.ReadsPerStartPoint,
    RNA_COL.TotalReads,
    FRACTION_SECONDARY,
)


# Which columns will the data table always have
DEFAULT_TABLE_COLUMN = [
    {"name": "Library", "id": RNA_COL.Library},
    {"name": "Project", "id": PROJECT},
    {"name": "Run", "id": RNA_COL.Run},
    {"name": "Lane", "id": RNA_COL.Lane},
    {"name": "Kit", "id": PINERY_COL.PrepKit},
    {"name": "Library Design", "id": PINERY_COL.LibrarySourceTemplateType},
    {"name": "Tissue Origin", "id": PINERY_COL.TissueOrigin},
    {"name": "Tissue Type", "id": PINERY_COL.TissueType},
    {"name": "Tissue Material", "id": PINERY_COL.TissuePreparation},
]

# Columns on which shape and colour can be set
SHAPE_COLOUR_COLUMN = [
    {"name": "Project", "id": PROJECT},
    {"name": "Kit", "id": PINERY_COL.PrepKit},
    {"name": "Library Design", "id": PINERY_COL.LibrarySourceTemplateType},
    {"name": "Tissue Origin", "id": PINERY_COL.TissueOrigin},
    {"name": "Tissue Type", "id": PINERY_COL.TissueType},
    {"name": "Tissue Material", "id": PINERY_COL.TissuePreparation},
]


plot_creator = ShinyMimic(
    lambda: RNA_DF,
    "bamqc_over_time",
    METRICS_TO_GRAPH,
    SHAPE_COLOUR_COLUMN,
    SHAPE_COLOUR_COLUMN,
    PROJECT,
    PINERY_COL.PrepKit,
    COL_RUN_DATE,
    RNA_COL.Library,
)


layout = plot_creator.generate_layout(
    4,
    PROJECT,
    PINERY_COL.PrepKit,
    DEFAULT_TABLE_COLUMN + [{"name": i, "id": i} for i in METRICS_TO_GRAPH],
)

try:
    from app import app
except ModuleNotFoundError:
    import dash

    app = dash.Dash(__name__)
    app.layout = layout

plot_creator.assign_callbacks(app)

if __name__ == "__main__":
    app.run_server(debug=True)
