FROM python:3.6

USER root

# mount dashi code at /dashi
WORKDIR /dashi
# copy in just what directories are required to avoid accidentally copying in
# the cache or Dockerfile
COPY .docker/requirements_less.txt /dashi/.docker/

# Requirements for pytables (HDF5) and scipy (blas and la and fortran)
RUN apt-get -yy update && apt-get -yy install libhdf5-serial-dev libblas3 liblapack3 liblapack-dev libblas-dev gfortran
RUN pip install --trusted-host pypi.python.org -r .docker/requirements_less.txt && pip install gunicorn

COPY *.py requirements.txt /dashi/
COPY application /dashi/application/

EXPOSE 5000
COPY .docker/start.sh .docker/start.sh 
CMD bash /dashi/.docker/start.sh


