#!/usr/bin/env python
# coding=utf-8
import logging
from six.moves.urllib.parse import quote
from flask import Flask, request, render_template
import oauth
from constants import SECRET_KEY
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.logger.setLevel(logging.DEBUG)
funcs = dict(logged_in=oauth.logged_in, quote=quote, len=len)
app.jinja_env.globals.update(**funcs)


@app.route('/')
def index():
    if oauth.logged_in():
        return render_template('index.html', bookmarks=oauth.get_bookmarks())
    return render_template('index.html')


@app.route('/oauth')
def auth():
    return oauth.authorize()


@app.route('/oauth/callback')
def auth_callback():
    return oauth.callback()


@app.route('/oauth/logout')
def auth_logout():
    return oauth.logout()


@app.route('/feed')
def feed():
    return oauth.feed()


@app.route('/feed/read', methods=['POST'])
def mark_as_read():
    url = request.args.get('url')
    oauth.mark_as_read(url)
    return 'ok'


@app.route('/feed/read_all')
def mark_as_read_all():
    return oauth.mark_as_read_all()

if __name__ == "__main__":
    app.run()
