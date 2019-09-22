from django.conf import settings

import core.musiq.song_utils as song_utils

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

class MyLogger(object):
    def debug(self, msg):
        if settings.DEBUG:
            print(msg)
    def warning(self, msg):
        if settings.DEBUG:
            print(msg)
    def error(self, msg):
        print(msg)

class SongTooLargeException(Exception):
    pass

class NoPlaylistException(Exception):
    pass

class Downloader:

    def __init__(self, musiq, target):
        self.musiq = musiq
        self.target = target
        self.info_dict = None
        # youtube-dl --format bestaudio[ext=m4a]/best[ext=m4a] --output '%(id)s.%(ext)s --no-playlist --write-thumbnail --default-search auto --add-metadata --embed-thumbnail
        self.ydl_opts = {
            'format': 'bestaudio[ext=m4a]/best[ext=m4a]',
            'outtmpl': os.path.join(settings.SONGS_CACHE_DIR, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'no_color': True,
            'writethumbnail': True,
            'default_search': 'auto',
            'postprocessors': [{
                    'key': 'FFmpegMetadata',
                }, {
                    'key': 'EmbedThumbnail',
                    # overwrite any thumbnails already present
                    'already_have_thumbnail': True,
                }],
            'logger': MyLogger(),
        }

    def get_playlist_info(self):
        del self.ydl_opts['noplaylist']
        self.ydl_opts['extract_flat'] = True

        # in case of a radio playist, restrict the number of songs that are downloaded
        # if we received just the id, it is an id starting with 'RD'
        # if its a url, the id is behind a '&list='
        if song_utils.is_radio(self.target):
            self.ydl_opts['playlistend'] = self.musiq.base.settings.max_playlist_items

        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            self.info_dict = ydl.extract_info(self.target, download=False)

        if self.info_dict['_type'] != 'playlist' or 'entries' not in self.info_dict:
            raise NoPlaylistException('Not a Playlist')

        playlist_info = {}
        playlist_info['id'] = self.info_dict['id']
        playlist_info['urls'] = []
        if 'title' in self.info_dict:
            playlist_info['title'] = self.info_dict['title']
        for entry in self.info_dict['entries']:
            playlist_info['urls'].append('https://www.youtube.com/watch?v=' + entry['id'])
        return playlist_info

    def check(self):
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            self.info_dict = ydl.extract_info(self.target, download=False)
        # this value is not an exact match, but it's a good approximation
        if 'entries' in self.info_dict:
            self.info_dict = self.info_dict['entries'][0]
        size = self.info_dict['filesize']
        max_size = self.musiq.base.settings.max_download_size * 1024 * 1024
        if max_size != 0 and song_utils.path_from_id(self.info_dict['id']) is None and size > max_size:
            raise SongTooLargeException('Song too long')

    def fetch(self):
        # check if file was already downloaded and only download if necessary
        location = song_utils.path_from_id(self.info_dict['id'])
        if location is not None:
            return location

        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([self.target])

        location = song_utils.path_from_id(self.info_dict['id'])
        base = os.path.splitext(location)[0]
        thumbnail = base + '.jpg'
        try:
            os.remove(thumbnail)
        except FileNotFoundError:
            self.musiq.base.logger.info('tried to delete ' + thumbnail + ' but does not exist')

        try:
            # tag the file with replaygain to perform volume normalization
            subprocess.call(['aacgain', '-q', '-c', location], stdout=subprocess.DEVNULL)
        except OSError as e:
            if e.errno == errno.ENOENT:
                # the aacgain package was not found. Skip normalization
                pass
            else:
                raise
                
        return location

if __name__ == '__main__':
    Downloader().fetch()

