import {localStorageGet, registerSpecificState} from '../base';
import {showPlayButton, showPauseButton} from './buttons';

export let state = null;
let animationInProgress = false;

const downloadSvg = `
<svg version="1.1" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
 <g>
  <path d="m41.5 8v40h-16.5l25 25 25-25h-16.5v-40z"/>
  <rect x="17.5" y="86.5" width="65" height="8.5"/>
 </g>
</svg>`;


/** Clear any stored state. */
export function clearState() {
  state = null;
}

/** Update the musiq state.
 * @param {Object} newState an object containing all state information */
export function updateState(newState) {
  if (!('musiq' in newState)) {
    // this state is not meant for a musiq update
    return;
  }
  // create deep copy
  let oldState = null;
  if (state != null) {
    oldState = jQuery.extend(true, {}, state);
  }
  const currentSong = newState.musiq.current_song;
  if (currentSong == null) {
    state = newState.musiq;
    $('#current_song_title').empty();
    $('#current_song_title').append($('<em/>').text('Currently Empty'));
    $('#current_song_title').trigger('change');
    $('#current_song').removeClass('present');
    $('#current_song').addClass('empty');

    $('#song_votes .vote_down').removeClass('pressed');
    $('#song_votes .vote_up').removeClass('pressed');
    $('#current_song_votes').text(0);

    $('#progress_bar').css('transition', 'none');
    $('#progress_bar').css('width', '0%');
    // Trigger a reflow, flushing the CSS changes
    $('#progress_bar')[0].offsetHeight;

    showPlayButton();
  } else {
    state = newState.musiq;

    if (oldState == null ||
      oldState.current_song == null ||
      oldState.current_song.id != state.current_song.id) {
      insertDisplayName($('#current_song_title'), currentSong);
      $('#current_song_title').trigger('change');
    }

    const previousVote = localStorageGet('vote_' + currentSong.queue_key);
    if (previousVote == '+') {
      $('#song_votes .vote_up').addClass('pressed');
      $('#song_votes .vote_down').removeClass('pressed');
    } else if (previousVote == '-') {
      $('#song_votes .vote_down').addClass('pressed');
      $('#song_votes .vote_up').removeClass('pressed');
    } else {
      $('#song_votes .vote_down').removeClass('pressed');
      $('#song_votes .vote_up').removeClass('pressed');
    }

    $('#current_song_votes').text(currentSong.votes);

    $('#progress_bar').css('transition', 'none');
    $('#progress_bar').css('width', state.progress + '%');
    // Trigger a reflow, flushing the CSS changes
    $('#progress_bar')[0].offsetHeight;

    if (state.paused) {
      showPlayButton();
    } else {
      showPauseButton();

      const duration = state.current_song.duration;

      const played = state.progress / 100 * duration;
      const left = duration - played;

      $('#progress_bar').css({
        'transition': 'width ' + left + 's linear',
        'width': '100%',
      });
    }
  }

  if (state.shuffle) {
    $('#set_shuffle').removeClass('icon_disabled');
    $('#set_shuffle').addClass('icon_enabled');
  } else {
    $('#set_shuffle').removeClass('icon_enabled');
    $('#set_shuffle').addClass('icon_disabled');
  }
  if (state.repeat) {
    $('#set_repeat').removeClass('icon_disabled');
    $('#set_repeat').addClass('icon_enabled');
  } else {
    $('#set_repeat').removeClass('icon_enabled');
    $('#set_repeat').addClass('icon_disabled');
  }
  if (state.autoplay) {
    $('#set_autoplay').removeClass('icon_disabled');
    $('#set_autoplay').addClass('icon_enabled');
  } else {
    $('#set_autoplay').removeClass('icon_enabled');
    $('#set_autoplay').addClass('icon_disabled');
  }

  $('#volume_slider').val(state.volume);
  if (state.volume == 0) {
    $('#volume_indicator').addClass('fa-volume-off');
    $('#volume_indicator').removeClass('fa-volume-down');
    $('#volume_indicator').removeClass('fa-volume-up');
  } else if (state.volume <= 0.5) {
    $('#volume_indicator').removeClass('fa-volume-off');
    $('#volume_indicator').addClass('fa-volume-down');
    $('#volume_indicator').removeClass('fa-volume-up');
  } else {
    $('#volume_indicator').removeClass('fa-volume-off');
    $('#volume_indicator').removeClass('fa-volume-down');
    $('#volume_indicator').addClass('fa-volume-up');
  }

  $('#total_time').text(state.total_time_formatted);

  /*
  <li class="list-group-item">
    <div class="queue_entry">
      <div class="download_icon queue_handle">
        <div class="download_overlay"></div>
        <svg>
          <!-- downloadSvg -->
        </svg>
      </div>
      <div class="queue_index queue_handle"><fa-sort>{{ forloop.counter }}</div>
      <div class="queue_title">{{ song.artist }} - {{ song.title }}</div>
      <div class="queue_info">
        <span class="queue_info_time">{{ song.duration_formatted }}</span>
        <span class="queue_info_controls">
          {% if voting_system %}
          <i class="fas fa-chevron-circle-up vote_up"></i>
          <i class="fas fa-chevron-circle-down vote_down"></i>
          {% else %}
          <i class="fas level-up-alt prioritize"></i>
          <i class="fas fa-trash-alt remove"></i>
          {% endif %}
        </span>
      </div>
    </div>
  </li>
  */

  // don't start a new animation when an old one is still in progress
  // the running animation will end in the (then) current state
  applyQueueChange(oldState, state);
}

/** Inserts the displayname of a song into an element.
 * @param {HTMLElement} element the div the displayname should be inserted into
 * @param {Object} song the song the info is taken from
 */
function insertDisplayName(element, song) {
  if (song.artist == null || song.artist == '') {
    element.text(song.title);
  } else {
    element.text(' – ' + song.title);
    element.prepend($('<strong/>').text(song.artist));
  }
}

/** Create a queue entry from the given song.
 * @param {Object} song the song containing all information
 * @return {Object} the created queue item
 */
function createQueueItem(song) {
  const li = $('<li/>')
      .addClass('list-group-item');
  const entryDiv = $('<div/>')
      .addClass('queue_entry')
      .appendTo(li);
  const downloadIcon = $('<div/>')
      .addClass('download_icon')
      .addClass('queue_handle')
      .appendTo(entryDiv);
  $('<div/>')
      .addClass('download_overlay')
      .appendTo(downloadIcon);

  $(downloadSvg).appendTo(downloadIcon);

  const index = $('<div/>')
      .addClass('queue_index')
      .addClass('queue_handle');
  if (VOTING_SYSTEM) {
    index.text(song.votes);
  } else {
    index.text(song.index);
  }
  index.appendTo(entryDiv);
  if (song.internal_url) {
    downloadIcon.hide();
  } else {
    index.hide();
  }
  const title = $('<div/>');
  insertDisplayName(title, song);
  title.addClass('queue_title')
      .appendTo(entryDiv);
  const info = $('<div/>')
      .addClass('queue_info')
      .appendTo(entryDiv);
  $('<span/>')
      .addClass('queue_info_time')
      .text(song.duration_formatted)
      .appendTo(info);
  const controls = $('<span/>')
      .addClass('queue_info_controls')
      .appendTo(info);
  if (VOTING_SYSTEM) {
    const previousVote = localStorageGet('vote_' + song.id);
    const up = $('<i/>')
        .addClass('fas')
        .addClass('fa-chevron-circle-up')
        .addClass('vote_up');
    if (previousVote == '+') {
      up.addClass('pressed');
    }
    up.appendTo(controls);
    const down = $('<i/>')
        .addClass('fas')
        .addClass('fa-chevron-circle-down')
        .addClass('vote_down');
    if (previousVote == '-') {
      down.addClass('pressed');
    }
    down.appendTo(controls);
  }
  if (!VOTING_SYSTEM || CONTROLS_ENABLED) {
    $('<i/>')
        .addClass('fas')
        .addClass('fa-level-up-alt')
        .addClass('prioritize')
        .appendTo(controls);
    $('<i/>')
        .addClass('fas')
        .addClass('fa-trash-alt')
        .addClass('remove')
        .appendTo(controls);
  }
  return li;
}

/** Apply the given state without any animation from scratch.
 * @param {Object} newState the new state object
 */
function rebuildSongQueue(newState) {
  animationInProgress = false;
  $('#song_queue').empty();
  $.each(newState.song_queue, function(index, song) {
    const queueEntry = createQueueItem(song);
    queueEntry.appendTo($('#song_queue'));
  });
}

/** Find the differences between the old and the new state, initiate animations.
 * @param {Object} oldState the current state from which the animations start
 * @param {Object} newState the new state to which it should be animated
 */
function applyQueueChange(oldState, newState) {
  if (animationInProgress) return;

  if (oldState == null) {
    rebuildSongQueue(newState);
  } else {
    // find mapping from old to new indices
    const newIndices = [];
    $.each(oldState.song_queue, function(oldIndex, song) {
      const newIndex = newState.song_queue.findIndex((other) => {
        return other.id == song.id;
      });
      newIndices.push(newIndex);
    });

    // add new songs
    $.each(newState.song_queue, function(newIndex, song) {
      if (!newIndices.includes(newIndex)) {
        // song was not present in old indices -> new song
        const queueEntry = createQueueItem(song);
        queueEntry.css('opacity', '0');

        queueEntry.appendTo($('#song_queue'));
      }
    });

    // initiate transition to their new positions
    let animationNeeded = false;
    const transitionDuration = 0.5;
    $('#song_queue>li').css('top', '0px');
    $('#song_queue>li').css('transition',
        'top ' + transitionDuration + 's ease, ' +
        'opacity ' + transitionDuration + 's ease');

    let liHeight = $('#song_queue>li').first().outerHeight();
    liHeight -= parseFloat($('#song_queue>li').first()
        .css('border-bottom-width'));

    $('#song_queue>li').each(function(index, li) {
      if (newIndices[index] == -1) {
        // item was deleted
        animationNeeded = true;
        $(li).css('opacity', '0');
      } else {
        // skip items that don't move at all
        if (newIndices[index] == index) {
          return;
        }
        // item was moved
        animationNeeded = true;
        const delta = (newIndices[index] - index) * liHeight;
        $(li).css('top', delta + 'px');

        // make new songs visible
        $(li).css('opacity', '1');
      }
    });

    if (animationNeeded) {
      animationInProgress = true;
      // update queue after animations
      setTimeout(function() {
        $('#song_queue>li').css('transition', 'none');
        // update the queue to the now current state
        rebuildSongQueue(state);
      }, transitionDuration * 1000);
    } else {
      $('#song_queue>li').css('transition', 'none');
    }
  }
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  registerSpecificState(updateState);
});
