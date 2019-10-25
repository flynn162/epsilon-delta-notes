from flask import render_template
from sqlops import Db

class DbCreate(Db):
    pass

def handle_get(config):
    return render_template('new.html')

def handle_post(config):
    return
