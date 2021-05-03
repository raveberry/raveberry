import {keyOfElement} from './buttons';
import {state} from './update';
import {localStorageSet, warningToastWithBar} from '../base';

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

  /** Vote a song down.
   * @param {HTMLElement} button the button that was pressed to vote
   * @param {number} key the key of the voted song */
  function voteDown(button, key) {
    let votes = button.closest('.queue-entry').find('.queue-index');
    if (votes.length == 0) {
      votes = button.siblings('#current-song-votes');
    }
    votes.text(parseInt(votes.text()) - 1);
    $.post(urls['musiq']['vote-down'], {
      key: key,
    });
  }

  /** Vote a song up.
   * @param {HTMLElement} button the button that was pressed to vote
   * @param {number} key the key of the voted song */
  function voteUp(button, key) {
    let votes = button.closest('.queue-entry').find('.queue-index');
    if (votes.length == 0) {
      votes = button.siblings('#current-song-votes');
    }
    votes.text(parseInt(votes.text()) + 1);
    $.post(urls['musiq']['vote-up'], {
      key: key,
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
    const other = $(this).siblings('.vote-down');
    if ($(this).hasClass('pressed')) {
      $(this).removeClass('pressed');
      localStorageSet('vote-' + key, '0', 7);
      voteDown($(this), key);
    } else {
      $(this).addClass('pressed');
      if (other.hasClass('pressed')) {
        other.removeClass('pressed');
        voteUp($(this), key);
      }
      localStorageSet('vote-' + key, '+', 7);
      voteUp($(this), key);
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
    const other = $(this).siblings('.vote-up');
    if ($(this).hasClass('pressed')) {
      $(this).removeClass('pressed');
      localStorageSet('vote-' + key, '0', 7);
      voteUp($(this), key);
    } else {
      $(this).addClass('pressed');
      if (other.hasClass('pressed')) {
        other.removeClass('pressed');
        voteDown($(this), key);
      }
      localStorageSet('vote-' + key, '-', 7);
      voteDown($(this), key);
    }
  });
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  onReady();
});
