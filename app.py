from flask import Flask, render_template

app = Flask(__name__)


@app.route('/result/<tournament_id>/ranks')
def ranks(name=None):
    return render_template('rankings_template.html', name=name)


