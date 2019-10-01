from flask import Flask, render_template, request, redirect, escape
import os, sys, signal

import page_view, page_edit

app = Flask(__name__)
app.secret_key = os.urandom(128 // 8)
app.config['SESSION_PERMANENT'] = False

app_config = None

@app.route('/')
def index():
    return redirect('view', code=302)

@app.route('/view')
def view():
    return page_view.handle(app_config)

@app.route('/edit', methods=['GET', 'POST'])
def edit():
    if request.method == 'GET':
        return page_edit.handle_get(app_config)
    else:
        return page_edit.handle_post(app_config)

@app.route('/new', methods=['GET', 'POST'])
def new():
    return 'I can use new as a function name in Python!'

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
    else:
        print('Trying to terminate process with SIGTERM...', file=sys.stderr)
        os.kill(os.getpid(), signal.SIGTERM)
    return 'Bye\n'

def main(bind, port, config):
    global app_config
    app_config = config

    app_config['db_uri'] = str(app_config['db_path'])
    del app_config['db_path']

    app.run(bind, port, debug=True, use_reloader=False)
