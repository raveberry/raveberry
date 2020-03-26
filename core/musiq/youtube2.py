from django.conf import settings


import youtube_dl
import subprocess
import requests
import pickle
import errno
import json
import os


def get_initial_data(html):
    for line in html.split('\n'):
        line = line.strip()
        prefix = 'window["ytInitialData"] = '
        if line.startswith(prefix):
            # strip assignment and semicolon
            initial_data = line[len(prefix):-1]
            initial_data = json.loads(initial_data)
            return initial_data


def get_suggestion(url):
    session = requests.session()
    try:
        with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'rb') as f:
            session.cookies.update(pickle.load(f))
    except FileNotFoundError:
        pass

    headers = {
        'User-Agent': youtube_dl.utils.random_user_agent(),
    }
    r = session.get(url, headers=headers)

    with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'wb') as f:
        pickle.dump(session.cookies, f)

    initial_data = get_initial_data(r.text)
    url = initial_data['contents']['twoColumnWatchNextResults']['secondaryResults']['secondaryResults']['results'][0]['compactAutoplayRenderer']['contents'][0]['compactVideoRenderer']['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url']
    return 'https://www.youtube.com' + url


def search_playlist(query):
    session = requests.session()
    try:
        with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'rb') as f:
            session.cookies.update(pickle.load(f))
    except FileNotFoundError:
        pass

    headers = {
        'User-Agent': youtube_dl.utils.random_user_agent(),
    }
    params = {
            'search_query': query,
            # this is the value that youtube uses to filter for playlists only
            'sp': 'EgQQA1AD'
    }
    r = session.get('https://www.youtube.com/results', headers=headers, params=params)

    with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'wb') as f:
        pickle.dump(session.cookies, f)

    initial_data = get_initial_data(r.text)
    search_results = initial_data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']

    list_id = next(res['playlistRenderer']['playlistId'] for res in search_results if 'playlistRenderer' in res)
    return list_id

