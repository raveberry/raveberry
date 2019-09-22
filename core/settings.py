from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.utils import dateparse
from django.utils import timezone
from django.db import models
from django.conf import settings

from core.models import Setting
from core.models import PlayLog
from core.models import RequestLog
import core.state_handler as state_handler
import core.musiq.song_utils as song_utils

from functools import wraps
from datetime import timedelta
from dateutil import tz
import urllib.request
import subprocess
import threading
import time
import math
import os
import re

class Settings:

    def __init__(self, base):
        self.base = base
        self.voting_system = Setting.objects.get_or_create(key='voting_system', defaults={'value': False})[0].value == 'True'
        self.logging_enabled = Setting.objects.get_or_create(key='logging_enabled', defaults={'value': True})[0].value == 'True'
        self.people_to_party = int(Setting.objects.get_or_create(key='people_to_party', defaults={'value': 3})[0].value)
        self.alarm_probability = float(Setting.objects.get_or_create(key='alarm_probability', defaults={'value': 0})[0].value)
        self.downvotes_to_kick = int(Setting.objects.get_or_create(key='downvotes_to_kick', defaults={'value': 3})[0].value)
        self.max_download_size = int(Setting.objects.get_or_create(key='max_download_size', defaults={'value': 10})[0].value)
        self.max_playlist_items = int(Setting.objects.get_or_create(key='max_playlist_items', defaults={'value': 10})[0].value)
        self._check_internet()
        self.bluetoothctl = None
        self.bluetooth_devices = []
        self.homewifi = Setting.objects.get_or_create(key='homewifi', defaults={'value': ''})[0].value

    def state_dict(self):
        state_dict = self.base.state_dict()
        state_dict['voting_system'] = self.voting_system
        state_dict['logging_enabled'] = self.logging_enabled
        state_dict['people_to_party'] = self.people_to_party
        state_dict['alarm_probability'] = self.alarm_probability
        state_dict['downvotes_to_kick'] = self.downvotes_to_kick
        state_dict['max_download_size'] = self.max_download_size
        state_dict['max_playlist_items'] = self.max_playlist_items
        state_dict['has_internet'] = self.has_internet

        state_dict['bluetooth_scanning'] = self.bluetoothctl is not None
        state_dict['bluetooth_devices'] = self.bluetooth_devices

        try:
            with open(os.path.join(settings.BASE_DIR, 'config/homewifi')) as f:
                state_dict['homewifi_ssid'] = f.read()
        except FileNotFoundError:
            state_dict['homewifi_ssid'] = ''

        try:
            state_dict['homewifi_enabled'] = subprocess.call(['/usr/local/sbin/raveberry/homewifi_enabled']) != 0
            state_dict['events_enabled'] = subprocess.call(['/usr/local/sbin/raveberry/events_enabled']) != 0
            state_dict['hotspot_enabled'] = subprocess.call(['/usr/local/sbin/raveberry/hotspot_enabled']) != 0
            state_dict['wifi_protected'] = subprocess.call(['/usr/local/sbin/raveberry/wifi_protected']) != 0
            state_dict['tunneling_enabled'] = subprocess.call(['sudo', '/usr/local/sbin/raveberry/tunneling_enabled']) != 0
            state_dict['remote_enabled'] = subprocess.call(['/usr/local/sbin/raveberry/remote_enabled']) != 0
        except FileNotFoundError:
            self.base.logger.error('scripts not installed')

        return state_dict

    def get_state(self, request):
        state = self.state_dict()
        return JsonResponse(state)

    def update_state(self):
        state_handler.update_state(self.state_dict())

    def index(self, request):
        if not self.base.user_manager.is_admin(request.user):
            raise PermissionDenied
        context = self.base.context(request)
        return render(request, 'settings.html', context)

    def _check_internet(self):
        response = subprocess.call(['ping','-c','1','-W','3','1.1.1.1'], stdout=subprocess.DEVNULL)
        if response == 0:
            self.has_internet = True
        else:
            self.has_internet = False

    # settings can only be changed by admin
    def option(func):
        def _decorator(self, request, *args, **kwargs):
            # don't allow option changes during alarm
            if request.user.username != 'admin':
                return HttpResponseForbidden()
            response = func(self, request, *args, **kwargs)
            if response is not None:
                return response
            self.update_state()
            return HttpResponse()
        return wraps(func)(_decorator)

    @option
    def set_voting_system(self, request):
        enabled = request.POST.get('value') == 'true'
        Setting.objects.filter(key='voting_system').update(value=enabled)
        self.voting_system = enabled
    @option
    def set_logging_enabled(self, request):
        enabled = request.POST.get('value') == 'true'
        Setting.objects.filter(key='logging_enabled').update(value=enabled)
        self.logging_enabled = enabled
    @option
    def set_people_to_party(self, request):
        value = int(request.POST.get('value'))
        Setting.objects.filter(key='people_to_party').update(value=value)
        self.people_to_party = value
    @option
    def set_alarm_probability(self, request):
        value = float(request.POST.get('value'))
        Setting.objects.filter(key='alarm_probability').update(value=value)
        self.alarm_probability = value
    @option
    def set_downvotes_to_kick(self, request):
        value = int(request.POST.get('value'))
        Setting.objects.filter(key='downvotes_to_kick').update(value=value)
        self.downvotes_to_kick = value
    @option
    def set_max_download_size(self, request):
        value = int(request.POST.get('value'))
        Setting.objects.filter(key='max_download_size').update(value=value)
        self.max_download_size = value
    @option
    def set_max_playlist_items(self, request):
        value = int(request.POST.get('value'))
        Setting.objects.filter(key='max_playlist_items').update(value=value)
        self.max_playlist_items = value
    @option
    def check_internet(self, request):
        self._check_internet()
    @option
    def update_user_count(self, request):
        self.base.user_manager.update_user_count()

    def _get_bluetoothctl_line(self):
        # Note: this variable is not guarded by a lock. 
        # But there should only be one admin accessing these bluetooth functions anyway.
        if self.bluetoothctl is None:
            return ''
        line = self.bluetoothctl.stdout.readline().decode()
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        line = ansi_escape.sub('', line)
        line = line.strip()
        return line
    def _stop_bluetoothctl(self):
        self.bluetoothctl.stdin.close()
        self.bluetoothctl.wait()
        self.bluetoothctl = None
    @option
    def set_bluetooth_scanning(self, request):
        enabled = request.POST.get('value') == 'true'
        if enabled:
            if self.bluetoothctl is not None:
                return HttpResponseBadRequest('Already Scanning')
            self.bluetooth_devices = []
            self.bluetoothctl = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

            self.bluetoothctl.stdin.write(b'devices\n')
            self.bluetoothctl.stdin.write(b'scan on\n')
            self.bluetoothctl.stdin.flush()
            while True:
                line = self._get_bluetoothctl_line()
                if not line:
                    break
                # match old devices
                match = re.match('Device (\S*) (.*)', line)
                # match newly scanned devices
                # We need the '.*' at the beginning of the line to account for control sequences 
                if not match:
                    match = re.match('.*\[NEW\] Device (\S*) (.*)', line)
                if match:
                    address = match.group(1)
                    name = match.group(2)
                    # filter unnamed devices
                    # devices named after their address are no speakers
                    if re.match('[A-Z0-9][A-Z0-9](-[A-Z0-9][A-Z0-9]){5}', name):
                        continue
                    self.bluetooth_devices.append({
                        'address': address,
                        'name': name,
                    })
                    self.update_state()
        else:
            if self.bluetoothctl is None:
                return HttpResponseBadRequest('Currently not scanning')
            self._stop_bluetoothctl()
    @option
    def connect_to_bluetooth_device(self, request):
        address = request.POST.get('address')
        if self.bluetoothctl is not None:
            return HttpResponseBadRequest('Stop scanning before connecting')
        if address is None or address is '':
            return HttpResponseBadRequest('No device selected')

        self.bluetoothctl = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        error = ''

        # A Function that acts as a timeout for unexpected errors (or timeouts)
        def timeout():
            time.sleep(20)
            error = 'Timed out'
            if self.bluetoothctl is not None:
                self._stop_bluetoothctl()
        threading.Thread(target=timeout, daemon=True).start()

        self.bluetoothctl.stdin.write(b'pair ' + address.encode() + b'\n')
        self.bluetoothctl.stdin.flush()
        while True:
            line = self._get_bluetoothctl_line()
            if not line:
                break
            if re.match('.*Device ' + address + ' not available', line):
                error = 'Device unavailable'
                break
            elif re.match('.*Failed to pair: org.bluez.Error.AlreadyExists', line):
                break
            elif re.match('.*Pairing successful', line):
                break

        if error:
            self._stop_bluetoothctl()
            return HttpResponseBadRequest(error)

        self.bluetoothctl.stdin.write(b'connect ' + address.encode() + b'\n')
        self.bluetoothctl.stdin.flush()
        while True:
            line = self._get_bluetoothctl_line()
            if not line:
                break
            if re.match('.*Device ' + address + ' not available', line):
                error = 'Device unavailable'
                break
            elif re.match('.*Failed to connect: org.bluez.Error.Failed', line):
                error = 'Connect Failed'
                break
            elif re.match('.*Failed to connect: org.bluez.Error.InProgress', line):
                error = 'Connect in progress'
                break
            elif re.match('.*Connection successful', line):
                break
        # trust the device to automatically reconnect when it is available again
        self.bluetoothctl.stdin.write(b'trust ' + address.encode() + b'\n')
        self.bluetoothctl.stdin.flush()

        self._stop_bluetoothctl()
        if error:
            return HttpResponseBadRequest(error)

        # Update mpd's config to output to the bluetooth device
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/update_bluetooth_device', address])
        return HttpResponse('Connected')

    @option
    def available_ssids(self, request):
        output = subprocess.check_output(['sudo', '/usr/local/sbin/raveberry/list_available_ssids'])
        output = output.decode()
        ssids = output.split('\n')
        print(ssids)
        return JsonResponse(ssids[:-1], safe=False)
    @option
    def connect_to_wifi(self, request):
        ssid = request.POST.get('ssid')
        password = request.POST.get('password')
        if ssid is None or password is None \
                or ssid == '' or password == '':
            return HttpResponseBadRequest('Please provide both SSID and password')
        try:
            output = subprocess.check_output(['sudo', '/usr/local/sbin/raveberry/connect_to_wifi', ssid, password])
            output = output.decode()
            return HttpResponse(output)
        except subprocess.CalledProcessError as e:
            output = e.output.decode()
            return HttpResponseBadRequest(output)
    @option
    def disable_homewifi(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/disable_homewifi'])
    @option
    def enable_homewifi(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/enable_homewifi'])
    @option
    def stored_ssids(self, request):
        output = subprocess.check_output(['sudo', '/usr/local/sbin/raveberry/list_stored_ssids'])
        output = output.decode()
        ssids = output.split('\n')
        return JsonResponse(ssids[:-1], safe=False)
    @option
    def set_homewifi_ssid(self, request):
        homewifi_ssid = request.POST.get('homewifi_ssid')
        with open(os.path.join(settings.BASE_DIR, 'config/homewifi'), 'w+') as f:
            f.write(homewifi_ssid)

    @option
    def analyse(self, request):
        startdate = request.POST.get('startdate')
        starttime = request.POST.get('starttime')
        enddate = request.POST.get('enddate')
        endtime = request.POST.get('endtime')
        if startdate is None or startdate == '' \
                or starttime is None or starttime == '' \
                or enddate is None or enddate == '' \
                or endtime is None or endtime == '':
            return HttpResponseBadRequest('All fields are required')

        start = dateparse.parse_datetime(startdate + 'T' + starttime)
        end = dateparse.parse_datetime(enddate + 'T' + endtime)

        if start is None or end is None:
            return HttpResponseBadRequest('invalid start-/endtime given')
        if start >= end:
            return HttpResponseBadRequest('start has to be before end')

        start = timezone.make_aware(start)
        end = timezone.make_aware(end)

        played = PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end)
        requested = RequestLog.objects.all().filter(created__gte=start).filter(created__lt=end)
        played_count = played.values('song__url', 'song__artist', 'song__title').values('song__url', 'song__artist', 'song__title', count=models.Count('song__url')).order_by('-count')
        played_votes = PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end).order_by('-votes')
        devices = requested.values('address').values('address', count=models.Count('address'))
        
        response = {}
        response['songs_played'] = len(played);
        response['most_played_song'] = song_utils.displayname(
                played_count[0]['song__artist'],
                played_count[0]['song__title']) + ' (' + str(played_count[0]['count']) + ')'
        response['highest_voted_song'] = played_votes[0].song.displayname() + ' (' + str(played_votes[0].votes) + ')'
        response['most_active_device'] = devices[0]['address'] + ' (' + str(devices[0]['count']) + ')'
        requested_by_ip = requested.filter(address=devices[0]['address'])
        for i in range(6):
            if i >= len(requested_by_ip):
                break
            response['most_active_device'] += '\n'
            if i == 5:
                response['most_active_device'] += '...'
            else:
                response['most_active_device'] += requested_by_ip[i].song.displayname()


        binsize = 3600
        number_of_bins = math.ceil((end - start).total_seconds() / binsize)
        request_bins = [0 for _ in range(number_of_bins)]

        for r in requested:
            seconds = (r.created - start).total_seconds()
            index = int(seconds / binsize)
            request_bins[index] += 1

        current_time = start
        current_index = 0
        response['request_activity'] = ''
        while current_time < end:
            response['request_activity'] += current_time.strftime('%H:%M') 
            response['request_activity'] += ':\t' + str(request_bins[current_index])
            response['request_activity'] += '\n'
            current_time += timedelta(seconds=binsize)
            current_index += 1

        localtz = tz.gettz(settings.TIME_ZONE)
        playlist = ''
        for log in played:
            localtime = log.created.astimezone(localtz)
            playlist += '[{:02d}:{:02d}] {}\n'.format(localtime.hour, localtime.minute, log.song.displayname())
        response['playlist'] = playlist

        return JsonResponse(response)

    @option
    def disable_events(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/disable_events'])
    @option
    def enable_events(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/enable_events'])
    @option
    def disable_hotspot(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/disable_hotspot'])
    @option
    def enable_hotspot(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/enable_hotspot'])
    @option
    def unprotect_wifi(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/unprotect_wifi'])
    @option
    def protect_wifi(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/protect_wifi'])
    @option
    def disable_tunneling(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/disable_tunneling'])
    @option
    def enable_tunneling(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/enable_tunneling'])
    @option
    def disable_remote(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/disable_remote'])
    @option
    def enable_remote(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/enable_remote'])
    @option
    def reboot_server(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/reboot_server'])
    @option
    def reboot_system(self, request):
        subprocess.call(['sudo', '/usr/local/sbin/raveberry/reboot_system'])
