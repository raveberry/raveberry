import {state} from './update';
import {
  localStorageGet, localStorageSet,
  infoToast, successToast, warningToast, errorToast,
} from '../base';

/** Finds the song key to a given HTML element.
 * @param {HTMLElement} element an element that is part of a queue entry
 * @return {number} id of the song represented in the entry
 */
export function keyOfElement(element) {
  // takes a jquery element and returns the index of it in the song queue
  let index = element.closest('.queue_entry').parent().index();
  // if the element is currently being reordered,
  // look into its index span for the index
  if (index == -1) {
    let el = element.find('.queue_index');
    if (index.length == 0) {
      el = element.closest('.queue_entry').find('.queue_index');
    }
    index = el.text() - 1;
  }
  return state.song_queue[index].id;
}

/** Checks if playlist mode is enabled.
 * @return {boolean} whether playlist mode is currently enabled.
 */
export function playlistEnabled() {
  return $('#playlist_mode').hasClass('icon_enabled');
}

/** Disable playlist mode by modifying the respective classes. */
export function disablePlaylistMode() {
  $('#playlist_mode').removeClass('icon_enabled');
  $('#playlist_mode').addClass('icon_disabled');
  $('#request_radio').removeClass('icon_enabled');
  $('#request_radio').addClass('icon_disabled');
  $('#shuffle_all').removeClass('icon_enabled');
  $('#shuffle_all').addClass('icon_disabled');
  $('#remove_all').removeClass('icon_enabled');
  $('#remove_all').addClass('icon_disabled');
}

/** Morph the pause button into the play button. */
export function showPlayButton() {
  $('#play').before($('#pause'));
  setTimeout(function() {
    $('#play_button_container').removeClass('morphed');
  }, 50);
}

/** Morph the play button into the pause button. */
export function showPauseButton() {
  $('#pause').before($('#play'));
  setTimeout(function() {
    $('#play_button_container').addClass('morphed');
  }, 50);
}

/** Request an archived music item.
 * @param {number} key the database key of the archived item
 * @param {string} query the query that lead to this entry
 * @param {string} platform the platform the music should be played from
 */
export function requestArchivedMusic(key, query,
    platform = localStorageGet('platform')) {
  $.post(urls['request_music'],
      {
        key: key,
        query: query,
        playlist: playlistEnabled(),
        platform: platform,
      }).done(function(response) {
    successToast(response.message, '"' + query + '"');
    localStorageSet('vote_' + response.key, '+', 7);
  }).fail(function(response) {
    errorToast(response.responseText, '"' + query + '"');
  });
  infoToast('searching...', '"' + query + '"');
  $('#music_input').val('').trigger('change');
  disablePlaylistMode();
}

/** Request a new music item.
 * @param {string} query the query that is searched for
 * @param {string} platform the platform the music should be played from
 */
export function requestNewMusic(query, platform = localStorageGet('platform')) {
  $.post(urls['request_music'],
      {
        query: query,
        playlist: playlistEnabled(),
        platform: platform,
      }).done(function(response) {
    successToast(response.message, '"' + query + '"');
    localStorageSet('vote_' + response.key, '+', 7);
  }).fail(function(response) {
    errorToast(response.responseText, '"' + query + '"');
  });
  infoToast('searching...', '"' + query + '"');
  $('#music_input').val('').trigger('change');
  disablePlaylistMode();
}

/** Shows a modal with additional information for a song.
 * @param {HTMLElement} element the element that info should be shown about
 * @param {string} url the external url that will be linked in the modal
 */
function showTitleModal(element, url) {
  const newModalText = element.contents().clone();
  if (newModalText.length > 1) {
    // cut the character that connects artist and title
    newModalText.get(1).data = newModalText.get(1).data.substring(3);
  }
  newModalText.append('<br/>');
  $('#title_modal .modal-text').html(newModalText);
  $('#external_link').attr('href', url);
  $('#title_modal').modal('show');
}

/** Adds handlers for all buttons. */
export function onReady() {
  $('#playlist_mode').on('click tap', function(e) {
    if ($(this).hasClass('icon_disabled')) {
      $(this).removeClass('icon_disabled');
      $(this).addClass('icon_enabled');
      $('#request_radio').removeClass('icon_disabled');
      $('#request_radio').addClass('icon_enabled');
      $('#shuffle_all').removeClass('icon_disabled');
      $('#shuffle_all').addClass('icon_enabled');
      $('#remove_all').removeClass('icon_disabled');
      $('#remove_all').addClass('icon_enabled');
      warningToast('Use this power wisely');
    } else {
      disablePlaylistMode();
    }
  });
  // the key of the song that was suggested via random suggest
  let randomKey = null;
  $('#random_suggestion').on('click tap', function() {
    $.get(urls['random_suggestion'], {playlist: playlistEnabled()}).done(
        function(response) {
          $('#music_input').val(response.suggestion)
              .trigger('change');
          randomKey = response.key;
          // morph search icon into go icon to indicate the absence of search
          $('#request_archived_music').before($('#request_new_music'));
          // wait until the change was applied, then initiate the animation
          setTimeout(function() {
            $('#request_button_container').addClass('morphed');
          }, 50);
        }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  /** Morph the go icon into the search icon. */
  function showSearchIcon() {
    // change back to the search icon when the user focuses the input field
    $('#request_new_music').before($('#request_archived_music'));
    // wait until the change was applied, then initiate the animation
    setTimeout(function() {
      $('#request_button_container').removeClass('morphed');
    }, 50);
  }

  $('#request_new_music').on('click tap', function() {
    requestNewMusic($('#music_input').val());
  });
  $('#request_archived_music').on('click tap', function() {
    requestArchivedMusic(randomKey, $('#music_input').val());
    showSearchIcon();
  });
  $('#music_input').focus(function() {
    showSearchIcon();
    const el = $(this) as JQuery<HTMLInputElement>;
    const contentLength = (el.val() as string).length;
    el[0].setSelectionRange(contentLength, contentLength);
  });
  $('#clearbutton').on('click tap', function() {
    $(this).prev('input').val('').trigger('change').focus();
  });
  $('#music_input').on('change input copy paste cut', function() {
    const icon = $(this).next('i');
    if (!(this as HTMLInputElement).value) {
      icon.css('opacity', '0');
    } else {
      icon.css('opacity', '1');
    }
  });
  $('#music_input').on('keydown', function(e) {
    if (e.which === 13) {
      if (randomKey == null) {
        requestNewMusic($('#music_input').val());
      } else {
        requestArchivedMusic(randomKey, $('#music_input').val());
      }
    } else {
      // another key was pressed -> the input changed,
      // clear the stored key from random suggestion
      randomKey = null;
    }
  });

  // info popup for the current song
  $('#current_song').on('click tap', function() {
    if (state.current_song == null) {
      return;
    }
    const url = state.current_song.external_url;
    showTitleModal($('#current_song_title'), url);
  });

  $('#volume_slider').change(function() {
    $.post(urls['set_volume'], {
      value: $(this).val(),
    });
  });
  $('#shuffle_all').on('click tap', function() {
    if (!playlistEnabled()) {
      warningToast('Please enable playlists to use this');
      return;
    }
    $.post(urls['shuffle_all']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    disablePlaylistMode();
  });
  $('#remove_all').on('click tap', function() {
    if (!playlistEnabled()) {
      warningToast('Please enable playlists to use this');
      return;
    }
    $.post(urls['remove_all']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    disablePlaylistMode();
  });

  // info popups for songs with long text
  $('#song_queue').on('click tap', '.queue_title', function() {
    const index = $(this).closest('.queue_entry').parent().index();
    const url = state.song_queue[index].external_url;
    showTitleModal($(this), url);
  });
  // close modals on click
  $('#title_modal .modal-content').on('click tap', function() {
    $('#title_modal').modal('hide');
  });
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  onReady();
});
