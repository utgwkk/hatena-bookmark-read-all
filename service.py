from xml.etree import ElementTree
from urllib.parse import parse_qs
import constants
import requests

def get(auth, url, *, params=None):
    if params is None:
        params = {}

    headers = {'User-Agent': constants.USER_AGENT}
    resp = requests.get(
        url,
        headers=headers,
        auth=auth,
        params=params,
    )
    resp.raise_for_status()
    return resp

def post(auth, url, *, params=None):
    if params is None:
        params = {}

    headers = {'User-Agent': constants.USER_AGENT}
    resp = requests.post(
        url,
        headers=headers,
        auth=auth,
        params=params,
    )
    resp.raise_for_status()
    return resp

def request_token(oauth):
    # Fetch access token
    params = {
        'scope': constants.SCOPE,
        'oauth_callback': constants.CALLBACK_URL,
    }
    resp = post(
        oauth,
        constants.REQUEST_TOKEN_URL,
        params=params,
    )

    resp_body = parse_qs(resp.text)
    oauth_token = resp_body['oauth_token'][0]
    oauth_token_secret = resp_body['oauth_token_secret'][0]
    return oauth_token, oauth_token_secret

def get_access_token(auth):
    resp = post(
        auth,
        constants.GET_ACCESS_TOKEN_URL,
    )
    resp_body = parse_qs(resp.text)
    oauth_token = resp_body['oauth_token'][0]
    oauth_token_secret = resp_body['oauth_token_secret'][0]
    return oauth_token, oauth_token_secret

def get_username(auth):
    resp = get(
        auth,
        'https://bookmark.hatenaapis.com/rest/1/my'
    )
    return resp.json()['name']

def get_bookmark(auth, url):
    resp = get(
        auth,
        'https://bookmark.hatenaapis.com/rest/1/my/bookmark',
        params={'url': url},
    )
    return resp.json()

def update_bookmark(auth, url, comment, tags):
    params = {'url': url, 'comment': comment, 'tags': tags}
    post(
        auth,
        'https://bookmark.hatenaapis.com/rest/1/my/bookmark',
        params=params,
    )

def get_bookmark_feed(auth, username, page=1):
    params = {'tag': 'あとで読む', 'page': page}
    resp = get(
        auth,
        f'https://b.hatena.ne.jp/{username}/bookmark.rss',
        params=params,
    )
    return resp.text

def get_bookmark_feed_as_list(auth, username, page=1):
    xml = get_bookmark_feed(auth, username, page)

    tree = ElementTree.fromstring(xml)
    namespace = {
        'rdf': 'http://purl.org/rss/1.0/',
        'dc': 'http://purl.org/dc/elements/1.1/',
    }

    data = []
    targets = tree.findall('rdf:item', namespace)
    for elem in targets:
        url = elem.find('rdf:link', namespace).text
        title = elem.find('rdf:title', namespace).text
        date = elem.find('dc:date', namespace).text.replace('T', ' ')
        entry = {'url': url, 'title': title, 'date': date}
        data.append(entry)

    return data
