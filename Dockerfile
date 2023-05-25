FROM python:3.10

USER root

# mount dashi code at /dashi
WORKDIR /dashi
# copy in just what directories are required to avoid accidentally copying in
# the cache or Dockerfile
COPY *.py requirements.txt /dashi/

# Requirements for expect for passing a passphrase to ssh-agent
RUN apt-get -yy update && apt-get -yy install expect

COPY application /dashi/application/

EXPOSE 5000
COPY .docker/start.sh .docker/enter_passphrase /dashi/.docker/ 
CMD bash /dashi/.docker/start.sh


