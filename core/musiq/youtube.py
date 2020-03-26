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
from core.musiq.music_provider import MusicProvider

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

class NoPlaylistException(Exception):
    pass

class Downloader:

    def get_playlist_info(self):
        self.ydl_opts = get_ydl_opts()

class YoutubeProvider(MusicProvider):
    @staticmethod
    def create(musiq, internal_url=None, external_url=None):
        provider = YoutubeProvider(musiq, None, None)
        if internal_url is not None:
            provider.id = YoutubeProvider.get_id_from_internal_url(internal_url)
        elif external_url is not None:
            provider.id = YoutubeProvider.get_id_from_external_url(external_url)
        return provider

    @staticmethod
    def get_id_from_external_url(url):
        return parse_qs(urlparse(url).query)['v'][0]

    @staticmethod
    def get_id_from_internal_url(url):
        return os.path.splitext(os.path.basename(url[len('file://'):]))[0]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.ok_response = 'song queued'
        self.info_dict = None
        self.ydl_opts = get_ydl_opts()

    def check_cached(self):
        if self.id is not None:
            archived_song = ArchivedSong.objects.get(url=self.get_external_url())
        elif self.key is not None:
            archived_song = ArchivedSong.objects.get(id=self.key)
        else:
            try:
                archived_song = ArchivedSong.objects.get(url=self.query)
                # TODO check for other yt url formats (youtu.be)
            except ArchivedSong.DoesNotExist:
                return False
        self.id = YoutubeProvider.get_id_from_external_url(archived_song.url)
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
        if max_size != 0 and song_utils.path_from_id(self.info_dict['id']) is None and (size is None or size > max_size):
            self.error = 'Song too long'
            return False
        return True

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

            try:
                # tag the file with replaygain to perform volume normalization
                subprocess.call(['aacgain', '-q', '-c', location], stdout=subprocess.DEVNULL)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    pass  # the aacgain package was not found. Skip normalization
                else:
                    raise

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
            thread = threading.Thread(target=self._download, args=(ip, archive, manually_requested), daemon=True)
            thread.start()
            if not background:
                thread.join()
        return True

    def get_metadata(self):
        '''gathers the metadata for the song at the given location.
        'title' and 'duration' is read from tags, the 'url' is built from the location'''

        parsed = mutagen.easymp4.EasyMP4(self.get_path())
        metadata = dict()

        metadata['internal_url'] = self.get_internal_url()
        metadata['external_url'] = 'https://www.youtube.com/watch?v=' + self.id

        if parsed.tags is not None:
            if 'artist' in parsed.tags:
                metadata['artist'] = parsed.tags['artist'][0]
            if 'title' in parsed.tags:
                metadata['title'] = parsed.tags['title'][0]
        if 'artist' not in metadata:
            metadata['artist'] = ''
        if 'title' not in metadata:
            metadata['title'] = metadata['external_url']
        if parsed.info is not None and parsed.info.length is not None:
            metadata['duration'] = parsed.info.length
        else:
            metadata['duration'] = -1

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
        session = requests.session()
        try:
            with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'rb') as f:
                session.cookies.update(pickle.load(f))
        except FileNotFoundError:
            pass

        headers = {
            'User-Agent': youtube_dl.utils.random_user_agent(),
        }
        r = session.get(self.get_external_url(), headers=headers)

        with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'wb') as f:
            pickle.dump(session.cookies, f)

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

class YoutubePlaylistProvider(MusicProvider):

    @staticmethod
    def get_id_from_external_url(url):
        return parse_qs(urlparse(url).query)['list'][0]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.ok_response = 'queueing playlist'
        self.ydl_opts = get_ydl_opts()
        del self.ydl_opts['noplaylist']
        self.ydl_opts['extract_flat'] = True

    def is_radio(self):
        return self.id.startswith('RD')

    def check_cached(self):
        if self.key is not None:
            archived_playlist = ArchivedPlaylist.objects.get(id=self.key)
        else:
            try:
                list_id = YoutubePlaylistProvider.get_id_from_external_url(self.query)
                archived_playlist = ArchivedPlaylist.objects.get(list_id=list_id)
            except (KeyError, ArchivedSong.DoesNotExist):
                return False
        self.id = archived_playlist.list_id
        self.key = archived_playlist.id
        return True

    def search_id(self):
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
            'search_query': self.query,
            # this is the value that youtube uses to filter for playlists only
            'sp': 'EgQQA1AD'
        }
        r = session.get('https://www.youtube.com/results', headers=headers, params=params)

        with open(os.path.join(settings.BASE_DIR, 'config/youtube_cookies.pickle'), 'wb') as f:
            pickle.dump(session.cookies, f)

        initial_data = get_initial_data(r.text)
        search_results = \
            initial_data['contents']['twoColumnSearchResultsRenderer']['primaryContents'][
                'sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']

        list_id = next(res['playlistRenderer']['playlistId'] for res in search_results if
                       'playlistRenderer' in res)
        return list_id

    def check_downloadable(self):
        try:
            self.id = YoutubePlaylistProvider.get_id_from_external_url(self.query)
        except KeyError:
            self.id = self.search_id()
        return True

    def download(self, ip, background=True, archive=True, manually_requested=True):

        queryset = ArchivedPlaylist.objects.filter(list_id=self.id)
        if not self.is_radio() and queryset.exists():
            self.key = queryset.get().id
        else:
            # in case of a radio playist, restrict the number of songs that are downloaded
            self.ydl_opts['playlistend'] = self.musiq.base.settings.max_playlist_items

            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.id, download=False)

            if info_dict['_type'] != 'playlist' or 'entries' not in info_dict:
                # query was not a playlist url -> search for the query
                assert False

            assert self.id == info_dict['id']
            self.urls = []
            self.title = None
            if 'title' in info_dict:
                self.title = info_dict['title']
            for entry in info_dict['entries']:
                self.urls.append('https://www.youtube.com/watch?v=' + entry['id'])
            assert self.key is None

        self.enqueue(ip)
        return True

    def _queue_songs(self, ip, archived_playlist):
        for index, entry in enumerate(archived_playlist.entries.all()):
            if index == self.musiq.base.settings.max_playlist_items:
                break
            # request every url in the playlist as their own url
            song_provider = YoutubeProvider(self.musiq, query=entry.url, key=None)

            if not song_provider.check_cached():
                if not song_provider.check_downloadable():
                    # song is not downloadable, continue with next song in playlist
                    continue
                if not song_provider.download(ip, background=False, archive=False, manually_requested=False):
                    # error during song download, continue with next song in playlist
                    continue
            else:
                song_provider.enqueue('', archive=False, manually_requested=False)

            if settings.DEBUG:
                # the sqlite database has problems if songs are pushed very fast while a new song is taken from the queue. Add a delay to mitigate.
                time.sleep(1)

    def enqueue(self, ip, archive=True, manually_requested=True):
        if self.key is None:
            with transaction.atomic():

                archived_playlist = ArchivedPlaylist.objects.create(list_id=self.id,
                                                                    title=self.title, counter=1)
                for index, url in enumerate(self.urls):
                    PlaylistEntry.objects.create(
                        playlist=archived_playlist,
                        index=index,
                        url=url,
                    )
        else:
            assert not self.is_radio()
            queryset = ArchivedPlaylist.objects.filter(list_id=self.id)

            if archive:
                queryset.update(counter=F('counter') + 1)
            archived_playlist = queryset.get()

        ArchivedPlaylistQuery.objects.get_or_create(playlist=archived_playlist, query=self.query)

        if self.musiq.base.settings.logging_enabled:
            RequestLog.objects.create(playlist=archived_playlist, address=ip)

        thread = threading.Thread(target=self._queue_songs, args=(ip, archived_playlist), daemon=True)
        thread.start()

if __name__ == '__main__':
    Downloader().fetch()

