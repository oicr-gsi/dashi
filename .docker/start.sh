#!/usr/bin/env bash

# mount your private key for bitbucket into the container to allow this command to succeed
pip install --trusted-host pypi.python.org -r requirements.txt

export GSI_ETL_CACHE_DIR='/cache'

gunicorn --bind 0.0.0.0:5000 wsgi:app
