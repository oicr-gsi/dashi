import os
import pandas
from pandas import DataFrame, Series
from typing import List

from gsiqcetl import QCETLMultiCache, QCETLCache
import gsiqcetl.column
import gsiqcetl.common.utility
import gsiqcetl.common
import pinery
import json

ex_lib_designs = ["EX", "TS"]
rna_lib_designs = ["MR", "SM", "TR", "WT"]
wgs_lib_designs = ["AS", "CH", "NN", "PG", "SW", "WG"]

PINERY_COL = pinery.column.SampleProvenanceColumn
BAMQC4_COL = gsiqcetl.column.BamQc4Column
BCL_KNOWN = gsiqcetl.column.Bcl2BarcodeCallerKnownColumn
BCL_UNKNOWN = gsiqcetl.column.Bcl2BarcodeCallerUnknownColumn
BCL_SUMMARY = gsiqcetl.column.Bcl2BarcodeCallerSummaryColumn
CROSSCHECKFINGERPRINTS_COL = gsiqcetl.column.CrosscheckFingerprintsCallSwapColumn
DNASEQQC_COL = gsiqcetl.column.DnaSeqQCColumn
RNASEQQC2_COL = gsiqcetl.column.RnaSeqQc2Column
BAMQC4_MERGED_COL = gsiqcetl.column.BamQc4MergedColumn
MUTECT_CALL_COL = gsiqcetl.column.MutetctCallabilityColumn
HSMETRICS_MERGED_COL = gsiqcetl.column.HsMetricsColumn
RNASEQQC2_MERGED_COL = gsiqcetl.column.RnaSeqQc2MergedColumn
INSTRUMENTS_COL = pinery.column.InstrumentWithModelColumn
RUN_COL = pinery.column.RunsColumn
RUNSCANNER_FLOWCELL_COL = gsiqcetl.column.RunScannerFlowcellColumn
PROJECT_COL = pinery.column.ProjectsColumn
FASTQC_COL = gsiqcetl.column.FastqcColumn
CFMEDIP_COL = gsiqcetl.column.CfMeDipQcColumn
sample_type_col = "Sample Type"
ml_col = "Merged Library"

pinery_ius_columns = [PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber,
                      PINERY_COL.IUSTag]

bamqc4_ius_columns = [BAMQC4_COL.Run, BAMQC4_COL.Lane, BAMQC4_COL.Barcodes]
dnaseqqc_ius_columns = [DNASEQQC_COL.Run, DNASEQQC_COL.Lane, DNASEQQC_COL.Barcodes]
fastqc_ius_columns = [FASTQC_COL.Run, FASTQC_COL.Lane, FASTQC_COL.Barcodes]
cfmedip_ius_columns = [CFMEDIP_COL.Run, CFMEDIP_COL.Lane, CFMEDIP_COL.Barcodes]
rnaseqqc2_ius_columns = [RNASEQQC2_COL.Run, RNASEQQC2_COL.Lane,
                        RNASEQQC2_COL.Barcodes]

pinery_merged_columns = [PINERY_COL.StudyTitle, PINERY_COL.RootSampleName,
    PINERY_COL.GroupID, PINERY_COL.LibrarySourceTemplateType,
    PINERY_COL.TissueOrigin, PINERY_COL.TissueType]
bamqc4_merged_columns = [BAMQC4_MERGED_COL.Project, BAMQC4_MERGED_COL.Donor,
                         BAMQC4_MERGED_COL.GroupID, BAMQC4_MERGED_COL.LibraryDesign,
                         BAMQC4_MERGED_COL.TissueOrigin, BAMQC4_MERGED_COL.TissueType]
callability_merged_columns = [MUTECT_CALL_COL.Project, MUTECT_CALL_COL.Donor,
    MUTECT_CALL_COL.GroupID, MUTECT_CALL_COL.LibraryDesign,
    MUTECT_CALL_COL.TissueOrigin, MUTECT_CALL_COL.TissueType]
hsmetrics_merged_columns = [HSMETRICS_MERGED_COL.Project,
                            HSMETRICS_MERGED_COL.Donor, HSMETRICS_MERGED_COL.GroupID,
                            HSMETRICS_MERGED_COL.LibraryDesign, HSMETRICS_MERGED_COL.TissueOrigin,
                            HSMETRICS_MERGED_COL.TissueType]
rnaseqqc2_merged_columns = [RNASEQQC2_MERGED_COL.Project,
    RNASEQQC2_MERGED_COL.Donor, RNASEQQC2_MERGED_COL.GroupID,
    RNASEQQC2_MERGED_COL.LibraryDesign, RNASEQQC2_MERGED_COL.TissueOrigin,
    RNASEQQC2_MERGED_COL.TissueType]

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


def label_merged_library(row: Series) -> str:
    return "_".join([row[col] for col in pinery_merged_columns])


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


root_dirs = os.getenv("GSI_QC_ETL_ROOT_DIRECTORY")
if root_dirs is None:
    raise KeyError("mandetory env variable GSI_QC_ETL_ROOT_DIRECTORY has not been set")
else:
    root_dirs = root_dirs.split(":")
    cache = QCETLMultiCache(root_dirs)
_pinery_client = pinery.PineryClient()

# Mongo Provenance can be loaded from DB or a cached hd5 DataFrame
mongo_source = {}
for s in ["MONGO_URL", "MONGO_FILE"]:
    if os.getenv(s) is not None:
        mongo_source[s] = os.getenv(s)
if len(mongo_source) != 1:
    raise ValueError(
        "Expected one source for Mango Provenance. Got {}".format(mongo_source)
    )

if mongo_source.get("MONGO_URL"):
    _provenance_client = pinery.PineryProvenanceClient(provider="pinery-miso-v7")
    _pinery_samples = _provenance_client.get_all_samples()
elif mongo_source.get("MONGO_FILE"):
    _pinery_samples = pinery.load_db("sqlite:///" + mongo_source["MONGO_FILE"])
else:
    raise ValueError("No Mongo source specified")

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
    PINERY_COL.Institute: "Unspecified",
    PINERY_COL.SequencingControlType: "Sample"
})
# Cast the primary key/join columns to explicit types now that the NA values are filled in
_pinery_samples = _pinery_samples.astype({
    PINERY_COL.SequencerRunName: 'str',
    PINERY_COL.LaneNumber: 'int64',
    PINERY_COL.IUSTag: 'str',
    PINERY_COL.GroupID: 'str'})
# Fill in the "Sample Type" column (Tumor/Reference/Blood/Unknown)
_pinery_samples[sample_type_col] = _pinery_samples.apply(label_sample_type, axis=1)
# Drop columns we definitely don't care about.
_pinery_samples = _pinery_samples.drop(axis=1, columns=[
    PINERY_COL.NanodropConcentration,
    PINERY_COL.QubitConcentration,
    PINERY_COL.RunIDandPosition,
    PINERY_COL.TubeID,
    PINERY_COL.PoolName,
    PINERY_COL.STRResult,
    PINERY_COL.QubitConcentration,
    PINERY_COL.Version,
    PINERY_COL.NanodropConcentration,
    PINERY_COL.Purpose,
    PINERY_COL.SequencingParameters,
    PINERY_COL.GroupIDDescription,
    PINERY_COL.CreateDate,
    PINERY_COL.TemplateType,
    PINERY_COL.RunBaseMask,
    PINERY_COL.RunDir,
    PINERY_COL.LastModified,
    PINERY_COL.SequencerRunPlatformModel,
    PINERY_COL.ReceiveDate,
    PINERY_COL.TissueRegion,
    PINERY_COL.WorkflowType,
    PINERY_COL.Skip,
    ])

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
# Fill in the "Merged Library" column (used as the x-axis for merged graphs)
_pinery_merged_samples[ml_col] = _pinery_merged_samples.apply(
    label_merged_library, axis=1)

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


def get_bcl2barcodecaller_known():
    return cache.load_same_version("bcl2barcodecaller").remove_missing("known").unique("known").copy(deep=True)


def get_bcl2barcodecaller_unknown():
    return cache.load_same_version("bcl2barcodecaller").remove_missing("unknown").unique("unknown").copy(deep=True)


def get_bcl2barcodecaller_summary():
    return cache.load_same_version("bcl2barcodecaller").remove_missing("summary").unique("summary").copy(deep=True)


def get_dnaseqqc_and_bamqc4():
    # Utility function creates new DataFrame, so no need to copy again
    return gsiqcetl.common.utility.concat_workflow_versions(
        [
            normalized_ius(
                cache.load_same_version("dnaseqqc").remove_missing("dnaseqqc").unique("dnaseqqc"),
                dnaseqqc_ius_columns
            ),
            normalized_ius(cache.load_same_version("bamqc4").unique("bamqc4"), bamqc4_ius_columns),
        ],
        dnaseqqc_ius_columns,
    )


def get_cfmedip():
    return cache.load_same_version("cfmedipqc").unique("cfmedipqc").copy(deep=True)


def get_cfmedip_insert_metrics():
    return cache.load_same_version("cfmedipqc").unique("insert_metrics").copy(deep=True)


def get_crosscheckfingerprints():
    return cache.load_same_version(
        "crosscheckfingerprints"
    # crosscheckfingerprints caches won't be archived
    ).remove_missing(
        "filterswaps"
    ).unique("filterswaps").copy(deep=True)


def get_fastqc():
    return normalized_ius(cache.load_same_version("fastqc").unique("fastqc"), fastqc_ius_columns)


def get_rnaseqqc2():
    return normalized_ius(cache.load_same_version("rnaseqqc2").unique("rnaseqqc2"), rnaseqqc2_ius_columns)


def get_runscanner_flowcell():
    return cache.load_same_version("runscannerillumina").unique("flowcell").copy(deep=True)


def get_bamqc4_merged():
    return normalized_merged(cache.load_same_version("bamqc4merged").unique("bamqc4merged"), bamqc4_merged_columns)


def get_mutect_callability():
    return normalized_merged(
        cache.load_same_version("mutectcallability").unique("mutectcallability"),
        callability_merged_columns
    )


def get_hsmetrics_merged():
    return normalized_merged(cache.load_same_version("hsmetrics").unique("metrics"), hsmetrics_merged_columns)


def get_rnaseqqc2_merged():
    return normalized_merged(
        cache.load_same_version("rnaseqqc2merged").unique("rnaseqqc2merged"),
        rnaseqqc2_merged_columns
    )


def get_pinery_samples(active_projects_only=True):
    """Get Pinery Sample Provenance DataFrame"""
    samples = _pinery_samples.copy(deep=True)
    # Serve samples for active projects unless ALL projects are requested
    if (not active_projects_only or os.getenv("SAMPLES_FOR_PROJECTS", 'ACTIVE').lower() in ('all')):
        return samples
    else:
        return samples.loc[samples[PINERY_COL.StudyTitle].isin(
            _active_projects)]


def get_pinery_merged_samples(active_projects_only=True):
    samples = _pinery_merged_samples.copy(deep=True)
    if (active_projects_only):
        return samples.loc[samples[PINERY_COL.StudyTitle].isin(
            _active_projects)]
    else:
        return samples

def get_runs():
    return _runs_with_instruments.copy(deep=True)

def df_with_fastqc_data(df, merge_cols):
    group = get_fastqc().groupby([FASTQC_COL.Run, FASTQC_COL.Lane, FASTQC_COL.Barcodes])
    total_reads = group[FASTQC_COL.TotalSequences].sum()
    # Pick any read (1 or 2) and its total sequences are the clusters
    total_clusters = group[FASTQC_COL.TotalSequences].first().rename("Total Clusters")
    fastqc = pandas.concat([total_reads, total_clusters], axis=1).reset_index()
    df_with_fastqc = df.merge(
        fastqc,
        how="left",
        left_on=merge_cols,
        right_on=[FASTQC_COL.Run, FASTQC_COL.Lane, FASTQC_COL.Barcodes],
        suffixes=('', '_q')
    )
    return df_with_fastqc

def df_with_pinery_samples_ius(df: DataFrame, pinery_samples: DataFrame, ius_cols:
                           List[str], right_suffix='_q'):
    """Do a left merge between the DataFrame and modern Pinery samples
    data. Only samples in QC DataFrame will be kept."""
    df = df.merge(
        pinery_samples,
        how="left",
        left_on=ius_cols,
        right_on=pinery_ius_columns,
        suffixes=('', right_suffix)
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


def df_with_run_info(df: DataFrame, run_col: str, right_suffix='_q'):
    """Add the instrument model column to a DataFrame."""
    r_i = _runs_with_instruments.copy(deep=True)
    return df.merge(
        r_i[[
            INSTRUMENTS_COL.ModelName,
            INSTRUMENTS_COL.Platform,
            RUN_COL.Name,
            pinery.column.RunsColumn.StartDate,
            pinery.column.RunsColumn.CompletionDate,
        ]],
        how="left",
        left_on=run_col,
        right_on=[RUN_COL.Name],
        suffixes=('', right_suffix)
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

def build_miso_info(df, page_title, metrics):
    """
    Builds the JSON for the http body for the request to MISO.
    Expects an array of dicts in the format:
    [{
        'title': threshold name minus the 'maximum' or 'minimum', 
        'threshold_type': gt, ge, lt, le
        'threshold': the current threshold setting from the sidebar,
        'value': the column to check in the dataframe for this threshold
    }]
    Note that the threshold_type rule is for what PASSES the threshold, ie what ISN'T in the Failed Samples table
    Returns [json string dump of http body, button style]
    """
    if (len(df.index) > 0):
        miso_button_style = {"display": "inline-block"}
        miso_request = {'report': page_title, 'library_aliquots': []}
        for index, row in df.iterrows():
            split_provenance_id = row[PINERY_COL.SampleProvenanceID].split('_')
            metrics_this_row = []
            for metric in metrics:
                metrics_this_row.append({
                    'title': metric['title'],
                    'threshold_type': metric['threshold_type'],
                    'threshold': metric['threshold'],
                    # MISO expects a JSON null object for missing data, not Pandas's NaN
                    'value': None if pandas.isna(row[metric['value']]) else row[metric['value']]
                })
            miso_request['library_aliquots'].append({
                'name': split_provenance_id[2],
                'metrics': metrics_this_row,
                'run_id': split_provenance_id[0],
                'partition': row[PINERY_COL.LaneNumber]
            })
        return [json.dumps(miso_request), miso_button_style]
    else:
        return [json.dumps({}), {"display": "none"}]


def extract_single_ldi(pinery_lims_id: str) -> str:
    """
    Dashi gets the Pinery LIMS ID (6273_1_LDI92180), but lab only deals with LDI part.

    Args:
        pinery_lims_id: Pinery LIMS ID

    Returns: Just the LDI info

    """
    return pinery_lims_id.rsplit("_", 1)[1]


def extract_multi_ldi(pinery_lims_ids: List[str]) -> str:
    """
    Call ready views have a comma seperated string of Pinery LIMS IDs. Extract LDI part from all of them.

    Args:
        pinery_lims_ids: List of Pinery LIMS ID

    Returns: Comma seperated LDIs

    """
    return ",".join([extract_single_ldi(x) for x in pinery_lims_ids])
