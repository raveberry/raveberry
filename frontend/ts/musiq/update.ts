import {localStorageGet, registerSpecificState} from '../base';
import {showPlayButton, showPauseButton} from './buttons';
import {syncAudioStream} from './audio';

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
  const currentSong = newState.musiq.currentSong;
  if (currentSong == null) {
    state = newState.musiq;
    $('#current-song-title').empty();
    $('#current-song-title').append($('<em/>').text('Currently Empty'));
    $('#current-song-title').trigger('change');
    $('#current-song').removeClass('present');
    $('#current-song').addClass('empty');

    $('#song-votes .vote-down').removeClass('pressed');
    $('#song-votes .vote-up').removeClass('pressed');
    $('#current-song-votes').text(0);

    $('#progress-bar').css('transition', 'none');
    $('#progress-bar').css('width', '0%');
    // Trigger a reflow, flushing the CSS changes
    $('#progress-bar')[0].offsetHeight;

    showPlayButton();
  } else {
    state = newState.musiq;

    if (oldState == null ||
      oldState.currentSong == null ||
      oldState.currentSong.id != state.currentSong.id) {
      // only update the current song title if it changed,
      // so the marquee effect does not reset
      insertDisplayName($('#current-song-title'), currentSong);
      $('#current-song-title').trigger('change');
    }

    const previousVote = localStorageGet('vote-' + currentSong.queueKey);
    if (previousVote == '+') {
      $('#song-votes .vote-up').addClass('pressed');
      $('#song-votes .vote-down').removeClass('pressed');
    } else if (previousVote == '-') {
      $('#song-votes .vote-down').addClass('pressed');
      $('#song-votes .vote-up').removeClass('pressed');
    } else {
      $('#song-votes .vote-down').removeClass('pressed');
      $('#song-votes .vote-up').removeClass('pressed');
    }

    $('#current-song-votes').text(currentSong.votes);

    $('#progress-bar').css('transition', 'none');
    $('#progress-bar').css('width', state.progress + '%');
    // Trigger a reflow, flushing the CSS changes
    $('#progress-bar')[0].offsetHeight;

    if (state.paused) {
      showPlayButton();
    } else {
      showPauseButton();

      const duration = state.currentSong.duration;

      const played = state.progress / 100 * duration;
      const left = duration - played;

      $('#progress-bar').css({
        'transition': 'width ' + left + 's linear',
        'width': '100%',
      });
    }
  }

  if (state.shuffle) {
    $('#set-shuffle').removeClass('icon-disabled');
    $('#set-shuffle').addClass('icon-enabled');
  } else {
    $('#set-shuffle').removeClass('icon-enabled');
    $('#set-shuffle').addClass('icon-disabled');
  }
  if (state.repeat) {
    $('#set-repeat').removeClass('icon-disabled');
    $('#set-repeat').addClass('icon-enabled');
  } else {
    $('#set-repeat').removeClass('icon-enabled');
    $('#set-repeat').addClass('icon-disabled');
  }
  if (state.autoplay) {
    $('#set-autoplay').removeClass('icon-disabled');
    $('#set-autoplay').addClass('icon-enabled');
  } else {
    $('#set-autoplay').removeClass('icon-enabled');
    $('#set-autoplay').addClass('icon-disabled');
  }

  $('#volume-slider').val(state.volume);
  if (state.volume == 0) {
    $('#volume-indicator').addClass('fa-volume-off');
    $('#volume-indicator').removeClass('fa-volume-down');
    $('#volume-indicator').removeClass('fa-volume-up');
  } else if (state.volume <= 0.5) {
    $('#volume-indicator').removeClass('fa-volume-off');
    $('#volume-indicator').addClass('fa-volume-down');
    $('#volume-indicator').removeClass('fa-volume-up');
  } else {
    $('#volume-indicator').removeClass('fa-volume-off');
    $('#volume-indicator').removeClass('fa-volume-down');
    $('#volume-indicator').addClass('fa-volume-up');
  }

  $('#total-time').text(state.totalTimeFormatted);

  /*
  <li class="list-group-item">
    <div class="queue-entry">
      <div class="download-icon queue-handle">
        <div class="download-overlay"></div>
        <svg>
          <!-- downloadSvg -->
        </svg>
      </div>
      <div class="queue-index queue-handle"><fa-sort>{{ forloop.counter }}</div>
      <div class="queue-title">{{ song.artist }} - {{ song.title }}</div>
      <div class="queue-info">
        <span class="queue-info-time">{{ song.duration-formatted }}</span>
        <span class="queue-info-controls">
          {% if voting-system %}
          <i class="fas fa-chevron-circle-up vote-up"></i>
          <i class="fas fa-chevron-circle-down vote-down"></i>
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

  syncAudioStream();
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

/** Create an empty queue entry.
 * @return {Object} the created queue item
 */
function createQueueItem() {
  const li = $('<li/>')
      .addClass('list-group-item');
  const entryDiv = $('<div/>')
      .addClass('queue-entry')
      .appendTo(li);
  const downloadIcon = $('<div/>')
      .addClass('download-icon')
      .addClass('queue-handle')
      .appendTo(entryDiv);
  $('<div/>')
      .addClass('download-overlay')
      .appendTo(downloadIcon);
  $(downloadSvg).appendTo(downloadIcon);

  $('<div/>')
      .addClass('queue-index')
      .addClass('queue-handle')
      .appendTo(entryDiv)
      .hide();
  $('<div/>')
      .addClass('queue-title')
      .appendTo(entryDiv);
  const info = $('<div/>')
      .addClass('queue-info')
      .appendTo(entryDiv);
  $('<span/>')
      .addClass('queue-info-time')
      .appendTo(info);
  const controls = $('<span/>')
      .addClass('queue-info-controls')
      .appendTo(info);
  if (VOTING_SYSTEM) {
    $('<i/>')
        .addClass('fas')
        .addClass('fa-chevron-circle-up')
        .addClass('vote-up')
        .appendTo(controls);
    $('<i/>')
        .addClass('fas')
        .addClass('fa-chevron-circle-down')
        .addClass('vote-down')
        .appendTo(controls);
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

/** Update a given queue entry with the information from a given song.
 * @param {Object} entry the list item to be updated
 * @param {Object} song the song containing all information
 */
function updateInformation(entry, song) {
  const index = entry.find('.queue-index');
  if (VOTING_SYSTEM) {
    index.text(song.votes);
  } else {
    index.text(song.index);
  }
  const downloadIcon = entry.find('.download-icon');
  if (song.internalUrl) {
    downloadIcon.hide();
    index.show();
  } else {
    downloadIcon.show();
    index.hide();
  }

  const title = entry.find('.queue-title');
  insertDisplayName(title, song);

  const time = entry.find('.queue-info-time');
  time.text(song.durationFormatted);

  const previousVote = localStorageGet('vote-' + song.id);
  if (previousVote == '+') {
    const up = entry.find('.vote-up');
    up.addClass('pressed');
  }
  if (previousVote == '-') {
    const down = entry.find('.vote-down');
    down.addClass('pressed');
  }
}

/** Apply the given state without any animation from scratch.
 * @param {Object} newState the new state object
 */
function rebuildSongQueue(newState) {
  animationInProgress = false;
  $('#song-queue').empty();
  $.each(newState.songQueue, function(index, song) {
    const queueEntry = createQueueItem();
    updateInformation(queueEntry, song);
    queueEntry.appendTo($('#song-queue'));
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
    $.each(oldState.songQueue, function(oldIndex, song) {
      const newIndex = newState.songQueue.findIndex((other) => {
        return other.id == song.id;
      });
      newIndices.push(newIndex);
    });

    // add new songs
    $.each(newState.songQueue, function(newIndex, song) {
      if (!newIndices.includes(newIndex)) {
        // song was not present in old indices -> append new song to the end
        const queueEntry = createQueueItem();
        queueEntry.css('opacity', '0');

        queueEntry.appendTo($('#song-queue'));

        // store its target index in our array
        newIndices.push(newIndex);
      }
    });

    // initiate transition to their new positions
    let animationNeeded = false;
    const transitionDuration = 0.5;
    $('#song-queue>li').css('top', '0px');
    $('#song-queue>li').css('transition',
        'top ' + transitionDuration + 's ease, ' +
        'opacity ' + transitionDuration + 's ease');

    let liHeight = $('#song-queue>li').first().outerHeight();
    liHeight -= parseFloat($('#song-queue>li').first()
        .css('border-bottom-width'));

    $('#song-queue>li').each(function(index, li) {
      if (newIndices[index] == -1) {
        // item was deleted
        animationNeeded = true;
        $(li).css('opacity', '0');
      } else if (index >= oldState.songQueue.length) {
        // item was added just now
        // make new songs visible
        animationNeeded = true;
        $(li).css('opacity', '1');
        const delta = (newIndices[index] - index) * liHeight;
        $(li).css('top', delta + 'px');
      } else {
        // update information of existing songs directly
        // instead of after the animation.
        // -> faster updates and updates for cases where no animation is started
        // (e.g. placeholder updates)
        const song = newState.songQueue[newIndices[index]]
        updateInformation($(li), song);

        // skip items that don't move at all
        if (newIndices[index] == index) {
          return;
        }
        // item was moved
        animationNeeded = true;
        const delta = (newIndices[index] - index) * liHeight;
        $(li).css('top', delta + 'px');
      }
    });

    if (animationNeeded) {
      animationInProgress = true;
      // update queue after animations
      setTimeout(function() {
        $('#song-queue>li').css('transition', 'none');
        // update the queue to the now current state
        rebuildSongQueue(state);
      }, transitionDuration * 1000);
    } else {
      $('#song-queue>li').css('transition', 'none');
    }
  }
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  registerSpecificState(updateState);
});
