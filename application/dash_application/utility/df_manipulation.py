import datetime
import pandas as pd
from pandas import DataFrame
from typing import List

import gsiqcetl.column
import pinery

PINERY_COL = pinery.column.SampleProvenanceColumn
BAMQC_COL = gsiqcetl.column.BamQcColumn
ICHORCNA_COL = gsiqcetl.column.IchorCnaColumn
RNASEQQC_COL = gsiqcetl.column.RnaSeqQcColumn
INSTRUMENTS_COL = pinery.column.InstrumentWithModelColumn
RUN_COL = pinery.column.RunsColumn
PROJECT_COL = pinery.column.ProjectsColumn

pinery_ius_columns = [PINERY_COL.SequencerRunName, PINERY_COL.LaneNumber,
                      PINERY_COL.IUSTag]

bamqc_ius_columns = [BAMQC_COL.Run, BAMQC_COL.Lane, BAMQC_COL.Barcodes]
ichorcna_ius_columns = [ICHORCNA_COL.Run, ICHORCNA_COL.Lane, ICHORCNA_COL.Barcodes]
rnaseqqc_ius_columns = [RNASEQQC_COL.Run, RNASEQQC_COL.Lane,
                        RNASEQQC_COL.Barcodes]

_pinery_client = pinery.PineryClient()
_provenance_client = pinery.PineryProvenanceClient(provider="pinery-miso-v5")
_pinery_samples = _provenance_client.get_all_samples()
# Cast the primary key/join columns to explicit types
_pinery_samples = _pinery_samples.astype({
    PINERY_COL.SequencerRunName: 'str',
    PINERY_COL.LaneNumber: 'int64',
    "IUSTag": 'str'})
# NaN sample attrs need to be changed to a str.
# Use the expected default values
_pinery_samples.fillna({
    PINERY_COL.PrepKit: "Unspecified",
    PINERY_COL.LibrarySourceTemplateType: "NN",
    PINERY_COL.TissueOrigin: "nn",
    PINERY_COL.TissueType: "n",
    PINERY_COL.TissuePreparation: "Unknown",
    PINERY_COL.GroupID: "",
    PINERY_COL.GroupIDDescription: ""
})
_runs = _pinery_client.get_runs(False).runs

_instruments = _pinery_client.get_instruments_with_models()
_projects = _pinery_client.get_projects()

_active_projects = _projects.loc[_projects[PROJECT_COL.IsActive] == True]
_active_projects = _active_projects[PROJECT_COL.Name].unique()
_active_samples = _pinery_samples.loc[_pinery_samples[
    PINERY_COL.StudyTitle].isin(
    _active_projects)]

_runs_with_instruments = _runs.copy(deep=True).merge(
        _instruments[[INSTRUMENTS_COL.ModelName, INSTRUMENTS_COL.Platform,
                      INSTRUMENTS_COL.InstrumentID]],
        how="left",
        left_on=[RUN_COL.InstrumentID],
        right_on=[INSTRUMENTS_COL.InstrumentID]
    )


def get_pinery_samples():
    """Get Pinery Sample Provenance DataFrame"""
    return _pinery_samples.copy(deep=True)


def get_pinery_samples_from_active_projects():
    return _active_samples.copy(deep=True)


def df_with_pinery_samples(df: DataFrame, pinery_samples: DataFrame, ius_cols:
                           List[str]):
    """Do an outer merge between the DataFrame and modern Pinery samples 
    data."""
    df = df.merge(
        pinery_samples,
        how="right",
        left_on=ius_cols,
        right_on=pinery_ius_columns
    )
    # drop items with no Pinery data, because they must be old
    df = df.dropna(subset=[PINERY_COL.SampleName])
    # drop items with Pinery data that is definitely old
    #  (pre-MISO, aka pre-April 2017)
    is_modern = pd.to_datetime(df[PINERY_COL.CreateDate]).apply(
        lambda x:
        x > datetime.date(2017, 4, 1))
    df = df[is_modern]
    return df


def df_with_instrument_model(df: DataFrame, run_col: str):
    """Add the instrument model column to a DataFrame."""
    r_i = _runs_with_instruments.copy(deep=True)
    return df.merge(
        r_i[[INSTRUMENTS_COL.ModelName, RUN_COL.Name]],
        how="left",
        left_on=run_col,
        right_on=[RUN_COL.Name]
    )


def df_with_normalized_ius_columns(df: DataFrame, run_col: str, lane_col: str,
                                   barcodes_col: str):
    return df.astype({
        run_col: 'str',
        lane_col: 'int64',
        barcodes_col: 'str'
    })


def filter_by_library_design(df: DataFrame, library_designs: List[str]):
    return df[df[PINERY_COL.LibrarySourceTemplateType].isin(library_designs)]
