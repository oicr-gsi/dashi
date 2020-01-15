from application import create_app
import os
import logging
import dotenv

dotenv.load_dotenv()

logging.basicConfig(filename='dashi.log', level=logging.INFO)

if os.getenv("DASHI_LOG_TO_CONSOLE") == "True":
    logging.getLogger().addHandler(logging.StreamHandler())

## Set up application
app = create_app(os.environ.get("DASHI_DEBUG", "false") == "true")

## Run application
if __name__ == "__main__":
    app.run()
