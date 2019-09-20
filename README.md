# Dashi

## Purpose

Interactive visualization of OICR Genomics QC data

## Installation

`pip install git+https://github.com/oicr-gsi/dashi`

For development, it is more convenient to run

`pip install -e git+https://github.com/oicr-gsi/dashi#egg=dashi --src DICT`

where `DICT` is the destination folder for the code. The installed package is
symbolically linked to that folder and any changes in the code will be
automatically available in the installed package.

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

Consistent PEP8 compliant formatting can be ensured by enabling pre-commit
git hook.

    ```
    # Activate your preferred Dashi Python environment. If using Conda
    source activate your_dashi_conda_environment

    pip install pre-commit

    #While in the root of Dashi
    pre-commit install
    ```
