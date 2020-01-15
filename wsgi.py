from application import create_app
import os
import logging
import dotenv

dotenv.load_dotenv()

logging.basicConfig(filename=(os.getenv("LOG_FILE_LOCATION") or "dashi.log"), level=logging.INFO)

if os.getenv("LOG_TO_CONSOLE") == "True":
    logging.getLogger().addHandler(logging.StreamHandler())

## Set up application
app = create_app(os.environ.get("DEBUG", "false") == "true")

## Run application
if __name__ == "__main__":
    app.run()
