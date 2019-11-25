# Setup
1. Install python3, pip
1. Setup new virtual environment
1. `pip install -r requirements.txt`
1. Set the GSI_ETL_CACHE_DIR environment variable
1. `flask run` **OR** `gunicorn --bind 0.0.0.0:5000 wsgi:app`