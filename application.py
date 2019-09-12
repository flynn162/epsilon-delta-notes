from flask import Flask, render_template, request, redirect, escape
from pathlib import Path
from configparser import RawConfigParser
import os, sys, signal

import page_view

app = Flask(__name__)
app.secret_key = os.urandom(128 // 8)
app.config['SESSION_PERMANENT'] = False

def load_as_dir(base_dir, rel_dir_str, default):
    if not rel_dir_str:
        rel_dir_str = default
    if default is None:
        return
    img_dir = base_dir.joinpath(rel_dir_str)
    if not img_dir.is_dir():
        raise FileNotFoundError('%s is not a directory' % str(img_dir))
    return img_dir

def load_as_file(path_str):
    if not path_str:
        return None
    else:
        path = Path(path_str).resolve(True)
        if not path.is_file():
            raise FileNotFoundError('%s is not a file' % str(path))
        return path

def load_img_dir(img_dir_str, default):
    if app.config['db_path']:
        app.config['img_dir'] = load_as_dir(app.config['db_path'].parent,
                                            img_dir_str,
                                            default)
    else:
        app.config['img_dir'] = None

def load_env_var():
    app.config['db_path'] = load_as_file(os.environ.get('EDN_DB_FILE'))
    app.config['db_uri'] = str(app.config['db_path'])
    load_img_dir(os.environ.get('EDN_IMG_DIR'), None)

def load_config():
    config_path = load_as_file(os.environ.get('EDN_CONFIG_FILE'))
    print(' * Loading config', config_path, file=sys.stderr)
    if not config_path:
        return

    config = RawConfigParser()
    config.read(config_path)
    if not app.config['img_dir']:
        load_img_dir(config['default'].get('img_dir'), 'images')

load_env_var()
load_config()
del app.config['db_path']

@app.route('/')
def index():
    return redirect('view', code=302)

@app.route('/view')
def view():
    return page_view.handle(app)

@app.route('/edit')
def edit():
    return render_template('edit.html', title='Editing')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
    else:
        print('Trying to terminate process with SIGTERM...', file=sys.stderr)
        os.kill(os.getpid(), signal.SIGTERM)
    return 'Bye\n'
