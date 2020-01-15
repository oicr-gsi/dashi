# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and as of version 1.0.0, follows semantic versioning.

## [Unreleased]
### Added
  * Bcl2Fastq Index QC graph
### Fixed
  * `nav_handler` and `content_handler` no longer throw exception on empty path

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
