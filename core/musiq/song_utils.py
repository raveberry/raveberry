from django.conf import settings

from urllib.parse import urlparse
from urllib.parse import parse_qs
import os
import mutagen.easymp4

def path_from_id(song_id):
    path = os.path.join(settings.SONGS_CACHE_DIR, song_id + '.m4a')
    path = path.replace('~', os.environ['HOME'])
    path = os.path.abspath(path)
    if os.path.isfile(path):
        return path
    else:
        return None

def path_from_url(url):
    ''' returns the file path for the song corresponding to the given url or None if the url is not cached '''
    song_id = id_from_url(url)
    return path_from_id(song_id)

def id_from_url(url):
    return parse_qs(urlparse(url).query)['v'][0]

def is_radio(id_or_url):
    return id_or_url.split('&list=')[-1].startswith('RD')

def determine_playlist_type(archived_playlist):
    # use the url of the first song in the playlist to determine the platform where the playlist is from
    first_song_url = archived_playlist.entries.first().url
    if first_song_url.startswith('local_library/'):
        return 'local'
    elif first_song_url.startswith('https://www.youtube.com/'):
        return 'youtube'
    elif first_song_url.startswith('https://open.spotify.com/'):
        return 'spotify'
    else:
        return None

def format_seconds(seconds):
    hours, seconds =  seconds // 3600, seconds % 3600
    minutes, seconds = seconds // 60, seconds % 60

    formatted = ''
    if hours > 0:
        formatted += '{:02d}:'.format(int(hours))
    formatted += '{0:02d}:{1:02d}'.format(int(minutes), int(seconds))
    return formatted

def get_duration(location):
    parsed = mutagen.File(location)
    return parsed.info.length

def gather_metadata(location):
    pass

def decide_deletion(location):
    return
    ''' takes the path to a song file and deletes it if it is larger than a threshold '''
    '''size = os.path.getsize(location)
    if size > settings.MAX_SONG_SIZE:
        os.remove(location)'''

def displayname(artist, title):
    if artist == '':
        return title
    else:
        return artist + ' – ' + title

def format_seconds(seconds):
    hours, seconds = seconds // 3600, seconds % 3600
    minutes, seconds = seconds // 60, seconds % 60

    formatted = ''
    if hours > 0:
        formatted += '{:02d}:'.format(int(hours))
    formatted += '{0:02d}:{1:02d}'.format(int(minutes), int(seconds))
    return formatted

def get_metadata(path):
    '''gathers the metadata for the song at the given location.
    'title' and 'duration' is read from tags, the 'url' is built from the location'''

    parsed = mutagen.File(path, easy=True)
    if parsed is None:
        raise ValueError
    metadata = dict()

    if parsed.tags is not None:
        if 'artist' in parsed.tags:
            metadata['artist'] = parsed.tags['artist'][0]
        if 'title' in parsed.tags:
            metadata['title'] = parsed.tags['title'][0]
    if 'artist' not in metadata:
        metadata['artist'] = ''
    if 'title' not in metadata:
        metadata['title'] = os.path.split(path)[1]
    if parsed.info is not None and parsed.info.length is not None:
        metadata['duration'] = parsed.info.length
    else:
        metadata['duration'] = -1

    return metadata
