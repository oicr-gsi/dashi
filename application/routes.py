from flask import current_app as app
from flask import render_template
import random

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
            title='Platonic-Dash Demo')

@app.route('/page2')
@app.metrics.counter('page2_loads', 'Number of times page2 is loaded')
def page2():
    return render_template('page2.html',
            mystery_item=random.choice(['A', 'B', 'C']))
