from flask import current_app as app
from flask import render_template
import random

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
            title='Platonic-Dash Default Page')
