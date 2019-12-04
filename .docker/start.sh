#!/usr/bin/env bash

# check if the passphrase is mounted. If it is, install it into ssh-agent
if [ -e /run/secrets/ssh_passphrase ]
then
    eval $(ssh-agent -s);
    /dashi/.docker/enter_passphrase $(cat /run/secrets/ssh_passphrase)
fi


# mount your private key for bitbucket into the container to allow this command to succeed
pip install --trusted-host pypi.python.org -r requirements.txt

export PINERY_URL='http://seqbio-pinery-prod-www.hpc.oicr.on.ca:8080/pinery-ws-miso/'
export MONGO_URL="mongodb://provenance_ro:$(cat /run/secrets/mongo_password)@provenance-mongo-db.gsi.oicr.on.ca:27017/provenance"
export GSI_QC_ETL_ROOT_DIRECTORY='/cache'

flask run --host=0.0.0.0 --port=5000
