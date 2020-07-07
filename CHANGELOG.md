# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and as of version 1.0.0, follows semantic versioning.

## [Unreleased]

## [200707-0945] - 2020-07-07

## [200706-1605] - 2020-07-06
## Changed
  * Removed Insert Size columns from raw data table on RNAseq reports
  * Updated Dash to 1.13 (supports subplot sorting)

## [200629-1329] - 2020-06-29
## Changed
  * Navbar now appears on front page, eliminates need for Reports list
  * Converted bcl2fastq report to bcl2barcode

## Upgrade Notes
  * New required environment variable 'BARCODES_STREXPAND'

## [200622-1532] - 2020-06-22
## Changed
  * Call ready pages use median coverage 

## [200615-1633] - 2020-06-15
## Changed
  * Adjusted JIRA button behaviour and wording
  * Empty graphs start at 0
  * Sorting is independent of colour/shape by
  * First and second sort options are the same
  
## Removed
  * The Call Ready linking Color to First Sort

## [200608-1438] - 2020-06-08
## Added
  * Alphabetical second sort option (Sample Name, Merged Lane) 

## [200602-0954] - 2020-06-02
## Added
  * 2 SARS-CoV-2 mapping % graphs: % of host depleted, % of total reads
  
## Removed
  * SARS-CoV-2 On Target % graph

## [200601-1019] - 2020-06-01
## Changed
  * Removed FastQC dependency for Total Reads from Single Lane RNA-Seq
  * Made date range clearable

## Added
  * Help button to projects list

  
## [200525-1221] - 2020-05-25
## Changed
  * Cutoffs are medians where Median Insert Size graph
  * Single-Lane RNA-seq Correct Strand % is a percentage
  * Removed Purity from Call-Ready TS 2

## Added
  * Pulls run and project dump from Shesmu to create tables on front page

## [200519-0811] - 2020-05-19
## Changed
  * Switched Insert Mean to Insert Median with 10/90 percentiles
  * y-axis on graphs is always set to auto-scale, including on % graphs

## Added
  * Projects may now be specified through the url for all reports. Add 'project=' to the query portion of the URL.
## [200511-1447] - 2020-05-11
## Changed
  * Style changes to bar plots
  * Single Lane RNAseq now uses RNASeqQC2
  * JIRA link will prompt for login if not logged into JIRA

## [200504-1619] - 2020-05-04
## Changed
  * Show only On & Near Bases on TS Bar graph
  * Use BamQC4 as well as BamQC3

## Added
  * cfMeDIP report

## [200428-1006] - 2020-04-28
## Changed
  * locks down dependency versions to specific versions to avoid breaking changes, please run 'pip install -r requirements.txt --upgrade --no-cache-dir` 
  * Improved styling for graphs

## [200422-1118] - 2020-04-22
## Changed
  * SARS-CoV-2 coverage graph uses median coverage with 10/90 percentile error bars
  * No legends for cutoff lines nor highlighted samples, to preserve graph widths
  * SARS-CoV-2 On Target bar chart no longer shows unmapped numbers
  * Graphs now have white background colour
  * SARS-CoV-2 report now more accurately gets all Samples

## [200417-1147] - 2020-04-17
## Changed
  * SARS-CoV-2 data table works
  * SARS-CoV-2 Coverage Percentiles graph has x axis labels
  * SARS-CoV-2 Percentile graph is colourable
  * SARS-CoV-2 has adjustable cutoff lines
  * SARS-CoV-2 report sortable, colourable by Sequencing Control Type
  * SARS-CoV-2 sorting fixed

## [200409-1535] - 2020-04-09
## Added
  * SARS-CoV-2 report

## [200406-1118] - 2020-04-06
## Changed
  * Purity & Ploidy removed from Single Lane WGS
  * Pinery URL in docker

## Added
  * Proof-of-principle Genome Build features for Single Lane reports

## [200326-1116] - 2020-03-26
## Changed
  * RNA-seq 5/3 bias is on log scale
  * Single-Lane TS uses bamqc3
  * RNA-seq uses FASTQC for Total REads
  * Colour palette now colourblindness-friendly
## Added
  * add cr-WGS Coverage per Gb graph
  * add stacked bar chart for Percentage On/Near/Off Bait to Call-Ready TS 2

## [200305-1136] - 2020-03-05
## Changed
  * Standardized graph axes and titles
  * Updated some underlying data calculations
  * Removed Purity & Ploidy graphs from call-ready WGS
  * Wrapped graphs and tables in tabs for better table access
## Added
  * Buttons to create JIRA tickets

## [200214-1500] - 2020-02-14
### Changed
  * Update how % rRNA contamination is calculated for call-ready RNA
  * Use merged library fields as x-axis on call-ready graphs
  * On call-ready pages, pin "Colour By" value to "First Sort" value

## [200213-1220] - 2020-02-13
### Added
  * Bcl2Fastq Index QC graph
  * Set `DASHI_LOG_TO_CONSOLE=True` in `.env` file to log to console
  * Set `USE_BLEEDING_EDGE_ETL=1` in `.env` file to use gsi-qc-etl@master (development only)
### Changed
  * Filter logs now remove `end_date` if it is the current date
  * Filter logs now report `end_date` as a date rather than datetime
  * Filter logs now report `["all_runs"]` when all runs have been selected; etc for other dropdowns
  * Pinery entries with no QC data are excluded from plots and data table
  * Show Names drop down menu can display info from multiple fields
  * Put newline in `plot_builder.generate` to seperate color by and shape by
### Fixed
  * `nav_handler` and `content_handler` no longer throw exception on empty path
  * `Add All` button for Library Designs on WGS report now works
  * Remove blank Run from TS and RNA dropdowns
  * `content_handler` returns two values, matching the callback promise

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
