from django.conf import settings

import core.musiq.song_utils as song_utils

import youtube_dl
import subprocess
import errno
import os

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

class Downloader:

    def __init__(self, musiq):
        self.musiq = musiq
        self.info_dict = None
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

    def check(self, target):
        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            self.info_dict = ydl.extract_info(target, download=False)
        # this value is not an exact match, but it's a good approximation
        if 'entries' in self.info_dict:
            self.info_dict = self.info_dict['entries'][0]
        size = self.info_dict['filesize']
        max_size = self.musiq.base.settings.max_download_size * 1024 * 1024
        if max_size != 0 and song_utils.path_from_id(self.info_dict['id']) is None and size > max_size:
            raise SongTooLargeException('Song too long')

    def fetch(self, target):
        # check if file was already downloaded and only download if necessary
        location = song_utils.path_from_id(self.info_dict['id'])
        if location is not None:
            return location

        with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
            ydl.download([target])

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

