import logging
from urllib.parse import quote, parse_qs, urlencode
from xml.etree import ElementTree
from flask import Flask, Response, abort, request, redirect, session, url_for, render_template
import requests
from requests_oauthlib import OAuth1
import constants
app = Flask(__name__)
app.secret_key = constants.SECRET_KEY
app.logger.setLevel(logging.DEBUG)

# Helper


def logged_in():
    oauth_token = session.get('oauth_token', '')
    oauth_token_secret = session.get('oauth_token_secret', '')
    return oauth_token != '' and oauth_token_secret != ''


funcs = dict(logged_in=logged_in)
app.jinja_env.globals.update(**funcs)


def get_authorized_info():
    oauth_token = session.get('oauth_token', '')
    oauth_token_secret = session.get('oauth_token_secret', '')
    return OAuth1(
        constants.CONSUMER_KEY,
        client_secret=constants.CONSUMER_SECRET,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret
    )


def is_smartphone():
    user_agent = request.headers.get('User-Agent')
    for smp_ua in constants.SMARTPHONE_USER_AGENT:
        if smp_ua in user_agent:
            return True
    return False


def get_username():
    oauth = get_authorized_info()
    r = requests.get(
        'https://bookmark.hatenaapis.com/rest/1/my',
        auth=oauth,
    )
    r.raise_for_status()
    return r.json()['name']


def get_bookmarks(page=1):
    oauth = get_authorized_info()
    params = {'tag': 'あとで読む', 'page': page}
    data = []
    username = get_username()
    r = requests.get(
        f'https://b.hatena.ne.jp/{username}/bookmark.rss',
        params=params,
        auth=oauth,
    )
    r.raise_for_status()
    ns = {
        'rdf': 'http://purl.org/rss/1.0/',
        'dc': 'http://purl.org/dc/elements/1.1/',
    }
    xml = ElementTree.fromstring(r.text)
    targets = xml.findall('rdf:item', ns)
    for elem in targets:
        url = elem.find('rdf:link', ns).text
        title = elem.find('rdf:title', ns).text
        date = elem.find('dc:date', ns).text.replace('T', ' ')
        entry = {'url': url, 'title': title, 'date': date}
        data.append(entry)
    return data

# Controllers
@app.route('/')
def index():
    bookmarks = []
    if logged_in():
        bookmarks = bookmarks = get_bookmarks()

    return render_template('index.html', bookmarks=bookmarks)


@app.route('/oauth')
def auth():
    # Fetch access token
    oauth = OAuth1(
        constants.CONSUMER_KEY,
        client_secret=constants.CONSUMER_SECRET,
    )
    params = {
        'scope': constants.SCOPE,
        'oauth_callback': constants.CALLBACK_URL,
    }
    r = requests.post(constants.REQUEST_TOKEN_URL, auth=oauth, params=params)
    r.raise_for_status()

    rj = parse_qs(r.text)
    oauth_token = rj['oauth_token'][0]
    oauth_token_secret = rj['oauth_token_secret'][0]
    params = urlencode({'oauth_token': oauth_token})
    if is_smartphone():
        resp = redirect(constants.AUTHORIZE_URL_SP + '?' + params)
    else:
        resp = redirect(constants.AUTHORIZE_URL + '?' + params)
    session['oauth_token_secret'] = oauth_token_secret
    return resp


@app.route('/oauth/callback')
def auth_callback():
    verifier = request.args.get('oauth_verifier')
    oauth_token = request.args.get('oauth_token')
    oauth_token_secret = session.get('oauth_token_secret')
    oauth = OAuth1(
        constants.CONSUMER_KEY,
        client_secret=constants.CONSUMER_SECRET,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
        verifier=verifier,
    )
    r = requests.post(constants.GET_ACCESS_TOKEN_URL, auth=oauth)
    rj = parse_qs(r.text)
    oauth_token = rj['oauth_token'][0]
    oauth_token_secret = rj['oauth_token_secret'][0]
    session['oauth_token'] = oauth_token
    session['oauth_token_secret'] = oauth_token_secret
    return redirect(url_for('index'))


@app.route('/oauth/logout')
def auth_logout():
    if not logged_in():
        abort(400)
    session['oauth_token'] = ''
    session['oauth_token_secret'] = ''
    return redirect(url_for('index'))


@app.route('/feed')
def feed():
    if not logged_in():
        return redirect(url_for('index'))
    oauth = get_authorized_info()
    params = {'tag': 'あとで読む'}
    r = requests.get(
        'http://b.hatena.ne.jp/atom/feed',
        params=params,
        auth=oauth,
    )
    r.raise_for_status()
    return Response(r.text, mimetype='text/xml')


@app.route('/feed/read', methods=['POST'])
def mark_as_read():
    url = request.args.get('url')
    if not logged_in():
        abort(403)
    oauth = get_authorized_info()
    r = requests.get(
        'https://bookmark.hatenaapis.com/rest/1/my/bookmark',
        params={'url': url},
        auth=oauth,
    )
    r.raise_for_status()
    rj = r.json()
    comment = rj['comment_raw']
    tags = rj['tags']
    comment = comment.replace('[あとで読む]', '')
    if 'あとで読む' in tags:
        tags.remove('あとで読む')
    params = {'url': url, 'comment': comment, 'tags': tags}
    r = requests.post(
        'https://bookmark.hatenaapis.com/rest/1/my/bookmark',
        params=params,
        auth=oauth,
    )
    r.raise_for_status()

    return 'ok'


if __name__ == "__main__":
    app.run(debug=True)
