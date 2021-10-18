import {keyOfElement} from './buttons';
import {state} from './update';
import {localStorageSet, warningToastWithBar, errorToast} from '../base';

/** Adds handlers to buttons that are visible when voting is enabled. */
export function onReady() {
  // Use a token bucket implementation to allow 10 Votes per minute.
  const maxTokens = 10;
  let currentTokens = maxTokens;
  const bucketLifetime = 30000; // half a minute
  let currentBucket = $.now();

  /** Makes sure that voting does not occur too often.
   * @return {boolean} whether voting is allowed. */
  function canVote() {
    const now = $.now();
    const timePassed = now - currentBucket;
    if (timePassed > bucketLifetime) {
      currentBucket = now;
      currentTokens = maxTokens - 1;
      return true;
    }

    if (currentTokens > 0) {
      currentTokens--;
      return true;
    }

    const ratio = (bucketLifetime - timePassed) / bucketLifetime;
    warningToastWithBar('You\'re doing that too often');
    $('#vote-timeout-bar').css('transition', 'none');
    $('#vote-timeout-bar').css('width', ratio * 100 + '%');
    $('#vote-timeout-bar')[0].offsetHeight;
    $('#vote-timeout-bar').css({
      'transition': 'width ' + ratio * bucketLifetime / 1000 + 's linear',
      'width': '0%',
    });
    return false;
  }

  /** Vote for a song.
   * @param {HTMLElement} button the button that was pressed to vote
   * @param {number} key the key of the voted song
   * @param {number} amount the amount of votes, from -2 to +2. */
  function vote(button, key, amount) {
    let votes = button.closest('.queue-entry').find('.queue-index');
    if (votes.length == 0) {
      votes = button.siblings('#current-song-votes');
    }
    votes.text(parseInt(votes.text()) + amount);
    $.post(urls['musiq']['vote'], {
      key: key,
      amount: amount,
    }).fail(function(response) {
      errorToast(response.responseText);
      votes.text(parseInt(votes.text()) - amount);
    });
  }

  $('#content').on('click tap', '.vote-up', function() {
    if (!canVote()) {
      return;
    }
    let key = -1;
    if ($(this).closest('#current-song-card').length > 0) {
      if (state == null || state.currentSong == null) {
        return;
      }
      key = state.currentSong.queueKey;
    } else {
      key = keyOfElement($(this));
    }
    if (key == -1) {
      return;
    }
    const other = $(this).siblings('.vote-down');
    if ($(this).hasClass('pressed')) {
      $(this).removeClass('pressed');
      localStorageSet('vote-' + key, '0', 7);
      vote($(this), key, -1);
    } else {
      $(this).addClass('pressed');
      if (other.hasClass('pressed')) {
        other.removeClass('pressed');
        vote($(this), key, 2);
      } else {
        vote($(this), key, 1);
      }
      localStorageSet('vote-' + key, '+', 7);
    }
  });
  $('#content').on('click tap', '.vote-down', function() {
    if (!canVote()) {
      return;
    }
    let key = -1;
    if ($(this).closest('#current-song-card').length > 0) {
      if (state == null || state.currentSong == null) {
        return;
      }
      key = state.currentSong.queueKey;
    } else {
      key = keyOfElement($(this));
    }
    if (key == -1) {
      return;
    }
    const other = $(this).siblings('.vote-up');
    if ($(this).hasClass('pressed')) {
      $(this).removeClass('pressed');
      localStorageSet('vote-' + key, '0', 7);
      vote($(this), key, 1);
    } else {
      $(this).addClass('pressed');
      if (other.hasClass('pressed')) {
        other.removeClass('pressed');
        vote($(this), key, -2);
      } else {
        vote($(this), key, -1);
      }
      localStorageSet('vote-' + key, '-', 7);
    }
  });
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  onReady();
});
