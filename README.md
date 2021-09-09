# Dashi

Dashi is a quality control reporting system developed for genomic and
transcriptomic data. It is built on top of
[gsi-qc-etl](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse),
OICR's private QC data integration system, and so is currently of limited
utility to external parties. Please contact us for more information.

# Requirements
* Access to [gsi-qc-etl](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse)
* A running [pinery](https://github.com/oicr-gsi/pinery) install
* A running MongoDB installation with provenance data and the password for the
    same. See
    [Historical Provenance MongoDB](https://wiki.oicr.on.ca/display/GSI/Historical+Provenance+MongoDB)
    (OICR internal)


## Environment Variables
Create a `.env` file in the root directory of this repository:

| Variable name | Required? | Description | Example | Default |
|---------------|-----------|-------------|---------|---------|
| `GSI_QC_ETL_ROOT_DIRECTORY` | **Yes** | Directory where the QC-ETL caches are located | `/qcetl` | |
| `MONGO_URL` | **Yes** | URL to location of MongoDB which holds Pinery data | `mongodb://user:password@mongo_web_url:27017/db_name` | |
| `PINERY_URL` | **Yes** | URL to location of Pinery web service root | `http://pinery-url:8080/pinery-ws-miso` | 
| `MISO_URL` | **Yes** | URL to location of MISO web service root | `http://miso.your.domain/` |
| `LOG_FILE_LOCATION` | **Yes** | File path where logs should be written | `~/logs/dashi.log` | `./dashi.log` |
| `BARCODES_STREXPAND` | **Yes** | Tab-separated file listing 10X barcodes and 4 sequences for each | `~/barcodes` | |
| `LOG_TO_CONSOLE` | No | Set to log to console as well as to log file specified above | `True` | do not log |
| `USE_BLEEDING_EDGE_ETL` | No | Set to install `gsi-qc-etl@master` instead of the release version of `gsi-qc-etl` in `requirements.txt` (Docker only) | `1` | use release version |
| `EXCLUDE_SWAP_LIBS` | No | File path to TSV file of library pairs to be excluded for swap view | `./exclude_swap_lib.tsv` | |

## Setup on bare metal

1. Install python3, pip.
1. Setup new virtual environment.
1. `pip install -r requirements.txt`.
1. Ensure your `.env` file is populated as per `Environment Variables` above.
1. `flask run` **OR** `gunicorn --bind 0.0.0.0:5000 wsgi:app`


## Set up Docker container

The Docker container is a more straightforward way to launch Dashi for testing.
The base container has most of the dependencies required for the app, with one
crucial exception: gsi-qc-etl. This repository is private to OICR and so you
need to pass in your SSH keys to permit download and installation.

**Requirements**
* Docker 18.09.6+
* Docker compose 1.23.1+

1. Ensure your ssh key has been added to OICR's Bitbucket and you can access and
   clone
   [gsi-qc-etl](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse). 
1. Download the gsi-qc-etl cache data to `$HOME/qcetl` (or modify
   docker-compose.yml to point to the correct location). The current location for
   this on OICR's cluster is at
   `/scratch2/groups/gsi/<development or production>/qcetl`.
1. Create a file at `.mongopass` with the password to the MongoDB database and
    make sure the location in docker-compose.yml is correct in `secrets`.
1. Ensure your `.env` file is populated as per `Environment Variables` above.
1. Ensure the file 'dashi.log' exists in the place specified by `LOG_FILE_LOCATION`. Create a blank file if necessary.
1. Build the container with `docker-compose build`. 
1. Launch with `docker-compose up`. Note that this completes installation of
    gsi-qc-etl before launching the app.
`

Then navigate to [http://0.0.0.0:5000/](http://0.0.0.0:5000/).



# Troubleshooting

**1. `docker-compose up` fails with `git@bitbucket.oicr.on.ca: Permission denied (publickey).
  fatal: Could not read from remote repository. Please make sure you have the correct access rights and the repository exists.`**

This is likely due to an error with binding your SSH key into the container. The
SSH key is required to install the gsi-qc-etl dependency. Follow these steps for
troubleshooting:

1. Try to clone gsi-qc-etl: `git clone ssh://git@bitbucket.oicr.on.ca/gsi/gsi-qc-etl.git`. 
    If this fails, check that you have correct permissions to the repository
    [https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse](https://bitbucket.oicr.on.ca/projects/GSI/repos/gsi-qc-etl/browse)
2. Check that your SSH key is located in `~/.ssh/`. If it is not, change the
    bind paths in `docker-compose.yml` for id_rsa, id_rsa.pub, and known_hosts.
3. Check if your SSH key requires a passphrase. If it is prompting from inside
    the container, it will fail. Create a private file with your SSH key
    passphrase. Open `docker-compose.yml` and uncomment out the
    `ssh_passphrase` lines in the dashi service and in the `secrets` section,
    and point docker-compose to your passphrase file in the secrets section.
    Do a fresh build of the compose file, ie. `docker-compose build --no-cache`.
    When next launching the container, the start.sh script will automatically
    provide the passphrase upon request.


**2. `docker-compose up` fails with `ModuleNotFoundError: No module named 'gsiqcetl'`**

Likely gsi-qc-etl failed to download. Check the Troubleshooting tip #1.

**3. `docker-compose up` is not starting and reporting messages like : `dashi    | [2019-12-04 22:08:06 +0000] [54] [CRITICAL] WORKER TIMEOUT (pid:113) 
    dashi    | [2019-12-04 22:08:06 +0000] [113] [INFO] Worker exiting (pid: 113)
    dashi    | [2019-12-04 22:08:07 +0000] [120] [INFO] Booting worker with pid: 120`
 

Gunicorn and Docker dislike each other. Try using `flask run` instead.
