FROM python:3.6

USER root

# mount dashi code at /dashi
WORKDIR /dashi

COPY *.py requirements.txt /dashi/
COPY .docker/requirements_less.txt .docker/start.sh /dashi/.docker/
COPY application /dashi/application/
# Requirements for pytables (HDF5) and scipy (blas and la and fortran)
RUN apt-get -yy update && apt-get -yy install libhdf5-serial-dev libblas3 liblapack3 liblapack-dev libblas-dev gfortran
RUN pip install --trusted-host pypi.python.org -r .docker/requirements_less.txt && pip install gunicorn

EXPOSE 5000

CMD bash /dashi/.docker/start.sh


