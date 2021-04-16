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
    $('#vote_timeout_bar').css('transition', 'none');
    $('#vote_timeout_bar').css('width', ratio * 100 + '%');
    $('#vote_timeout_bar')[0].offsetHeight;
    $('#vote_timeout_bar').css({
      'transition': 'width ' + ratio * bucketLifetime / 1000 + 's linear',
      'width': '0%',
    });
    return false;
  }

  /** Vote a song down.
   * @param {HTMLElement} button the button that was pressed to vote
   * @param {number} key the key of the voted song */
  function voteDown(button, key) {
    let votes = button.closest('.queue_entry').find('.queue_index');
    if (votes.length == 0) {
      votes = button.siblings('#current_song_votes');
    }
    votes.text(parseInt(votes.text()) - 1);
    $.post(urls['musiq']['vote_down'], {
      key: key,
    });
  }

  /** Vote a song up.
   * @param {HTMLElement} button the button that was pressed to vote
   * @param {number} key the key of the voted song */
  function voteUp(button, key) {
    let votes = button.closest('.queue_entry').find('.queue_index');
    if (votes.length == 0) {
      votes = button.siblings('#current_song_votes');
    }
    votes.text(parseInt(votes.text()) + 1);
    $.post(urls['musiq']['vote_up'], {
      key: key,
    });
  }

  $('#content').on('click tap', '.vote_up', function() {
    if (!canVote()) {
      return;
    }
    let key = -1;
    if ($(this).closest('#current_song_card').length > 0) {
      if (state == null || state.current_song == null) {
        return;
      }
      key = state.current_song.queue_key;
    } else {
      key = keyOfElement($(this));
    }
    const other = $(this).siblings('.vote_down');
    if ($(this).hasClass('pressed')) {
      $(this).removeClass('pressed');
      localStorageSet('vote_' + key, '0', 7);
      voteDown($(this), key);
    } else {
      $(this).addClass('pressed');
      if (other.hasClass('pressed')) {
        other.removeClass('pressed');
        voteUp($(this), key);
      }
      localStorageSet('vote_' + key, '+', 7);
      voteUp($(this), key);
    }
  });
  $('#content').on('click tap', '.vote_down', function() {
    if (!canVote()) {
      return;
    }
    let key = -1;
    if ($(this).closest('#current_song_card').length > 0) {
      if (state == null || state.current_song == null) {
        return;
      }
      key = state.current_song.queue_key;
    } else {
      key = keyOfElement($(this));
    }
    const other = $(this).siblings('.vote_up');
    if ($(this).hasClass('pressed')) {
      $(this).removeClass('pressed');
      localStorageSet('vote_' + key, '0', 7);
      voteUp($(this), key);
    } else {
      $(this).addClass('pressed');
      if (other.hasClass('pressed')) {
        other.removeClass('pressed');
        voteDown($(this), key);
      }
      localStorageSet('vote_' + key, '-', 7);
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
