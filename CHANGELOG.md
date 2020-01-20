# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and as of version 1.0.0, follows semantic versioning.

## [Unreleased]
### Added
  * Bcl2Fastq Index QC graph
  * Set `DASHI_LOG_TO_CONSOLE=True` in `.env` file to log to console
  * Set `USE_BLEEDING_EDGE_ETL=1` in `.env` file to use gsi-qc-etl@master (development only)
### Changed
  * Filter logs now remove `end_date` if it is the current date
  * Filter logs now report `end_date` as a date rather than datetime
  * Filter logs now report `["all_runs"]` when all runs have been selected; etc for other dropdowns
### Fixed
  * `nav_handler` and `content_handler` no longer throw exception on empty path
  * `Add All` button for Library Designs on WGS report now works
  * Remove blank Run from TS and RNA dropdowns

## [200114-1651] - 2020-01-14
### Added
  * Added footer containing version number
  * Added ability to search for data of runs from last X days using URL query `?last=Xdays`
  * Log filter parameters for each search
  * Added AS, CH, CM, NN libraries to pre-WGS page
### Changed
  * Loading animation no longer freezes during page load
  * Changed 'Pre-X' page titles to 'Single-Lane X' and updated URLs to match
### Fixed
  * Negative numbers are no longer valid for cutoff inputs
  * pre-WGS: BamQC and ichorCNA data are now reported independently
  * pre-RNA: rRNA contamination now fails above cutoff (not below)
  * pre-RNA: Get total reads data from FastQC (unique reads)

## [0.1] 2019-12-19
Dashi alpha release. Many features were added, and many changes were made.
See commit history for more details...
