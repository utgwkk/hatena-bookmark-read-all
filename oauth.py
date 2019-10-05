# coding=utf-8
from __future__ import print_function
from urllib.parse import parse_qs, urlencode
import requests
from xml.etree import ElementTree
from requests_oauthlib import OAuth1
from flask import make_response, redirect, request, \
                  url_for, session, Response, abort, current_app
from constants import *


def authorize():
    # Fetch access token
    oauth = OAuth1(CONSUMER_KEY, client_secret=CONSUMER_SECRET)
    params = {'scope': SCOPE,
              'oauth_callback': CALLBACK_URL}
    r = requests.post(REQUEST_TOKEN_URL, auth=oauth, params=params)
    if r.status_code == 200:
        rj = parse_qs(r.text)
        oauth_token = rj['oauth_token'][0]
        oauth_token_secret = rj['oauth_token_secret'][0]
        params = urlencode({'oauth_token': oauth_token})
        if is_smartphone():
            resp = make_response(redirect(AUTHORIZE_URL_SP + '?' + params))
        else:
            resp = make_response(redirect(AUTHORIZE_URL + '?' + params))
        session['oauth_token_secret'] = oauth_token_secret
        return resp


def callback():
    verifier = request.args.get('oauth_verifier')
    oauth_token = request.args.get('oauth_token')
    oauth_token_secret = session.get('oauth_token_secret')
    oauth = OAuth1(CONSUMER_KEY,
                   client_secret=CONSUMER_SECRET,
                   resource_owner_key=oauth_token,
                   resource_owner_secret=oauth_token_secret,
                   verifier=verifier)
    r = requests.post(GET_ACCESS_TOKEN_URL, auth=oauth)
    rj = parse_qs(r.text)
    oauth_token = rj['oauth_token'][0]
    oauth_token_secret = rj['oauth_token_secret'][0]
    session['oauth_token'] = oauth_token
    session['oauth_token_secret'] = oauth_token_secret
    return redirect(url_for('index'))


def logout():
    if not logged_in():
        abort(400)
    session['oauth_token'] = ''
    session['oauth_token_secret'] = ''
    resp = make_response(redirect(url_for('index')))
    return resp


def feed():
    if not logged_in():
        return redirect(url_for('index'))
    oauth = get_authorized_info()
    params = {'tag': 'あとで読む'}
    r = requests.get('http://b.hatena.ne.jp/atom/feed',
                     params=params,
                     auth=oauth)
    return Response(r.text, mimetype='text/xml')


def get_username():
    if not logged_in():
        return None
    oauth = get_authorized_info()
    r = requests.get(
        'https://bookmark.hatenaapis.com/rest/1/my',
        auth=oauth,
    )
    if r.status_code != 200:
        current_app.logger.error(f'code:{r.status_code} body:{r.text}')
        return None
    return r.json()['name']


# Functions
def logged_in():
    oauth_token = session.get('oauth_token', '')
    oauth_token_secret = session.get('oauth_token_secret', '')
    return oauth_token != '' and oauth_token_secret != ''


def get_authorized_info():
    oauth_token = session.get('oauth_token', '')
    oauth_token_secret = session.get('oauth_token_secret', '')
    return OAuth1(CONSUMER_KEY,
                  client_secret=CONSUMER_SECRET,
                  resource_owner_key=oauth_token,
                  resource_owner_secret=oauth_token_secret)


def get_bookmarks(page=1):
    if not logged_in():
        return redirect(url_for('index'))
    oauth = get_authorized_info()
    params = {'tag': 'あとで読む', 'page': page}
    data = []
    username = get_username()
    r = requests.get(f'https://b.hatena.ne.jp/{username}/bookmark.rss',
                        params=params,
                        auth=oauth)
    if r.status_code != 200:
        current_app.logger.error(f'code:{r.status_code} body:{r.text}')
        abort(400)
    ns = {'rdf': 'http://purl.org/rss/1.0/', 'dc': 'http://purl.org/dc/elements/1.1/'}
    xml = ElementTree.fromstring(r.text)
    targets = xml.findall('rdf:item', ns)
    for elem in targets:
        url = elem.find('rdf:link', ns).text
        title = elem.find('rdf:title', ns).text
        date = elem.find('dc:date', ns).text.replace('T', ' ')
        entry = {'url': url, 'title': title, 'date': date}
        data.append(entry)
    return data


def mark_as_read(url):
    if not logged_in():
        abort(403)
    oauth = get_authorized_info()
    r = requests.get('https://bookmark.hatenaapis.com/rest/1/my/bookmark',
                     params={'url': url},
                     auth=oauth)
    if r.status_code != 200:
        current_app.logger.error(f'code:{r.status_code} body:{r.text}')
        abort(400)
    rj = r.json()
    comment = rj['comment_raw']
    tags = rj['tags']
    comment = comment.replace(u'[あとで読む]', '')
    tags.remove(u'あとで読む')
    params = {'url': url, 'comment': comment, 'tags': tags}
    r = requests.post('https://bookmark.hatenaapis.com/rest/1/my/bookmark',
                      params=params, auth=oauth)
    if r.status_code != 200:
        current_app.logger.error(f'code:{r.status_code} body:{r.text}')
        abort(400)


def is_smartphone():
    user_agent = request.headers.get('User-Agent')
    return any(map(user_agent.__contains__,
               ['iPhone', 'iPad', 'Android', 'Mobile', 'Phone', 'Nexus']))
