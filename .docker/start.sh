#!/usr/bin/env bash


# Optionally rewrite pyproject.toml to use untested current ETL version (qc-etl@main)
# instead of a tested pinned commit of qc-etl
if [ "$USE_BLEEDING_EDGE_ETL" -eq 1 ]; then
    sed -i -E 's/(qc-etl = \{ git = "[^"]+", )rev = "[^"]*"/\1branch = "main"/' pyproject.toml
    uv lock -P qc-etl
fi

uv sync --frozen

uv run flask run --host=0.0.0.0 --port=5000
