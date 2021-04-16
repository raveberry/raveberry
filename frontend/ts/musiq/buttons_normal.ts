import {state} from './update';
import {
  keyOfElement,
  showPlayButton,
  showPauseButton,
  playlistEnabled,
  disablePlaylistMode,
} from './buttons';
import {infoToast, successToast, warningToast, errorToast} from '../base';

/** Adds handlers to buttons that are visible when voting is disabled. */
export function onReady() {
  $('#restart_song').on('click tap', function(e) {
    $.post(urls['musiq']['restart']);
  });
  $('#seek_backward').on('click tap', function(e) {
    $.post(urls['musiq']['seek_backward']);
  });
  $('#play').on('click tap', function(e) {
    // don't allow play command without a song
    if (state == null || state.current_song == null) return;
    showPauseButton();
    $.post(urls['musiq']['play']);
  });
  $('#pause').on('click tap', function(e) {
    showPlayButton();
    $.post(urls['musiq']['pause']);
  });
  $('#seek_forward').on('click tap', function(e) {
    $.post(urls['musiq']['seek_forward']);
  });
  $('#skip_song').on('click tap', function(e) {
    $.post(urls['musiq']['skip']);
  });
  $('#set_shuffle').on('click tap', function(e) {
    // send True if it is currently disabled to enable it and vice versa
    $.post(urls['musiq']['set_shuffle'],
        {
          value: $(this).hasClass('icon_disabled'),
        });
  });
  $('#set_repeat').on('click tap', function(e) {
    $.post(urls['musiq']['set_repeat'],
        {
          value: $(this).hasClass('icon_disabled'),
        });
  });
  $('#set_autoplay').on('click tap', function(e) {
    $.post(urls['musiq']['set_autoplay'],
        {
          value: $(this).hasClass('icon_disabled'),
        });
  });
  $('#request_radio').on('click tap', function(e) {
    if (!playlistEnabled()) {
      warningToast('Please enable playlists to use this');
      return;
    }
    $.post(urls['musiq']['request_radio']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    infoToast('Getting radio info', 'This could take some time');
    disablePlaylistMode();
  });
  $('#song_queue').on('click tap', '.prioritize', function() {
    $.post(urls['musiq']['prioritize'], {
      key: keyOfElement($(this)),
    });
  });
  $('#song_queue').on('click tap', '.remove', function() {
    $.post(urls['musiq']['remove'], {
      key: keyOfElement($(this)),
    });
  });
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  onReady();
});
