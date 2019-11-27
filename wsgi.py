from application import create_app
import os

## Set up application
app = create_app(os.environ.get("DASHI_DEBUG", "false") == "true")

## Run application
if __name__ == "__main__":
    app.run()
