import dash_core_components as core
import dash_html_components as html
import datetime
import pandas
from pandas import DataFrame, Series
from typing import List

import pinery.column
from gsiqcetl import QCETLCache
import gsiqcetl.column
import pinery


ex_lib_designs = ["EX", "TS"]
rna_lib_designs = ["MR", "SM", "TR", "WT"]
wgs_lib_designs = ["AS", "CH", "CM", "NN", "WG"]

PINERY_COL = pinery.column.SampleProvenanceColumn
BAMQC_COL = gsiqcetl.column.BamQcColumn
BAMQC3_COL = gsiqcetl.column.BamQc3Column
ICHORCNA_COL = gsiqcetl.column.IchorCnaColumn
RNASEQQC_COL = gsiqcetl.column.RnaSeqQcColumn
BAMQC3_MERGED_COL = gsiqcetl.column.BamQc3MergedColumn
ICHORCNA_MERGED_COL = gsiqcetl.column.IchorCnaMergedColumn
MUTECT_CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
HSMETRICS_MERGED_COL = gsiqcetl.column.HsMetricsColumn
RNASEQQC_MERGED_COL = gsiqcetl.column.RnaSeqQc2MergedColumn
INSTRUMENTS_COL = pinery.column.InstrumentWithModelColumn
RUN_COL = pinery.column.RunsColumn
PROJECT_COL = pinery.column.ProjectsColumn
sample_type_col = "Sample Type"

pinery_ius_columns = [PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber,
                      PINERY_COL.IUSTag]

bamqc_ius_columns = [BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes]
bamqc3_ius_columns = [BAMQC3_COL.Run, BAMQC3_COL.Lane, BAMQC3_COL.Barcodes]
ichorcna_ius_columns = [ICHORCNA_COL.Run,ICHORCNA_COL.Lane,
                        ICHORCNA_COL.Barcodes]
rnaseqqc_ius_columns = [RNASEQQC_COL.Run, RNASEQQC_COL.Lane,
                        RNASEQQC_COL.Barcodes]

pinery_merged_columns = [PINERY_COL.StudyTitle, PINERY_COL.RootSampleName,
    PINERY_COL.GroupID, PINERY_COL.LibrarySourceTemplateType,
    PINERY_COL.TissueOrigin, PINERY_COL.TissueType]
bamqc3_merged_columns = [BAMQC3_MERGED_COL.Project, BAMQC3_MERGED_COL.Donor,
    BAMQC3_MERGED_COL.GroupID, BAMQC3_MERGED_COL.LibraryDesign,
    BAMQC3_MERGED_COL.TissueOrigin, BAMQC3_MERGED_COL.TissueType]
ichorcna_merged_columns = [ICHORCNA_MERGED_COL.Project,
    ICHORCNA_MERGED_COL.Donor, ICHORCNA_MERGED_COL.GroupID,
    ICHORCNA_MERGED_COL.LibraryDesign, ICHORCNA_MERGED_COL.TissueOrigin,
    ICHORCNA_MERGED_COL.TissueType]
callability_merged_columns = [MUTECT_CALL_COL.Project, MUTECT_CALL_COL.Donor,
    MUTECT_CALL_COL.GroupID, MUTECT_CALL_COL.LibraryDesign,
    MUTECT_CALL_COL.TissueOrigin, MUTECT_CALL_COL.TissueType]
hsmetrics_merged_columns = [HSMETRICS_MERGED_COL.Project,
                            HSMETRICS_MERGED_COL.Donor, HSMETRICS_MERGED_COL.GroupID,
                            HSMETRICS_MERGED_COL.LibraryDesign, HSMETRICS_MERGED_COL.TissueOrigin,
                            HSMETRICS_MERGED_COL.TissueType]
rnaseqqc_merged_columns = [RNASEQQC_MERGED_COL.Project,
    RNASEQQC_MERGED_COL.Donor, RNASEQQC_MERGED_COL.GroupID,
    RNASEQQC_MERGED_COL.LibraryDesign, RNASEQQC_MERGED_COL.TissueOrigin,
    RNASEQQC_MERGED_COL.TissueType]

TUMOUR = "Tumour"
BLOOD = "Blood"
REFERENCE = "Reference"
CELL = "Cell"
UNKNOWN = "Unknown"

def label_sample_type(row: Series) -> str:
    if row[PINERY_COL.TissueType] == "S":
        return BLOOD
    elif row[PINERY_COL.TissueType] == "R":
        if row[PINERY_COL.TissueOrigin] == "Ly" or row[PINERY_COL.TissueOrigin] == "Pl":
            return BLOOD
        else:
            return REFERENCE
    elif row[PINERY_COL.TissueType] in ["P", "M", "O", "X", "T"]:
        return TUMOUR
    elif row[PINERY_COL.TissueType] == "C":
        return CELL
    else:
        return UNKNOWN


def is_tumour(row: Series) -> bool:
    if row[sample_type_col] == TUMOUR:
        return True
    return False


def is_normal(row: Series) -> bool:
    if row[sample_type_col] in [BLOOD, REFERENCE]:
        return True
    return False


def normalized_ius(df: DataFrame, ius_cols: List[str]):
    run_col, lane_col, barcodes_col = ius_cols
    return df.astype({
        run_col: 'str',
        lane_col: 'int64',
        barcodes_col: 'str'
    })

def normalized_merged(df: DataFrame, merged_cols: List[str]):
    project_col, donor_col, group_id_col, ld_col, to_col, tt_col = merged_cols
    return df.astype({
        project_col: 'str',
        donor_col: 'str',
        group_id_col: 'str',
        ld_col: 'str',
        to_col: 'str',
        tt_col: 'str'
    })


"""
Open a single instance of each cache, and use copies for the reports.
"""
cache = QCETLCache()
_bcl2fastq_known = cache.bcl2fastq.known
_bcl2fastq_unknown = cache.bcl2fastq.unknown
_rnaseqqc = normalized_ius(cache.rnaseqqc.rnaseqqc, rnaseqqc_ius_columns)
_bamqc = normalized_ius(cache.bamqc.bamqc, bamqc_ius_columns)
_bamqc3 = normalized_ius(cache.bamqc3.bamqc3, bamqc3_ius_columns)
_bamqc3_merged = normalized_merged(cache.bamqc3merged.bamqc3merged, bamqc3_merged_columns)
_ichorcna = normalized_ius(cache.ichorcna.ichorcna, ichorcna_ius_columns)
_ichorcna_merged = normalized_merged(cache.ichorcnamerged.ichorcnamerged, ichorcna_merged_columns)
_mutect_callability = normalized_merged(cache.mutectcallability.mutectcallability, callability_merged_columns)
_hsmetrics_merged = normalized_merged(cache.hsmetrics.metrics, hsmetrics_merged_columns)
_rnaseqqc_merged = normalized_merged(cache.rnaseqqc2merged.rnaseqqc2merged, rnaseqqc_merged_columns)

_pinery_client = pinery.PineryClient()
_provenance_client = pinery.PineryProvenanceClient(provider="pinery-miso-v5")
_pinery_samples = _provenance_client.get_all_samples()
# NaN sample attrs need to be changed to a str.
# Use the expected default values
_pinery_samples = _pinery_samples.fillna({
    PINERY_COL.PrepKit: "Unspecified",
    PINERY_COL.LibrarySourceTemplateType: "NN",
    PINERY_COL.TissueOrigin: "nn",
    PINERY_COL.TissueType: "n",
    PINERY_COL.TissuePreparation: "Unspecified",
    PINERY_COL.GroupID: "",
    PINERY_COL.GroupIDDescription: "",
    PINERY_COL.Institute: "Unspecified"
})
# Cast the primary key/join columns to explicit types now that the NA values are filled in
_pinery_samples = _pinery_samples.astype({
    PINERY_COL.SequencerRunName: 'str',
    PINERY_COL.LaneNumber: 'int64',
    "IUSTag": 'str',
    PINERY_COL.GroupID: 'str'})
# Fill in the "Sample Type" column (Tumor/Reference/Blood/Unknown)
_pinery_samples[sample_type_col] = _pinery_samples.apply(label_sample_type, axis=1)
# Drop columns we definitely don't care about.
_pinery_samples = _pinery_samples.drop(axis=1, columns=[PINERY_COL.NanodropConcentration, PINERY_COL.QubitConcentration, "RunIDandPosition", "TargetedResequencing", "TubeID", "RIN",
"PrepKit", "PoolName", "Organism", "STRResult", "QubitConcentration", "SampleProvenanceID",
"TissuePreparation", "TissueType", "SampleName", "RootSampleName", "Version", "NanodropConcentration",
"TissueOrigin", "Purpose", "SequencerRunName", "SequencingParameters", "UMIs", "GroupIDDescription",
"DV200", "CreateDate", "InstrumentName", "ParentSampleName", "SubProject", "TemplateType",
"RunBaseMask", "RunDir", "ExternalName", "Institute", "StudyTitle", "LastModified",
"GroupID", "SequencerRunPlatformModel", "ReceiveDate", "TissueRegion", "WorkflowType", "Skip",
"LaneNumber", "LibrarySourceTemplateType"])

# Helper function for the _pinery_merged_samples aggregation below.
# Takes a list of values and converts it to a comma-separated string.
unique_list = lambda vals: ", ".join(str(val) for val in sorted(set(vals)) if (val and val != "nan"))

""" Keep only these columns after merging on @merged_library columns.
Process the columns using the functions provided.
@merged_library columns (StudyTitle, RootSampleName, GroupID, TissueOrigin,
TissueType, LibrarySourceTemplateType) are already included in
the dataframe's index so they will also be retained."""
retain_columns_after_merge = {
    # sample attributes:
    PINERY_COL.DV200: unique_list,
    PINERY_COL.ExternalName: unique_list,
    PINERY_COL.Institute: unique_list,
    PINERY_COL.Organism: unique_list,
    PINERY_COL.RIN: unique_list,
    PINERY_COL.SubProject: unique_list,
    PINERY_COL.TissuePreparation: unique_list,
    sample_type_col: unique_list,
    # library attributes:
    PINERY_COL.PrepKit: unique_list,
    PINERY_COL.TargetedResequencing: unique_list,
    PINERY_COL.UMIs: unique_list,
}
    
"""
Converts the _pinery_samples data, where each row represents a single sequenced sample,
to a dataframe where each row represents a "merged library" (rows are joined on the following
PINERY_COL columns: RootSampleName (Donor), GroupID, TissueOrigin, TissueType,
LibrarySourceTemplateType). This multi-column index will be used to join full-depth QC
data to Pinery data.
1. Convert NA values to empty string (because our QC data seems to use '' instead of NA for Group ID)
2. Group the data by "merged library" columns
3. Aggregate and transform the columns we want to keep for Dashi
4. Reset the index to flatten the row
"""
_pinery_merged_samples = _pinery_samples.fillna('').groupby(by=pinery_merged_columns).agg(retain_columns_after_merge).reset_index()

_runs = _pinery_client.get_runs(False).runs
_runs[pinery.column.RunsColumn.StartDate] = pandas.to_datetime(
    _runs[pinery.column.RunsColumn.StartDate], utc=True)
_runs[pinery.column.RunsColumn.CompletionDate] = pandas.to_datetime(
    _runs[pinery.column.RunsColumn.CompletionDate], utc=True)

_instruments = _pinery_client.get_instruments_with_models()
_projects = _pinery_client.get_projects()

_active_projects = _projects.loc[_projects[PROJECT_COL.IsActive]]
_active_projects = _active_projects[PROJECT_COL.Name].unique()

_runs_with_instruments = _runs.copy(deep=True).merge(
    _instruments[[INSTRUMENTS_COL.ModelName, INSTRUMENTS_COL.Platform,
                  INSTRUMENTS_COL.InstrumentID]],
    how="left",
    left_on=[RUN_COL.InstrumentID],
    right_on=[INSTRUMENTS_COL.InstrumentID]
)


def get_bcl2fastq_known():
    return _bcl2fastq_known.copy(deep=True)


def get_bcl2fastq_unknown():
    return _bcl2fastq_unknown.copy(deep=True)


def get_bamqc():
    return _bamqc.copy(deep=True)


def get_bamqc3():
    return _bamqc3.copy(deep=True)


def get_ichorcna():
    return _ichorcna.copy(deep=True)


def get_rnaseqqc():
    return _rnaseqqc.copy(deep=True)


def get_bamqc3_merged():
    return _bamqc3_merged.copy(deep=True)


def get_ichorcna_merged():
    return _ichorcna_merged.copy(deep=True)


def get_mutect_callability():
    return _mutect_callability.copy(deep=True)


def get_hsmetrics_merged():
    return _hsmetrics_merged.copy(deep=True)


def get_rnaseqqc_merged():
    return _rnaseqqc_merged.copy(deep=True)


def get_pinery_samples(active_projects_only=True):
    """Get Pinery Sample Provenance DataFrame"""
    samples = _pinery_samples.copy(deep=True)
    if (active_projects_only):
        return samples.loc[samples[PINERY_COL.StudyTitle].isin(
            _active_projects)]
    else:
        return samples


def get_pinery_merged_samples(active_projects_only=True):
    samples = _pinery_merged_samples.copy(deep=True)
    if (active_projects_only):
        return samples.loc[samples[PINERY_COL.StudyTitle].isin(
            _active_projects)]
    else:
        return samples

def get_runs():
    return _runs_with_instruments.copy(deep=True)


def df_with_pinery_samples_ius(df: DataFrame, pinery_samples: DataFrame, ius_cols:
                           List[str]):
    """Do a left merge between the DataFrame and modern Pinery samples
    data. Only samples in QC DataFrame will be kept."""
    df = df.merge(
        pinery_samples,
        how="left",
        left_on=ius_cols,
        right_on=pinery_ius_columns,
        suffixes=('', '_q')
    )
    # Drop metrics with no corresponding Pinery data. This should only happen
    # if data is very old or stale
    df = df.dropna(subset=[PINERY_COL.SampleName])
    return df


def df_with_pinery_samples_merged(df: DataFrame, pinery_samples: DataFrame,
    merged_cols: List[str]):
    """Do a left merge between the DataFrame and modern Pinery samples
    data. Only samples in QC DataFrame will be kept."""
    df = df.merge(
        pinery_samples,
        how="left",
        left_on=merged_cols,
        right_on=pinery_merged_columns,
        suffixes=('', '_q')
    )
    return df


def df_with_instrument_model(df: DataFrame, run_col: str):
    """Add the instrument model column to a DataFrame."""
    r_i = _runs_with_instruments.copy(deep=True)
    return df.merge(
        r_i[[INSTRUMENTS_COL.ModelName, INSTRUMENTS_COL.Platform,
             RUN_COL.Name]],
        how="left",
        left_on=run_col,
        right_on=[RUN_COL.Name]
    )


def filter_by_library_design(df: DataFrame, library_designs: List[str],
                             ld_col=PINERY_COL.LibrarySourceTemplateType):
    return df[df[ld_col].isin(library_designs)]


def get_illumina_instruments(df: DataFrame) -> List[str]:
    """
    Gets a list of Illumina instruments with a given order.

    :param df: DataFrame (must contain Platform and Model Name columns)
    :return: list of instruments, correctly ordered
    """
    correct_order = [
        "Illumina NovaSeq 6000",
        "Illumina HiSeq 2500",
        "Illumina MiSeq",
        "NextSeq 550",
        "Illumina HiSeq X",
    ]
    eviction_list = [
        "Illumina Genome Analyzer II",
    ]
    instruments = df.loc[df[INSTRUMENTS_COL.Platform] == 'ILLUMINA'][
        INSTRUMENTS_COL.ModelName].sort_values().unique()
    pruned = [i for i in instruments if i not in eviction_list]
    sorted_instruments = sorted(pruned, key=lambda i:
        correct_order.index(i) if i in correct_order else -1)
    return sorted_instruments


def unique_set(df: DataFrame, col: str, reverse: bool=False) -> List[str]:
    unique = list(df[col].sort_values().dropna().unique())
    if reverse:
        return unique[::-1]
    else:
        return unique


def remove_suffixed_columns(df: DataFrame, suffix: str) -> DataFrame:
    """
    Join columns will often have the same column name, so DataFrames will append
    a suffix to distinguish them. Use this if we want to keep only one copy of the
    column around (usually because we've been using these as join columns so they
    should be the same)
    """
    to_drop = [col_name for col_name in df if col_name.endswith(suffix)]
    return df.drop(to_drop, axis=1)
