# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and as of version 1.0.0, follows semantic versioning.

## [Unreleased]
  * Replace Pandas `NaN` with Python `None`. When sending to MISO, `None` gets converted to `null`, which is what MISO
expects.

## [240930-1516] - 2024-09-30
  * Fix MISO URL formatting for MISO 2.23.0

## [231114-1038] - 2023-11-14
  * Update Werkzeug package due to security issue
  * Bump qc-etl to v1.28
  * Remove crosscheckfingerprints kludge from previous release
  * Hide closest library from swap view and show expected library instead

## [231102-1512] - 2023-11-02
  * Insert a annoying kludge because gsi-qc-etl does not handle crosscheckfingerprints correctly

## [231016-1108] - 2023-10-16
  * Bump gevent version due to security issue
  * Fixed serious logic bug during swap filtering. Before this, the closest LOD was used to filter for swaps.
This was wrong. The furthers away LOD needs to be looked at for swap filtering. This bug hid orphan swaps where the 
closest match was in the "can't make a call" ambiguous zone of LOD -20 to 20.
  * Additional columns to the export table. Needed for top-up prevention calculations.

## [230912-1151] - 2023-09-12
  * Add comments to requirements.txt to explain `~=` operator
  * Fixed deprecated `DataFrame.max` parameter
  * Bumped gsi-qc-etl version to 1.27 and removed temporary PyYAML version fix

## [230717-1358] - 2023-07-17
  * One more column for the All Samples table: Coverage for single lane TAR
  * Bcl2barcode view has been greatly simplified by using the `bcl2barcodecaller` gsiqcetl cache
  * Downgrade PyYAML dependency to sidestep Cython 3.0 breaking change

## [230529-1503] - 2023-05-29
  * Yet more columns for the All Samples tables
  * Removed unnecessary Docker instructions
  * Update gsiqcetl to V1.24, which allows for Flask to be updated to latest version
    (removes `click` dependency conflict)

## [230503-1624] - 2023-05-03
  * Remove all ichorcna usage.
  * Made `dnaseqqc` an optional archival source
  * Update Dashi to gsiqcetl V1.23
  * More columns in All Samples tables

## [230424-1324] - 2023-04-24
  * Fixed dependency versions to speed up `pip install`
  * Allow Dashi to pull from more than one cache source
  * Update Dashi to gsiqcetl V1.22
  * Edited "All Samples" tables after user feedback
  * Allow `crosscheckfingerprints` cache to be missing from archival source
  * Remove the Raw Data Table

## [230330-1838] - 2023-03-30
  * Reverted to rnaseqqc2 V2 cache due to column naming bug

## [230330-1200] - 
  * Fixed Merged Pinery Lims ID being blank in exported csv
  * Introduce All Samples table

## [230303-1532] - 2023-03-03
  * Removed SARS-CoV-2 view
  * Dash -> 2.8.1
  * werkzeug -> 2.2.3
  * dash_bootstrap_components -> 1.4.0
  * Remove JIRA buttons due to compatibility issue

## [230109-0955] - 2023-01-09
  * Corrected caches displayed in view footer
  * Removed dangling ichorcna usage in single lane and call ready WG
  * Add the PG code (Plasma Whole Genome) to the WG view

## [221206-0851] - 2022-12-06
  * Changed `Total Clusters (Passed Filter)` to `Pipeline Filtered Clusters`
  * Removed `Total Reads (Passed Filter)`, as it's not used and (like clusters) does not count total reads.

## [221114-1440] - 2022-11-14
  * Switched Call Ready TAR Median Target Coverage to Mean Bait Coverage
  * No data for swap view doesn't cause crash (stage cache has become empty)
  * Remove 'Purity' from Call-Ready and Single-Lane WGS

## [221101-1532] - 2022-11-01
  * Fix bug where libraries without swaps were completely excluded from swap view

## [221017-1015] - 2022-10-17
  * Switch Dashi to qc-etl v1 caches
  * Update Python Docker version to 3.10
  * Swap view no longer loads huge data into memory and does heavy computation. Done by qc-etl.
  * Use gsi-qc-etl v1.9, which uses a Pandas version supported by Python 3.10

## [221003-0956] - 2022-10-03
## Changed
  * Remove bamqc3 caches from Dashi
  * Fixed werkzeug version

## [220809-1028] - 2022-08-09

## [220719-1428] - 2022-07-19
## Changed
  * Change on target graphs for call-ready and single-lane tar to use HsMetrics PCT_SELECTED_BASES

## [220712-0842] - 2022-07-12

## [220629-1419] - 2022-06-29
## Changed
  * Switch median insert size to mean insert size

## [220614-1309] - 2022-06-14
## Changed
  * Display Shallow Whole Genome libraries

## [220418-0952] - 2022-04-18
## Changed
  * dnaSeqQC cache loading alongside BamQC4 (picking the newest record if its found in
both caches)

## [220315-1154] - 2022-03-15
## Changed
  * Renamed columns in swap view

## [220222-0847] - 2022-02-22
## Changed
  * Unticking 'only show swaps' shows all projects in swap view
  * Added project name to swap view (does not always match Alias)
  * Showing meta data along library alias in swap view

## [220207-1446] - 2022-02-07
## Changed
  * Sample provenance is loaded from cache on disk rather than Mongo DB

## [220125-1411] - 2022-01-25
## Changed
  * TS acronym is TAR now
  * Mongo Provenance can be supplied as a hd5 file via MONGO_FILE env

## [220111-0825] - 2022-01-11
## Fixed
  * Wrong swap was being shown if patient has had only one library sequenced.
  * Special columns for Single Lane TS were not exported in CSV table.

## Changed
  * Added "Coverage per Gb" column to Call Ready TS data table

## [211122-1638] - 2021-11-22
## Changed
  * User messages can be displayed in each view.
  * Add checkbox to swap view to enable seeing all comparisons, not just those marked
as swaps.

## [211012-0851] - 2021-10-12
## Changed
  * Added sample hierarchy information to swap view (hidden by default to avoid clutter)
  * Made swap view more compact to see all columns on the screen
  * Fixed swap view bug where libraries from patients with only a single library were
ignored

## [210914-1010] - 2021-09-14
## Changed
  * `fill_in_color_col` and `fill_in_shape_col` take an arbitrary column for color/shape

## Added
  * Added Runscanner Illumina Flow Cell view (not turned on until GDI-2080 is solved)

## [210531-1427] - 2021-05-31
  * Remove bcl2barcode WIP and fix x-axis being cut off/missing tick labels

## [210511-0903] - 2021-05-11
## Changed
  * Clicking on Processing count on front page shows library names
  * Sample Swap view shows LOD scores of closet libraries + better column formatting

## [210503-1501] - 2021-05-03
## Added
  * Dashi license

## Changed
  * Sample Swap algorithm. The original approach used LOD cutoff, which produced too
many false positives (especially with WG/WT comparisons). New algorithm looks for the
most similar libraries and tags a swap if those are not from the same patient.

## [210426-1510] - 2021-04-26
## Added
  * Shesmu input link to the `status` page to view JSON that's passed to ETL

## [210412-1508] - 2021-04-12
## Changed
  * QC-ETL caches are now loaded in functions. Failure to load a cache will only 
impact views that call function. Previously, failure to load cache crashed all views.

## Added
  * Sample swap view
  * Gracefully dealing with caches that fail to load. Affected view shows error.

## [210406-0858] - 2021-04-06
## Changed
  * Bumped QC-ETL to 0.53.0

## [210323-0824] - 2021-03-23
## Changed
  * Fixed broken status page

## [210315-1515] - 2021-03-15
## Changed
  * Bumped QC-ETL to 0.51.0

## [210118-1517] - 2021-01-18
## Added
  * `/status` page showing date of the latest cache and cache errors
  * Alert pop up when run requested via URL query does not exist

## [210104-1505] - 2021-01-04
## Changed
  * Fix calculation of tumour/normal coverage cutoff values for Call Ready WGS
  * Add " + Intron" to Mean Insert Size fields on RNA reports

## Added
  * 'view all' link leading to page listing all runs on front page 

## [201123-0749] - 2020-11-23
## Removed
  * Any Call-Ready graphs or variables based on unmapped or non-primary reads. These
  are filtered out during BAM merging.
  
## Changed
  * Unmapped and non-primary read percentages are calculated using the BamQC `meta` 
  columns (https://github.com/oicr-gsi/bam-qc-metrics/blob/master/metrics.md#summary-of-fields).
  `non primary reads` column will always be 0, with `non primary reads meta` having
  the actual number
  * Use BamQC Total Reads as denominator for On Target Percentage rather than FastQC. 
  This is because BamQC On Target Reads calculations cannot be directly compared to 
  the actual total (FastQC) machine reads (due to BamQC filtering and non-primary reads)

## [201116-1508] - 2020-11-16
## Changed
  * Total PF Clusters in cfmedip come from fastqc
  * Spelling fixes

## [201109-1507] - 2020-11-09
## Changed
  * Fix colour scheme on png export
  * Sort by run date
  * Fix data labels
  * Bumped gsi-qc-etl to 0.44.2 (has correct median coverage calculations)

## [201102-1704] - 2020-11-02
## Added
  * Total PF Clusters to cfmedip view

## [201026-1520] - 2020-10-26
## Changed
  * Bumped gsi-qc-etl to 0.43.2 (has correct median calculations)
  * Switched cfmedip insert size median percentile to correct columns

## [201020-0811] - 2020-10-20
## Changed
  * MISO URLs now stored in config repo

## [201013-1418] - 2020-10-13
## Changed
  * 'QC in MISO' button now points to MISO Prod


## [201013-0744] - 2020-10-13
## Changed
  * Added insert size graph to cfmedip
  * Bumped gsi-qc-etl to 0.42.0

## [201008-1821] - 2020-10-08
## Changed
  * Added 'QC in MISO' button

## Configuration Changes
  * MISO_URL in .env required

## [201005-1627] - 2020-10-05
## Changed
  * Add clusters-per-sample thresholds
  * 'Missing' info no longer appears in Failed Samples table
  * Bumped gsi-qc-etl to 0.41.0
  * Call ready graphs new use clusters instead of reads
  * Single lane TS cutoffs were switched to clusters

## [200928-1530] - 2020-09-28
## Changed
  * Use Total Clusters instead of Total Reads in single lane views
  * New thresholds for cfMeDIP report

## [200921-1501] - 2020-09-21
## Changed
  * Added Tissue Origin as colour-by criteria
  * Updated thresholds in preparation for QC Handoff feature
  * Tumor purity graph for Call Ready WGS
  * Replace BamQC's TotalReads with FastQC's TotalSequences in applicable reports

## [200914-1449] - 2020-09-14
## Changed
  * Renamed 'Approve this run in MISO' button to 'View run in MISO' for clarity

## [200908-0809] - 2020-09-08
## Changed
  * Every data point now has a unique x-axis value, no longer stack vertically

## [200824-1630] - 2020-08-24
## Added
  * Row count at bottom of data tables

## [200817-1538] - 2020-08-17
## Changed
  * Bumped ETL version to 0.38.0
  
## Removed
  * `bamqc` cache dependency
  
## Added
  * Callability graphs show normal and tumor coverage cutoffs
  * Coverage graphs added to Single Lane WG and TS

## [200810-1533] - 2020-08-10
## Changed
  * Remaining Call-Ready reports converted to use subplots


## [200804-0746] - 2020-08-04
## Changed
  * Call-Ready TS 1 and 2 combined into one report via subplots
  * Single-lane pages converted to use subplots

## [200727-1637] - 2020-07-27
## Changed
  * Added columns to SARS-CoV-2 raw data table

## [200720-1507] - 2020-07-20
## Changed
  * Requires grouped_run_status and grouped_project_status files for front page
  * Displays only date instead of datetimes on front page

## [200713-1430] - 2020-07-13
## Changed
  * Bumped to ETL v0.37.0 (bcl2barcode fix)

## Added
  * Home button on navbar

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
