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
  let index = element.closest('.queue-entry').parent().index();
  // if the element is currently being reordered,
  // look into its index span for the index
  if (index == -1) {
    let el = element.find('.queue-index');
    if (index.length == 0) {
      el = element.closest('.queue-entry').find('.queue-index');
    }
    index = el.text() - 1;
  }
  return state.songQueue[index].id;
}

/** Checks if playlist mode is enabled.
 * @return {boolean} whether playlist mode is currently enabled.
 */
export function playlistEnabled() {
  return $('#playlist-mode').hasClass('icon-enabled');
}

/** Disable playlist mode by modifying the respective classes. */
export function disablePlaylistMode() {
  $('#playlist-mode').removeClass('icon-enabled');
  $('#playlist-mode').addClass('icon-disabled');
  $('#request-radio').removeClass('icon-enabled');
  $('#request-radio').addClass('icon-disabled');
  $('#shuffle-all').removeClass('icon-enabled');
  $('#shuffle-all').addClass('icon-disabled');
  $('#remove-all').removeClass('icon-enabled');
  $('#remove-all').addClass('icon-disabled');
}

/** Morph the pause button into the play button. */
export function showPlayButton() {
  $('#play').before($('#pause'));
  setTimeout(function() {
    $('#play-button-container').removeClass('morphed');
  }, 50);
}

/** Morph the play button into the pause button. */
export function showPauseButton() {
  $('#pause').before($('#play'));
  setTimeout(function() {
    $('#play-button-container').addClass('morphed');
  }, 50);
}

/** Request an archived music item.
 * @param {number} key the database key of the archived item
 * @param {string} query the query that lead to this entry
 * @param {string} platform the platform the music should be played from
 */
export function requestArchivedMusic(key, query,
    platform = localStorageGet('platform')) {
  $.post(urls['musiq']['request-music'],
      {
        key: key,
        query: query,
        playlist: playlistEnabled(),
        platform: platform,
      }).done(function(response) {
    successToast(response.message, '"' + query + '"');
    localStorageSet('vote-' + response.key, '+', 7);
  }).fail(function(response) {
    errorToast(response.responseText, '"' + query + '"');
  });
  infoToast('searching...', '"' + query + '"');
  $('#music-input').val('').trigger('change');
  disablePlaylistMode();
}

/** Request a new music item.
 * @param {string} query the query that is searched for
 * @param {string} platform the platform the music should be played from
 */
export function requestNewMusic(query, platform = localStorageGet('platform')) {
  $.post(urls['musiq']['request-music'],
      {
        query: query,
        playlist: playlistEnabled(),
        platform: platform,
      }).done(function(response) {
    successToast(response.message, '"' + query + '"');
    localStorageSet('vote-' + response.key, '+', 7);
  }).fail(function(response) {
    errorToast(response.responseText, '"' + query + '"');
  });
  infoToast('searching...', '"' + query + '"');
  $('#music-input').val('').trigger('change');
  disablePlaylistMode();
}

/** Shows a modal with additional information for a song.
 * @param {HTMLElement} element the element that info should be shown about
 * @param {string} duration the duration of the song
 * @param {string} url the external url that will be linked in the modal
 */
function showTitleModal(element, duration, url) {
  const contents = element.contents();
  const modalText = $('#title-modal .modal-text');
  modalText.empty();
  if (contents.length > 1) {
    modalText.append($('<strong/>').text(contents.get(0).innerText));
    // cut the character that connects artist and title
    modalText.append($('<span/>').text(contents.get(1).data.substring(3)));
  } else {
    modalText.append($('<span/>').text(contents.get(0).data));
  }
  modalText.append($('<span/>').text(duration));
  $('#external-link').attr('href', url);
  $('#title-modal').modal('show');
}

/** Adds handlers for all buttons. */
export function onReady() {
  $('#playlist-mode').on('click tap', function(e) {
    if ($(this).hasClass('icon-disabled')) {
      $(this).removeClass('icon-disabled');
      $(this).addClass('icon-enabled');
      $('#request-radio').removeClass('icon-disabled');
      $('#request-radio').addClass('icon-enabled');
      $('#shuffle-all').removeClass('icon-disabled');
      $('#shuffle-all').addClass('icon-enabled');
      $('#remove-all').removeClass('icon-disabled');
      $('#remove-all').addClass('icon-enabled');
      warningToast('Use this power wisely');
    } else {
      disablePlaylistMode();
    }
  });
  // the key of the song that was suggested via random suggest
  let randomKey = null;
  $('#random-suggestion').on('click tap', function() {
    $.get(urls['musiq']['random-suggestion'], {
      playlist: playlistEnabled(),
    }).done(
        function(response) {
          $('#music-input').val(response.suggestion)
              .trigger('change');
          randomKey = response.key;
          // morph search icon into go icon to indicate the absence of search
          $('#request-archived-music').before($('#request-new-music'));
          // wait until the change was applied, then initiate the animation
          setTimeout(function() {
            $('#request-button-container').addClass('morphed');
          }, 50);
        }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  /** Morph the go icon into the search icon. */
  function showSearchIcon() {
    // change back to the search icon when the user focuses the input field
    $('#request-new-music').before($('#request-archived-music'));
    // wait until the change was applied, then initiate the animation
    setTimeout(function() {
      $('#request-button-container').removeClass('morphed');
    }, 50);
  }

  $('#request-new-music').on('click tap', function() {
    requestNewMusic($('#music-input').val());
  });
  $('#request-archived-music').on('click tap', function() {
    requestArchivedMusic(randomKey, $('#music-input').val());
    showSearchIcon();
  });
  $('#music-input').focus(function() {
    showSearchIcon();
    const el = $(this) as JQuery<HTMLInputElement>;
    const contentLength = (el.val() as string).length;
    el[0].setSelectionRange(contentLength, contentLength);
  });
  $('#clearbutton').on('click tap', function() {
    // prevent scroll on focus, otherwise the page
    // "overscrolls" to the right afterwards.
    $(this).prev('input')
        .val('')
        .trigger('change')[0]
        .focus({preventScroll: true});
  });
  $('#music-input').on('change input copy paste cut', function() {
    const icon = $(this).next('i');
    if (!(this as HTMLInputElement).value) {
      icon.css('opacity', '0');
    } else {
      icon.css('opacity', '1');
    }
  });
  $('#music-input').on('keydown', function(e) {
    if (e.which === 13) {
      if (randomKey == null) {
        requestNewMusic($('#music-input').val());
      } else {
        requestArchivedMusic(randomKey, $('#music-input').val());
      }
    } else {
      // another key was pressed -> the input changed,
      // clear the stored key from random suggestion
      randomKey = null;
    }
  });

  // info popup for the current song
  $('#current-song-title').on('click tap', function() {
    if (state.currentSong == null) {
      return;
    }
    const url = state.currentSong.externalUrl;
    const duration = state.currentSong.durationFormatted;
    showTitleModal($('#current-song-title'), duration, url);
  });

  $('#volume-slider').change(function() {
    $.post(urls['musiq']['set-volume'], {
      value: $(this).val(),
    });
  });
  $('#shuffle-all').on('click tap', function() {
    if (!playlistEnabled()) {
      warningToast('Please enable playlists to use this');
      return;
    }
    $.post(urls['musiq']['shuffle-all']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    disablePlaylistMode();
  });
  $('#remove-all').on('click tap', function() {
    if (!playlistEnabled()) {
      warningToast('Please enable playlists to use this');
      return;
    }
    $.post(urls['musiq']['remove-all']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    disablePlaylistMode();
  });

  // info popups for songs with long text
  $('#song-queue').on('click tap', '.queue-title', function() {
    const index = $(this).closest('.queue-entry').parent().index();
    const url = state.songQueue[index].externalUrl;
    const duration = state.songQueue[index].durationFormatted;
    showTitleModal($(this), duration, url);
  });
  // close modals on click
  $('#title-modal .modal-content').on('click tap', function() {
    $('#title-modal').modal('hide');
  });
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  onReady();
});
