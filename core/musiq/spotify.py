import mopidy_spotify
from django.http import HttpResponse

from core.musiq import song_utils
from core.musiq.music_provider import SongProvider, PlaylistProvider
from core.models import ArchivedSong, Setting
from mopidy_spotify.web import OAuthClient

from urllib.parse import urlparse

from core.models import ArchivedSong, ArchivedPlaylist

_web_client = None
def get_web_client():
    global _web_client
    if _web_client is None:
        client_id = Setting.objects.get(key='spotify_client_id').value
        client_secret = Setting.objects.get(key='spotify_client_secret').value
        _web_client = OAuthClient(
            base_url="https://api.spotify.com/v1",
            refresh_url="https://auth.mopidy.com/spotify/token",
            client_id=client_id,
            client_secret=client_secret)
    return _web_client

def get_search_suggestions(query, playlist):
    web_client = get_web_client()
    result = web_client.get(
        "search",
        params={
            'q': query,
            'limit': '10',
            'market': 'from_token',
            'type': 'playlist' if playlist else 'track',
        },
    )

    if playlist:
        items = result['playlists']['items']
    else:
        items = result['tracks']['items']

    suggestions = []
    for item in items:
        external_url = item['external_urls']['spotify']
        title = item['name']
        if playlist:
            displayname = title
        else:
            artist = item['artists'][0]['name']
            displayname = song_utils.displayname(artist, title)
        suggestions.append((displayname, external_url))

    # remove duplicates
    chosen_displaynames = set()
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion[0] in chosen_displaynames:
            continue
        unique_suggestions.append(suggestion)
        chosen_displaynames.add(suggestion[0])
    return unique_suggestions

class SpotifySongProvider(SongProvider):
    @staticmethod
    def get_id_from_external_url(url):
        return urlparse(url).path.split('/')[-1]

    @staticmethod
    def get_id_from_internal_url(url):
        return url.split(':')[-1]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = 'spotify'
        self.spotify_library = musiq.player.player.library
        self.metadata = dict()
        self.web_client = get_web_client()

    def check_cached(self):
        if self.query is not None and self.query.startswith('https://open.spotify.com/'):
            extracted_id = SpotifySongProvider.get_id_from_external_url(self.query)
            if extracted_id is not None:
                self.id = extracted_id

        if not self._check_cached():
            return False
        # Spotify songs cannot be cached and have to be streamed everytime
        return False

    def check_downloadable(self):
        if self.id is None:
            results = self.spotify_library.search({'any': [self.query]})

            try:
                track_info = results[0].tracks[0]
            except AttributeError:
                self.error = 'Song not found'
                return False
            self.id = SpotifySongProvider.get_id_from_internal_url(track_info.uri)
            self.gather_metadata(track_info=track_info)
        else:
            self.gather_metadata()

        return True

    def download(self, ip, background=True, archive=True, manually_requested=True):
        self.enqueue(ip, archive=archive, manually_requested=manually_requested)
        # spotify need to be streamed, no download possible
        return True

    def gather_metadata(self, track_info=None):
        if not track_info:
            results = self.spotify_library.search({'uri': [self.get_internal_url()]})
            track_info = results[0].tracks[0]

        self.metadata['internal_url'] = track_info.uri
        self.metadata['external_url'] = self.get_external_url()
        self.metadata['artist'] = track_info.artists[0].name
        self.metadata['title'] = track_info.name
        self.metadata['duration'] = track_info.length / 1000

    def get_metadata(self):
        if not self.metadata:
            self.gather_metadata()
        return self.metadata

    def get_internal_url(self):
        return 'spotify:track:' + self.id

    def get_external_url(self):
        return 'https://open.spotify.com/track/' + self.id

    def get_suggestion(self):
        result = self.web_client.get(
            'recommendations',
            params={
                'limit': '1',
                'market': 'from_token',
                'seed_tracks': self.id,
            },
        )

        try:
            external_url = result['tracks'][0]['external_urls']['spotify']
        except IndexError:
            self.error = 'no recommendation found'
            return None

        return external_url

    def request_radio(self, ip):
        result = self.web_client.get(
            'recommendations',
            params={
                'limit': self.musiq.base.settings.max_playlist_items,
                'market': 'from_token',
                'seed_tracks': self.id,
            },
        )

        for track in result['tracks']:
            external_url = track['external_urls']['spotify']
            self.musiq._request_music('', external_url, None, False, 'spotify', archive=False, manually_requested=False)

        return HttpResponse('queueing radio')

class SpotifyPlaylistProvider(PlaylistProvider):

    @staticmethod
    def get_id_from_external_url(url):
        if not url.startswith('https://open.spotify.com/playlist/'):
            return None
        return urlparse(url).path.split('/')[-1]

    def __init__(self, musiq, query, key):
        super().__init__(musiq, query, key)
        self.type = 'spotify'
        self.web_client = get_web_client()

    def search_id(self):
        result = self.web_client.get(
            "search",
            params={
                'q': self.query,
                'limit': '1',
                'market': 'from_token',
                'type': 'playlist',
            },
        )

        try:
            list_info = result['playlists']['items'][0]
        except IndexError:
            self.error = 'No playlist found'
            return None

        list_id = list_info['id']
        self.title = list_info['name']

        return list_id

    def is_radio(self):
        return False

    def fetch_metadata(self):
        if self.title is None:
            result = self.web_client.get(
                f"playlists/{self.id}",
                params={
                    'fields': 'name',
                    'limit': '50',
                },
            )
            self.title = result['name']

        # download at most 50 tracks for a playlist (spotifys maximum)
        # for more tracks paging would need to be implemented
        result = self.web_client.get(
            f"playlists/{self.id}/tracks",
            params={
                'fields': 'items(track(external_urls(spotify)))',
                'limit': '50',
                'market': 'from_token',
            },
        )

        track_infos = result['items']
        for track_info in track_infos:
            self.urls.append(track_info['track']['external_urls']['spotify'])
