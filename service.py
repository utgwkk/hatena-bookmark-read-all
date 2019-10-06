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
