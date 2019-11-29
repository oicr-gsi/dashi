# Dashi

Dashi is a quality control reporting system developed for genomic and
transcriptomic data. It is built on top of
[gsi-qc-etl](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse),
OICR's private QC data integration system, and so is currently of limited
utility to external parties. Please contact us for more information.

## Setup on bare metal

1. Install python3, pip
1. Setup new virtual environment
1. `pip install -r requirements.txt`
1. Set the GSI_ETL_CACHE_DIR environment variable
1. `flask run` **OR** `gunicorn --bind 0.0.0.0:5000 wsgi:app`


## Set up Docker container

The Docker container is a more straightforward way to launch Dashi for testing.
The base container has most of the dependencies required for the app, with one
crucial exception: gsi-qc-etl. This repository is private to OICR and so you
need to pass in your SSH keys to permit download and installation.

**Requirements**
* Docker 18.09.6+
* Docker compose 1.23.1+
* Access to [gsi-qc-etl](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse)


1. Ensure your ssh key has been added to OICR's Bitbucket and you can access and
   clone
   [gsi-qc-etl](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse).
2. Download the gsi-qc-etl cache data to `cache_files` (or modify
   docker-compose.yml to point to the correct location). The current location for
   this on OICR's cluster is at
   `/.mounts/labs/mcphersonlab/public/slazic/2019-01-16-GSI_ETL/dev_cache_files`.
3. Build the container with `docker-compose build`. Note that this completes
   installation of gsi-qc-etl before launching the app.
4. Launch with `docker-compose up`.`

Then navigate to [http://localhost:5000](http://localhost:5000).

