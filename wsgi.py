from application import create_app
import os
import logging

logging.basicConfig(filename='dashi.log', level=logging.INFO)

## Set up application
app = create_app(os.environ.get("DASHI_DEBUG", "false") == "true")

## Run application
if __name__ == "__main__":
    app.run()
