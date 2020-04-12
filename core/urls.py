from django.urls import include
from django.urls import path
from django.contrib import admin
from django.views.generic import RedirectView

import os

if os.environ.get('DJANGO_MOCK'):
    import core.mock
    urlpatterns = [
        path('', core.mock.index),
    ]
else:
    from core.base import Base
    base = Base()

    urlpatterns = [
        path('', RedirectView.as_view(pattern_name='musiq', permanent=False), name='base'),

        path('musiq/', base.musiq.index, name='musiq'),
        path('lights/', base.lights.index, name='lights'),
        path('pad/', base.pad.index, name='pad'),
        path('settings/', base.settings.index, name='settings'),
        path('accounts/', include('django.contrib.auth.urls')),
        path('login/', RedirectView.as_view(pattern_name='login', permanent=False)),
        path('logged_in/', base.logged_in, name='logged_in'),
        path('logout/', RedirectView.as_view(pattern_name='logout', permanent=False)),

        path('ajax/', include([
            path('state/', base.get_state, name='base_state'),
            path('submit_hashtag/', base.submit_hashtag, name='submit_hashtag'),
            path('musiq/', include([
                path('state/', base.musiq.get_state, name='musiq_state'),
                path('random_suggestion/', base.musiq.suggestions.random_suggestion, name='random_suggestion'),
                path('request_music/', base.musiq.request_music, name='request_music'),
                path('suggestions/', base.musiq.suggestions.get_suggestions, name='suggestions'),

                path('restart/', base.musiq.player.restart, name='restart_song'),
                path('seek_backward/', base.musiq.player.seek_backward, name='seek_backward'),
                path('play/', base.musiq.player.play, name='play_song'),
                path('pause/', base.musiq.player.pause, name='pause_song'),
                path('seek_forward/', base.musiq.player.seek_forward, name='seek_forward'),
                path('skip/', base.musiq.player.skip, name='skip_song'),
                path('set_shuffle/', base.musiq.player.set_shuffle, name='set_shuffle'),
                path('set_repeat/', base.musiq.player.set_repeat, name='set_repeat'),
                path('set_autoplay/', base.musiq.player.set_autoplay, name='set_autoplay'),
                path('request_radio/', base.musiq.request_radio, name='request_radio'),
                path('set_volume/', base.musiq.player.set_volume, name='set_volume'),
                path('remove_all/', base.musiq.player.remove_all, name='remove_all'),

                path('prioritize/', base.musiq.player.prioritize, name='prioritize_song'),
                path('remove/', base.musiq.player.remove, name='remove_song'),
                path('reorder/', base.musiq.player.reorder, name='reorder_song'),
                path('vote_up/', base.musiq.player.vote_up, name='vote_up_song'),
                path('vote_down/', base.musiq.player.vote_down, name='vote_down_song'),

                path('start_loop/', base.musiq.player.start_loop, name='start_player_loop'),
                path('stop_loop/', base.musiq.player.stop_loop, name='stop_player_loop'),
            ])),
            path('lights/', include([
                path('state/', base.lights.get_state, name='lights_state'),
                path('shortcut/', base.lights.set_lights_shortcut, name='set_lights_shortcut'),
                path('set_ring_program/', base.lights.set_ring_program, name='set_ring_program'),
                path('set_ring_brightness/', base.lights.set_ring_brightness, name='set_ring_brightness'),
                path('set_ring_monochrome/', base.lights.set_ring_monochrome, name='set_ring_monochrome'),
                path('set_strip_program/', base.lights.set_strip_program, name='set_strip_program'),
                path('set_strip_brightness/', base.lights.set_strip_brightness, name='set_strip_brightness'),
                path('adjust_screen/', base.lights.adjust_screen, name='adjust_screen'),
                path('set_screen_program/', base.lights.set_screen_program, name='set_screen_program'),
                path('set_program_speed/', base.lights.set_program_speed, name='set_program_speed'),
                path('set_fixed_color/', base.lights.set_fixed_color, name='set_fixed_color'),
            ])),
            path('pad/', include([
                path('state/', base.pad.get_state, name='pad_state'),
                path('submit/', base.pad.submit, name='submit_pad'),
            ])),
            path('settings/', include([
                path('state/', base.settings.get_state, name='settings_state'),
                path('set_voting_system/', base.settings.set_voting_system, name='set_voting_system'),
                path('set_logging_enabled/', base.settings.set_logging_enabled, name='set_logging_enabled'),
                path('set_people_to_party/', base.settings.set_people_to_party, name='set_people_to_party'),
                path('set_alarm_probability/', base.settings.set_alarm_probability, name='set_alarm_probability'),
                path('set_downvotes_to_kick/', base.settings.set_downvotes_to_kick, name='set_downvotes_to_kick'),
                path('set_max_download_size/', base.settings.set_max_download_size, name='set_max_download_size'),
                path('set_max_playlist_items/', base.settings.set_max_playlist_items, name='set_max_playlist_items'),
                path('check_internet/', base.settings.check_internet, name='check_internet'),
                path('update_user_count/', base.settings.update_user_count, name='update_user_count'),

                path('check_spotify_credentials/', base.settings.check_spotify_credentials, name='check_spotify_credentials'),
                path('set_spotify_credentials/', base.settings.set_spotify_credentials, name='set_spotify_credentials'),

                path('set_bluetooth_scanning/', base.settings.set_bluetooth_scanning, name='set_bluetooth_scanning'),
                path('connect_bluetooth/', base.settings.connect_bluetooth, name='connect_bluetooth'),
                path('disconnect_bluetooth/', base.settings.disconnect_bluetooth, name='disconnect_bluetooth'),

                path('available_ssids/', base.settings.available_ssids, name='available_ssids'),
                path('connect_to_wifi/', base.settings.connect_to_wifi, name='connect_to_wifi'),
                path('enable_homewifi/', base.settings.enable_homewifi, name='enable_homewifi'),
                path('disable_homewifi/', base.settings.disable_homewifi, name='disable_homewifi'),
                path('stored_ssids/', base.settings.stored_ssids, name='stored_ssids'),
                path('set_homewifi_ssid/', base.settings.set_homewifi_ssid, name='set_homewifi_ssid'),

                path('list_subdirectories/', base.settings.list_subdirectories, name='list_subdirectories'),
                path('scan_library/', base.settings.scan_library, name='scan_library'),
                path('create_playlists/', base.settings.create_playlists, name='create_playlists'),

                path('analyse/', base.settings.analyse, name='analyse'),

                path('disable_events/', base.settings.disable_events, name='disable_events'),
                path('enable_events/', base.settings.enable_events, name='enable_events'),
                path('disable_hotspot/', base.settings.disable_hotspot, name='disable_hotspot'),
                path('enable_hotspot/', base.settings.enable_hotspot, name='enable_hotspot'),
                path('unprotect_wifi/', base.settings.unprotect_wifi, name='unprotect_wifi'),
                path('protect_wifi/', base.settings.protect_wifi, name='protect_wifi'),
                path('disable_tunneling/', base.settings.disable_tunneling, name='disable_tunneling'),
                path('enable_tunneling/', base.settings.enable_tunneling, name='enable_tunneling'),
                path('disable_remote/', base.settings.disable_remote, name='disable_remote'),
                path('enable_remote/', base.settings.enable_remote, name='enable_remote'),
                path('reboot_server/', base.settings.reboot_server, name='reboot_server'),
                path('reboot_system/', base.settings.reboot_system, name='reboot_system'),
            ])),
        ])),

        path('api/', include([
            path('musiq/', include([
                path('post_song/', base.musiq.post_song, name='post_song'),
            ])),
        ])),
    ]
