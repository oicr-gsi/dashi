from flask import current_app as app
from flask import render_template
import random

## Use flask's server-side rendering to create a page from templates/index.html
## The @app.route decoration tells flask to return this content for both http://<root> and http://<root>/index
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')
