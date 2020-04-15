from contextlib import contextmanager

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, HttpResponseBadRequest

import core.musiq.song_utils as song_utils

import youtube_dl
import subprocess
import requests
import pickle
import errno
import time
import json
import os
import threading
import mutagen.easymp4

from urllib.parse import urlparse
from urllib.parse import parse_qs

from core.models import ArchivedSong, ArchivedPlaylist, PlaylistEntry, ArchivedPlaylistQuery, \
    RequestLog
from core.musiq.music_provider import SongProvider, PlaylistProvider
from core.util import background_thread


class MyLogger(object):
    def debug(self, msg):
        if settings.DEBUG:
            print(msg)
    def warning(self, msg):
        if settings.DEBUG:
            print(msg)
    def error(self, msg):
        print(msg)

# youtube-dl --format bestaudio[ext=m4a]/best[ext=m4a] --output '%(id)s.%(ext)s --no-playlist --write-thumbnail --default-search auto --add-metadata --embed-thumbnail
def get_ydl_opts():
    return {
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

def get_initial_data(html):
    for line in html.split('\n'):
        line = line.strip()
        prefix = 'window["ytInitialData"] = '
        if line.startswith(prefix):
            # strip assignment and semicolon
            initial_data = line[len(prefix):-1]
            initial_data = json.loads(initial_data)
            return initial_data

# a context that opens a session and loads the cookies file
@contextmanager
def youtube_session():
    session = requests.session()
    try:
        with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'rb') as f:
            session.cookies.update(pickle.load(f))
    except FileNotFoundError:
        pass

    headers = {
        'User-Agent': youtube_dl.utils.random_user_agent(),
    }
    session.headers.update(headers)
    yield session

    with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'wb') as f:
        pickle.dump(session.cookies, f)

def get_search_suggestions(query):
    with youtube_session() as session:
        params = {
            'client': 'youtube',
            'q': query,
            'xhr': 't', # this makes the response be a json file
        }
        r = session.get('https://clients1.google.com/complete/search', params=params)
    suggestions = json.loads(r.text)
    # first entry is the query, the second one contains the suggestions
    suggestions = suggestions[1]
    # suggestions are given as tuples; extract the string and skip the query if it occurs identically
    suggestions = [entry[0] for entry in suggestions if entry[0] != query]
    return suggestions

class NoPlaylistException(Exception):
    pass

class Downloader:

    def get_playlist_info(self):
        self.ydl_opts = get_ydl_opts()

class YoutubeSongProvider(SongProvider):
    @staticmethod
    def get_id_from_external_url(url):
        return parse_qs(urlparse(url).query)['v'][0]

    @staticmethod
    def get_id_from_internal_url(url):
        return os.path.splitext(os.path.basename(url[len('file://'):]))[0]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = 'youtube'
        self.info_dict = None
        self.ydl_opts = get_ydl_opts()

    def check_cached(self):
        # TODO: in case query is set but key and id is not, try to extract the id from the query
        # example: https://youtu.be/<id>
        if not self._check_cached():
            return False
        return os.path.isfile(self.get_path())

    def check_downloadable(self):
        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                self.info_dict = ydl.extract_info(self.query, download=False)
        except youtube_dl.utils.DownloadError as e:
            self.error = e
            return False

        # this value is not an exact match, but it's a good approximation
        if 'entries' in self.info_dict:
            self.info_dict = self.info_dict['entries'][0]

        self.id = self.info_dict['id']

        size = self.info_dict['filesize']
        max_size = self.musiq.base.settings.max_download_size * 1024 * 1024
        if max_size != 0 and song_utils.path_from_id(self.info_dict['id']) is None and (size is not None and size > max_size):
            self.error = 'Song too long'
            return False
        return True

    @background_thread
    def _download(self, ip, archive, manually_requested):
        error = None
        location = None

        self.placeholder = {'query': self.query, 'replaced_by': None}
        self.musiq.placeholders.append(self.placeholder)
        self.musiq.update_state()

        try:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([self.get_external_url()])

            location = self.get_path()
            base = os.path.splitext(location)[0]
            thumbnail = base + '.jpg'
            try:
                os.remove(thumbnail)
            except FileNotFoundError:
                self.musiq.base.logger.info('tried to delete ' + thumbnail + ' but does not exist')

        except youtube_dl.utils.DownloadError as e:
            error = e

        if error is not None or location is None:
            self.musiq.logger.error('accessible video could not be downloaded: ' + str(self.id))
            self.musiq.logger.error(error)
            self.musiq.logger.error('location: ' + str(location))
            self.musiq.placeholders.remove(self.placeholder)
            self.musiq.update_state()
            return
        self.enqueue(ip, archive=archive, manually_requested=manually_requested)

    def download(self, ip, background=True, archive=True, manually_requested=True):
        # check if file was already downloaded and only download if necessary
        if os.path.isfile(self.get_path()):
            self.enqueue(ip, archive=archive, manually_requested=manually_requested)
        else:
            thread = self._download(ip, archive, manually_requested)
            if not background:
                thread.join()
        return True

    def get_metadata(self):
        metadata = song_utils.get_metadata(self.get_path())

        metadata['internal_url'] = self.get_internal_url()
        metadata['external_url'] = 'https://www.youtube.com/watch?v=' + self.id
        if not metadata['title']:
            metadata['title'] = metadata['external_url']

        return metadata

    def get_path(self):
        path = os.path.join(settings.SONGS_CACHE_DIR, self.id + '.m4a')
        path = path.replace('~', os.environ['HOME'])
        path = os.path.abspath(path)
        return path

    def get_internal_url(self):
        return 'file://' + self.get_path()

    def get_external_url(self):
        return 'https://www.youtube.com/watch?v=' + self.id

    def get_suggestion(self):
        with youtube_session() as session:
            r = session.get(self.get_external_url())

        initial_data = get_initial_data(r.text)
        url = initial_data['contents']['twoColumnWatchNextResults']['secondaryResults'][
            'secondaryResults']['results'][0]['compactAutoplayRenderer']['contents'][0][
            'compactVideoRenderer']['navigationEndpoint']['commandMetadata'][
            'webCommandMetadata']['url']
        return 'https://www.youtube.com' + url

    def request_radio(self, ip):
        radio_id = 'RD' + self.id

        provider = YoutubePlaylistProvider(self.musiq, 'radio for ' + self.id, None)
        provider.id = radio_id
        if not provider.download(ip):
            return HttpResponseBadRequest(provider.error)
        return HttpResponse('queueing radio')

class YoutubePlaylistProvider(PlaylistProvider):

    @staticmethod
    def get_id_from_external_url(url):
        try:
            list_id = parse_qs(urlparse(url).query)['list'][0]
        except KeyError:
            return None
        return list_id

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = 'youtube'
        self.ydl_opts = get_ydl_opts()
        del self.ydl_opts['noplaylist']
        self.ydl_opts['extract_flat'] = True

    def is_radio(self):
        return self.id.startswith('RD')

    def search_id(self):
        with youtube_session() as session:
            params = {
                'search_query': self.query,
                # this is the value that youtube uses to filter for playlists only
                'sp': 'EgQQA1AD'
            }
            r = session.get('https://www.youtube.com/results', params=params)

        initial_data = get_initial_data(r.text)
        section_renderers = \
            initial_data['contents']['twoColumnSearchResultsRenderer']['primaryContents'][
                'sectionListRenderer']['contents']

        list_id = None
        for section_renderer in section_renderers:
            search_results = section_renderer['itemSectionRenderer']['contents']

            try:
                list_id = next(res['playlistRenderer']['playlistId'] for res in search_results if
                               'playlistRenderer' in res)
                break
            except StopIteration:
                # the search result did not contain the list id
                pass

        return list_id

    def fetch_metadata(self):
        # in case of a radio playist, restrict the number of songs that are downloaded
        if self.is_radio():
            self.ydl_opts['playlistend'] = self.musiq.base.settings.max_playlist_items

        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            info_dict = ydl.extract_info(self.id, download=False)

        if info_dict['_type'] != 'playlist' or 'entries' not in info_dict:
            # query was not a playlist url -> search for the query
            assert False

        assert self.id == info_dict['id']
        if 'title' in info_dict:
            self.title = info_dict['title']
        for entry in info_dict['entries']:
            self.urls.append('https://www.youtube.com/watch?v=' + entry['id'])
        assert self.key is None
