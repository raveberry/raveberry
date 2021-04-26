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
  $('#restart-song').on('click tap', function(e) {
    $.post(urls['musiq']['restart']);
  });
  $('#seek-backward').on('click tap', function(e) {
    $.post(urls['musiq']['seek-backward']);
  });
  $('#play').on('click tap', function(e) {
    // don't allow play command without a song
    if (state == null || state.currentSong == null) return;
    showPauseButton();
    $.post(urls['musiq']['play']);
  });
  $('#pause').on('click tap', function(e) {
    showPlayButton();
    $.post(urls['musiq']['pause']);
  });
  $('#seek-forward').on('click tap', function(e) {
    $.post(urls['musiq']['seek-forward']);
  });
  $('#skip-song').on('click tap', function(e) {
    $.post(urls['musiq']['skip']);
  });
  $('#set-shuffle').on('click tap', function(e) {
    // send True if it is currently disabled to enable it and vice versa
    $.post(urls['musiq']['set-shuffle'],
        {
          value: $(this).hasClass('icon-disabled'),
        });
  });
  $('#set-repeat').on('click tap', function(e) {
    $.post(urls['musiq']['set-repeat'],
        {
          value: $(this).hasClass('icon-disabled'),
        });
  });
  $('#set-autoplay').on('click tap', function(e) {
    $.post(urls['musiq']['set-autoplay'],
        {
          value: $(this).hasClass('icon-disabled'),
        });
  });
  $('#request-radio').on('click tap', function(e) {
    if (!playlistEnabled()) {
      warningToast('Please enable playlists to use this');
      return;
    }
    $.post(urls['musiq']['request-radio']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    infoToast('Getting radio info', 'This could take some time');
    disablePlaylistMode();
  });
  $('#song-queue').on('click tap', '.prioritize', function() {
    $.post(urls['musiq']['prioritize'], {
      key: keyOfElement($(this)),
    });
  });
  $('#song-queue').on('click tap', '.remove', function() {
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
