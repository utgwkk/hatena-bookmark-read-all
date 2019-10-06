from os import environ

# Constants
CONSUMER_KEY = environ.get('CONSUMER_KEY')
CONSUMER_SECRET = environ.get('CONSUMER_SECRET')
REQUEST_TOKEN_URL = 'https://www.hatena.com/oauth/initiate'
AUTHORIZE_URL = 'https://www.hatena.ne.jp/oauth/authorize'
AUTHORIZE_URL_SP = 'https://www.hatena.ne.jp/touch/oauth/authorize'
CALLBACK_URL = environ.get('CALLBACK_URL')
GET_ACCESS_TOKEN_URL = 'https://www.hatena.com/oauth/token'
SCOPE = 'read_public,read_private,write_public,write_private'
SMARTPHONE_USER_AGENT = ['iPhone', 'iPad',
                         'Android', 'Mobile', 'Phone', 'Nexus']

SECRET_KEY = environ.get('SECRET_KEY')
