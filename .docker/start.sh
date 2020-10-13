#!/usr/bin/env bash

# check if the passphrase is mounted. If it is, install it into ssh-agent
if [ -e /run/secrets/ssh_passphrase ]
then
    eval $(ssh-agent -s);
    /dashi/.docker/enter_passphrase $(cat /run/secrets/ssh_passphrase)
fi

# Optionally rewrite requirements.txt to use untested current ETL version (gsi-qc-etl@master)
# instead of a tested release version (gsi-qc-etl@<release version>)
if [ "$USE_BLEEDING_EDGE_ETL" -eq 1 ]; then
    sed -irn 's/^\(.*\)\/gsi-qc-etl.git@v.*$/\1\/gsi-qc-etl.git@master/ip' requirements.txt
fi

# mount your private key for bitbucket into the container to allow this command to succeed
pip install --trusted-host pypi.python.org -r requirements.txt

export PINERY_URL='http://pinery.gsi.oicr.on.ca/'
export MONGO_URL="mongodb://provenance_ro:$(cat /run/secrets/mongo_password)@provenance-mongo-db.gsi.oicr.on.ca:27017/provenance"
export GSI_QC_ETL_ROOT_DIRECTORY='/cache'
export MISO_URL='https://miso.oicr.on.ca/'

flask run --host=0.0.0.0 --port=5000
