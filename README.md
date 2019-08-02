# Dashi

## Purpose

Interactive visualization of OICR Genomics QC data

## Installation

<<<<<<< HEAD
<<<<<<< HEAD
`pip install git+https://github.com/oicr-gsi/dashi`

For development, it is more convenient to run

`pip install -e git+https://github.com/oicr-gsi/dashi#egg=dashi --src DICT`

where `DICT` is the destination folder for the code. The installed package is
symbolically linked to that folder and any changes in the code will be
automatically available in the installed package.
=======
`pip install git+https://github.com/slazicoicr/dashi`
=======
`pip install git+https://github.com/oicr-gsi/dashi`
>>>>>>> Fixed README link from personal fork to GSI repo

For development, it is more convenient to run

`pip install -e git+https://github.com/oicr-gsi/dashi#egg=dashi --src DICT`

<<<<<<< HEAD
where `DICT` is the destination folder for the code. The installed package is 
system linked to that folder and any changes in the code will be automatically 
available in the installed package.
>>>>>>> Added `setup.py` and CHANGELOG
=======
where `DICT` is the destination folder for the code. The installed package is
symbolically linked to that folder and any changes in the code will be
automatically available in the installed package.
>>>>>>> Fixed README link from personal fork to GSI repo

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
