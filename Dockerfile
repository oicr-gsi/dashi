FROM python:3.13

USER root

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# mount dashi code at /dashi
WORKDIR /dashi
# copy in just what directories are required to avoid accidentally copying in
# the cache or Dockerfile
COPY *.py pyproject.toml uv.lock /dashi/

COPY application /dashi/application/

EXPOSE 5000
COPY .docker/start.sh /dashi/.docker/ 
CMD bash /dashi/.docker/start.sh


