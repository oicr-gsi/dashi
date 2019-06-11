# Dashi

## Purpose

Interactive visualization of OICR Genomics QC data

## Requirements
* python >= 3.6
* pandas >= 23.0
* dash >= 0.43
* gsi-qc-etl (private OICR BitBucket repository)

## Usage

### Data

All visualizations expect gsi-qc-etl cache files to be located in the `data` folder at the root of this repository. The easiest approach is to use symbolic links. If necessary, future changes can allow the path to be set by environmental variables or config files.

### Running

Individual visualizations can be started by calling the desired python file. Example:

```
python runscanner/yield_over_time.py
```

A list of links to all available visualizations is started by
```
python index.py
```

## Development

If your development environment doesn't already automatically use PEP8 for formatting, you can 
install a git hook to automatically format Python files as part of the commit process. To do so,
run this once:

    ```
    git config core.hooksPath .githooks
    ```
