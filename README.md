# Dashi

Dashi is a quality control reporting system developed for genomic and
transcriptomic data. It is built on top of
[qc-etl](https://github.com/oicr-gsi/qc-etl), OICR's QC data integration
system.

# Requirements
* A built [qc-etl](https://github.com/oicr-gsi/qc-etl) cache directory
* A running [pinery](https://github.com/oicr-gsi/pinery) install


## Environment Variables
Create a `.env` file in the root directory of this repository.

| Variable name               | Required?              | Description                                                                                                                                              | Example                                               | Default |
|-----------------------------|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|---------|
| `QC_ETL_ROOT_DIRECTORY` | **Yes**                | One or more colon seperated directories where the QC-ETL caches are located. Records will be deduplicated, with records kept from the cache listed first | `/qcetl` or `/qcetl:/qcetl_archive`                    | |
| `MONGO_URL`                 | No                     | URL to location of MongoDB which holds historical Pinery provenance data                                                                                 | `mongodb://user:password@mongo_web_url:27017/db_name` | |
| `MONGO_FILE`                | No                     | File location of hd5 file holding DataFrame dump                                                                                                          | `/mongo_provenance.hd5`                               | |
| `PINERY_URL`                | **Yes**                | URL to location of Pinery web service root                                                                                                               | `http://pinery-url:8080/pinery-ws-miso`               | 
| `PINERY_USERNAME`           | No                     | Username for Pinery, only needed if `MONGO_URL`/`MONGO_FILE` are unset and Pinery sits behind HTTP Basic Auth                                            | `dashi`                                               | |
| `PINERY_PASSWORD`           | No                     | Password for Pinery, only needed if `MONGO_URL`/`MONGO_FILE` are unset and Pinery sits behind HTTP Basic Auth                                            |                                                        | |
| `MISO_URL`                  | **Yes**                | URL to location of MISO web service root                                                                                                                 | `http://miso.your.domain/`                            |
| `LOG_FILE_LOCATION`         | **Yes**                | File path where logs should be written                                                                                                                   | `~/logs/dashi.log`                                    | `./dashi.log` |
| `BARCODES_STREXPAND`        | **Yes**                | Tab-separated file listing 10X barcodes and 4 sequences for each                                                                                         | `~/barcodes`                                          | |
| `LOG_TO_CONSOLE`            | No                     | Set to log to console as well as to log file specified above                                                                                             | `True`                                                | do not log |
| `USE_BLEEDING_EDGE_ETL`     | No                     | Set to install `qc-etl@main` instead of the pinned commit of `qc-etl` in `pyproject.toml` (Docker only)                                    | `1`                                                   | use release version |
| `EXCLUDE_SWAP_LIBS`         | No                     | File path to TSV file of library pairs to be excluded for swap view                                                                                      | `./exclude_swap_lib.tsv`                              | |
| `SAMPLES_FOR_PROJECTS`      | No                     | Indicate whether samples from ALL projects should be used, or only samples from ACTIVE projects.                                                         | `ALL`                                                 | `ACTIVE` |
| `DISPLAY_USER_MESSAGE`      | No                     | A JSON file containing a dictionary of page names (key) and messages to display (value)                                                                  | `./user_messages.json`                                | |
| `ENABLED_REPORTS`           | No                     | Comma-separated list of view module names (as listed in `ALL_REPORTS` in `pages.py`) to enable on this deployment                                       | `call_ready_wgs,single_lane_wgs,bcl2barcode`           | all reports |

## Setup on bare metal

1. Install [uv](https://github.com/astral-sh/uv).
1. `uv sync`.
1. Ensure your `.env` file is populated as per `Environment Variables` above.
1. `uv run flask run` **OR** `uv run gunicorn --bind 0.0.0.0:5000 wsgi:app`

### Running as a systemd service

To keep Dashi running persistently on a systemd-based Linux host, run it under
a dedicated, unprivileged system user rather than root.

1. Create a system user with its own home directory (`uv` needs somewhere to
   install itself) and no login shell, then give it ownership of wherever
   Dashi is checked out. `/var/lib/dashi` and `/home/ubuntu/dashi` below are
   just examples — replace both with the actual paths on your host:
   ```
   sudo useradd --system --create-home --home-dir /var/lib/dashi --shell /usr/sbin/nologin dashi
   sudo chown -R dashi:dashi /home/ubuntu/dashi
   ```
   This user also needs write access to the file specified by
   `LOG_FILE_LOCATION`, and read access to the `QC_ETL_ROOT_DIRECTORY`
   cache.

1. Install `uv` as that user, so it lands in `dashi`'s own home/bin rather
   than root's:
   ```
   sudo -u dashi -H bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
   ```

1. Make sure `git` is installed — `uv sync` needs it to pull `qc-etl` directly
   from its GitHub repo per `pyproject.toml` (e.g. `sudo apt-get install -y
   git` on Debian/Ubuntu). Then, as the `dashi` user, sync dependencies inside
   the checked-out directory:
   ```
   sudo -u dashi -H bash -c 'cd /home/ubuntu/dashi && ~/.local/bin/uv sync'
   ```
   Make sure a populated `.env` file (see `Environment Variables` above) also
   exists in that directory and is readable by `dashi`.

1. Create a unit file at `/etc/systemd/system/dashi.service`. Adjust
   `WorkingDirectory` and the `uv` path/home directory to match your
   deployment, and `User`/`Group` if you named the system user something
   other than `dashi` in step 1. The `After=haproxy.service` /
   `Wants=haproxy.service` lines are only relevant if you're running Dashi
   behind haproxy like this deployment does — remove them if you aren't:
   ```
   [Unit]
   Description=Dashi
   After=syslog.target
   After=haproxy.service
   Wants=haproxy.service

   [Service]
   User=dashi
   Group=dashi
   WorkingDirectory=/home/ubuntu/dashi
   ExecStart=/var/lib/dashi/.local/bin/uv run flask run
   Environment=PATH=/var/lib/dashi/.local/bin:/usr/bin:/bin
   NoNewPrivileges=true
   Restart=always
   RuntimeMaxSec=1h

   [Install]
   WantedBy=multi-user.target
   ```

Then load and start it with:
```
sudo systemctl daemon-reload
sudo systemctl enable --now dashi
```

Verify it actually started:
```
sudo systemctl status dashi
sudo journalctl -u dashi -f
```
Look for `Running on http://0.0.0.0:5000` in the journal output — that confirms
Flask actually bound the port, not just that the process launched.


## Set up Docker container

The Docker container is a more straightforward way to launch Dashi for testing.
The base container has all dependencies required for the app, including
qc-etl, which now installs automatically since the repository is public.

**Requirements**
* Docker 18.09.6+
* Docker compose 1.23.1+

1. Download the qc-etl cache data to `$HOME/qcetl` (or modify
   docker-compose.yml to point to the correct location). The current location for
   this on OICR's cluster is at
   `/scratch2/groups/gsi/<development or production>/qcetl`.
1. Create a file at `.mongopass` with the password to the MongoDB database and
    make sure the location in docker-compose.yml is correct in `secrets`.
1. Ensure your `.env` file is populated as per `Environment Variables` above.
1. Ensure the file 'dashi.log' exists in the place specified by `LOG_FILE_LOCATION`. Create a blank file if necessary.
1. Build the container with `docker-compose build`. 
1. Launch with `docker-compose up`. Note that this completes installation of
    qc-etl before launching the app.
`

Then navigate to [http://0.0.0.0:5000/](http://0.0.0.0:5000/).



# Troubleshooting

**1. `docker-compose up` fails with `ModuleNotFoundError: No module named 'qcetl'`**

Likely `qc-etl` failed to download or the sync step in `.docker/start.sh` didn't
run. Check that `docker-compose up` output shows `uv sync` completing without
errors.

**2. `docker-compose up` is not starting and reporting messages like : `dashi    | [2019-12-04 22:08:06 +0000] [54] [CRITICAL] WORKER TIMEOUT (pid:113) 
    dashi    | [2019-12-04 22:08:06 +0000] [113] [INFO] Worker exiting (pid: 113)
    dashi    | [2019-12-04 22:08:07 +0000] [120] [INFO] Booting worker with pid: 120`
 

Gunicorn and Docker dislike each other. Try using `flask run` instead.
