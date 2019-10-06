import logging
from urllib.parse import urlencode
from flask import Flask, Response, abort, request, redirect, session, url_for, render_template
import requests
from requests_oauthlib import OAuth1

import constants
import service
app = Flask(__name__)
app.secret_key = constants.SECRET_KEY
app.logger.setLevel(logging.DEBUG)

# Helper


def logged_in() -> bool:
    '''
    ログイン中であるかどうかを表す真偽値を返す
    '''
    oauth_token = session.get('oauth_token', '')
    oauth_token_secret = session.get('oauth_token_secret', '')
    return oauth_token != '' and oauth_token_secret != ''


app.jinja_env.globals.update(logged_in=logged_in)


def get_authorized_info() -> OAuth1:
    '''
    認証情報を表すOAuth1オブジェクトを返す
    '''
    oauth_token = session.get('oauth_token', '')
    oauth_token_secret = session.get('oauth_token_secret', '')
    return OAuth1(
        constants.CONSUMER_KEY,
        client_secret=constants.CONSUMER_SECRET,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret
    )


def flush_session():
    '''
    セッションを破棄してログアウト状態にする
    '''
    del session['oauth_token']
    del session['oauth_token_secret']
    del session['username']


def is_smartphone() -> bool:
    '''
    アクセス元の端末がスマートフォンであるかどうかを判定する
    '''
    user_agent = request.headers.get('User-Agent')
    for smp_ua in constants.SMARTPHONE_USER_AGENT:
        if smp_ua in user_agent:
            return True
    return False


def get_username() -> str:
    '''
    ログインしているユーザーの名前を返す
    '''
    # sessionにキャッシュがあったら使う
    if 'username' in session:
        return session['username']

    oauth = get_authorized_info()
    username = service.get_username(oauth)
    # sessionにキャッシュする
    session['username'] = username
    return username


# Controllers
@app.route('/')
def index():
    '''
    GET /
    未読の記事一覧を表示する
    ログインしていないときはその旨が表示される
    '''
    bookmarks = []
    if logged_in():
        try:
            oauth = get_authorized_info()
            username = get_username()
            bookmarks = service.get_bookmark_feed_as_list(oauth, username)
        except requests.HTTPError:
            # ログインセッションがおかしくなるとAPIから401が返るので、
            # とりあえずログアウトする
            # ISE返るのを防いでるけどもっといい方法ありそう
            flush_session()

    return render_template('index.html', bookmarks=bookmarks)


@app.route('/oauth')
def auth():
    '''
    GET /oauth
    はてなのOAuth APIでログインする
    認可画面にリダイレクトする
    TODO: エンドポイント名再考の余地あり、/authorize はどうか
    '''
    oauth = OAuth1(
        constants.CONSUMER_KEY,
        client_secret=constants.CONSUMER_SECRET,
    )
    oauth_token, oauth_token_secret = service.request_token(oauth)
    params = urlencode({'oauth_token': oauth_token})
    if is_smartphone():
        resp = redirect(constants.AUTHORIZE_URL_SP + '?' + params)
    else:
        resp = redirect(constants.AUTHORIZE_URL + '?' + params)
    session['oauth_token_secret'] = oauth_token_secret
    return resp


@app.route('/oauth/callback')
def auth_callback():
    '''
    GET /oauth/callback
    認可画面からリダイレクトされる
    ここでアクセストークンが得られるので、ログアウトするまでこれを用いる
    '''
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
    oauth_token, oauth_token_secret = service.get_access_token(oauth)
    session['oauth_token'] = oauth_token
    session['oauth_token_secret'] = oauth_token_secret
    return redirect(url_for('index'))


@app.route('/oauth/logout')
def auth_logout():
    '''
    GET /oauth/logout
    ログアウトする
    ログインしていないときは400を返す
    '''
    if not logged_in():
        abort(400)

    flush_session()
    return redirect(url_for('index'))


@app.route('/feed')
def feed():
    '''
    GET /feed
    ログイン中のユーザーの「あとで読む」タグが付いたブックマークのRSSを返す
    ログインしていないときは / にリダイレクトする
    TODO: このエンドポイント使うことない気がする。要調査
    '''
    if not logged_in():
        return redirect(url_for('index'))

    page = int(request.args.get('page', 1))
    oauth = get_authorized_info()
    username = get_username()
    xml = service.get_bookmark_feed(oauth, username, page)
    return Response(xml, mimetype='text/xml')


@app.route('/feed/read', methods=['POST'])
def mark_as_read():
    '''
    POST /feed/read
    `url` パラメータのブックマークを既読状態にする
    ログインしていないときは403を返す
    TODO: 403より401の方がいいのでは？
    TODO: エンドポイント再考の余地があると思う
    feedというよりはbookmarkとか？
    '''
    if not logged_in():
        abort(403)

    url = request.args.get('url')
    oauth = get_authorized_info()
    bookmark = service.get_bookmark(oauth, url)

    comment = bookmark['comment_raw']
    tags = bookmark['tags']
    comment = comment.replace('[あとで読む]', '')
    if 'あとで読む' in tags:
        tags.remove('あとで読む')

    service.update_bookmark(oauth, url, comment, tags)

    return 'ok'


if __name__ == "__main__":
    app.run(debug=True)
