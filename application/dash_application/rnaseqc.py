import dash_html_components as html
import dash_core_components as core
from dash.dependencies import Input, Output
from .dash_id import init_ids
import pandas
import gsiqcetl.load
from gsiqcetl.rnaseqqc.constants import CacheSchema
from gsiqcetl.pinery.sampleprovenance.constants import (
    CacheSchema as SampleProvenanceCacheSchema
)

from application.dash_application.plots.shiny_mimic import ShinyMimic

page_name = 'rnaseqc/over_time'

RNA_DF = gsiqcetl.load.rnaseqqc(CacheSchema.v2)
RNA_COL = gsiqcetl.load.rnaseqqc_columns(CacheSchema.v2)

COL_RUN_DATE = "Run Date"
COL_PROP_ALIGNED_BASES = "Proportion Aligned Bases"

# The Run Name is used to extract the date
RNA_DF[COL_RUN_DATE] = (
    RNA_DF[RNA_COL.SequencerRunName].dropna().apply(lambda x: x.split("_")[0])
)
# Some runs do not have the proper format and will be excluded
RNA_DF = RNA_DF[RNA_DF[COL_RUN_DATE].str.isnumeric()]
RNA_DF[COL_RUN_DATE] = pandas.to_datetime(RNA_DF[COL_RUN_DATE], yearfirst=True)

RNA_DF[COL_PROP_ALIGNED_BASES] = (
    RNA_DF[RNA_COL.PassedFilterAlignedBases] / RNA_DF[RNA_COL.PassedFilterBases]
)

# List projects for which RNA-Seq studies have been done
ALL_PROJECTS = RNA_DF[RNA_COL.StudyTitle].sort_values().unique()

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
    left_on=[RNA_COL.SampleName, RNA_COL.SequencerRunName, RNA_COL.LaneNumber],
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

# Kits used for RNA-Seq experiments
ALL_KITS = RNA_DF[PINERY_COL.PrepKit].sort_values().unique()

# Which metrics can be plotted
METRICS_TO_GRAPH = (
    RNA_COL.ProportionUsableBases,
    RNA_COL.rRNAContaminationreadsaligned,
    RNA_COL.ProportionCorrectStrandReads,
    COL_PROP_ALIGNED_BASES,
    RNA_COL.ProportionCodingBases,
    RNA_COL.ProportionIntronicBases,
    RNA_COL.ProportionIntergenicBases,
    RNA_COL.ProportionUTRBases,
)

# Which columns will the data table always have
DEFAULT_TABLE_COLUMN = [
    {"name": "Library", "id": RNA_COL.SampleName},
    {"name": "Project", "id": RNA_COL.StudyTitle},
    {"name": "Run", "id": RNA_COL.SequencerRunName},
    {"name": "Lane", "id": RNA_COL.LaneNumber},
    {"name": "Kit", "id": PINERY_COL.PrepKit},
    {"name": "Library Design", "id": PINERY_COL.LibrarySourceTemplateType},
    {"name": "Tissue Origin", "id": PINERY_COL.TissueOrigin},
    {"name": "Tissue Type", "id": PINERY_COL.TissueType},
    {"name": "Tissue Material", "id": PINERY_COL.TissuePreparation},
]

# Columns on which shape and colour can be set
SHAPE_COLOUR_COLUMN = [
    {"name": "Project", "id": RNA_COL.StudyTitle},
    {"name": "Kit", "id": PINERY_COL.PrepKit},
    {"name": "Library Design", "id": PINERY_COL.LibrarySourceTemplateType},
    {"name": "Tissue Origin", "id": PINERY_COL.TissueOrigin},
    {"name": "Tissue Type", "id": PINERY_COL.TissueType},
    {"name": "Tissue Material", "id": PINERY_COL.TissuePreparation},
]

plot_creator = ShinyMimic(
    lambda: RNA_DF,
    "rnaseqqc_over_time",
    METRICS_TO_GRAPH,
    SHAPE_COLOUR_COLUMN,
    SHAPE_COLOUR_COLUMN,
    RNA_COL.StudyTitle,
    PINERY_COL.PrepKit,
    COL_RUN_DATE,
    RNA_COL.SampleName,
)

layout = plot_creator.generate_layout(
    4,
    RNA_COL.StudyTitle,
    PINERY_COL.PrepKit,
    DEFAULT_TABLE_COLUMN + [{"name": i, "id": i} for i in METRICS_TO_GRAPH],
)

def init_callbacks(dash_app):
    plot_creator.assign_callbacks(dash_app)