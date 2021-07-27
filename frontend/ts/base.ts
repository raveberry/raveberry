import 'bootstrap';
import 'jquerykeyframes';

const toastTimeout = 2000;
let currentToastId = 0;

/** Stores the given key value pair in local storage with an expiry date.
 * @param {string} key the key of the value to store
 * @param {string} value the value to store for the key
 * @param {number} [ttl] the number of days after which this entry expires
 */
export function localStorageSet(key, value, ttl?) {
  let expiryTime = null;
  if (ttl != null) {
    const date = new Date();
    date.setDate(date.getDate() + ttl);
    expiryTime = date.getTime();
  }

  const item = {
    value: value,
    expiry: expiryTime,
  };
  localStorage.setItem(key, JSON.stringify(item));
}
/** Retrieves the value for the given key from local storage,
 * respecting the expiration time.
 * @param {string} key the key of the value to retrieve
 * @return {?string} value value or null if expired or not stored
 */
export function localStorageGet(key) {
  const itemStr = localStorage.getItem(key);
  // if the item doesn't exist, return null
  if (!itemStr) {
    return null;
  }
  const item = JSON.parse(itemStr);
  if (item.expiry) {
    const now = new Date();
    if (now.getTime() > item.expiry) {
      localStorage.removeItem(key);
      return null;
    }
  }
  return item.value;
}
/** Deletes the entry for the given key from local storage.
 * @param {string} key the key to remove
 */
export function localStorageRemove(key) {
  localStorage.removeItem(key);
}

/** Shows a toast to inform the user.
 * @param {string} firstLine the main content of the toast
 * @param {string} [secondLine] an optional second line to be shown
 */
export function infoToast(firstLine, secondLine?) {
  $('#info-toast').find('.toast-content').text(firstLine);
  $('#info-toast').find('.toast-content').text(firstLine);
  if (secondLine != null) {
    $('#info-toast').find('.toast-content').append($('<br/>'));
    $('#info-toast').find('.toast-content').append(secondLine);
  }
  $('#success-toast').fadeOut();
  $('#warning-toast').fadeOut();
  $('#error-toast').fadeOut();
  $('#info-toast').fadeIn();
  currentToastId++;
  const showedToastId = currentToastId;
  setTimeout(function() {
    if (showedToastId == currentToastId) {
      $('#info-toast').fadeOut();
    }
  }, toastTimeout);
}

/** Shows a toast to inform the user that something happened successfully.
 * @param {string} firstLine the main content of the toast
 * @param {string} [secondLine] an optional second line to be shown
 */
export function successToast(firstLine, secondLine?) {
  $('#success-toast').find('.toast-content').text(firstLine);
  if (secondLine != null) {
    $('#success-toast').find('.toast-content').append($('<br/>'));
    $('#success-toast').find('.toast-content').append(secondLine);
  }
  $('#info-toast').fadeOut();
  $('#warning-toast').fadeOut();
  $('#error-toast').fadeOut();
  $('#success-toast').fadeIn();
  currentToastId++;
  const showedToastId = currentToastId;
  setTimeout(function() {
    if (showedToastId == currentToastId) {
      $('#success-toast').fadeOut();
    }
  }, toastTimeout);
}

/** Shows a toast to warn the user.
 * @param {string} firstLine the main content of the toast
 * @param {string} [secondLine] an optional second line to be shown
 * @param {boolean} [showBar] determines whether a time bar should be shown.
 */
export function warningToast(firstLine, secondLine?, showBar?) {
  if (!showBar) {
    $('#vote-timeout-bar').hide();
  }
  $('#warning-toast').find('.toast-content').text(firstLine);
  if (secondLine != null) {
    $('#warning-toast').find('.toast-content').append($('<br/>'));
    $('#warning-toast').find('.toast-content').append(secondLine);
  }
  $('#info-toast').fadeOut();
  $('#success-toast').fadeOut();
  $('#error-toast').fadeOut();
  $('#warning-toast').fadeIn();
  currentToastId++;
  const showedToastId = currentToastId;
  setTimeout(function() {
    if (showedToastId == currentToastId) {
      $('#warning-toast').fadeOut();
    }
  }, toastTimeout);
}

/** Wrapper that shows a toast without a bar.
 * @param {string} firstLine the main content of the toast
 * @param {string} [secondLine] an optional second line to be shown
 */
export function warningToastWithBar(firstLine, secondLine?) {
  warningToast(firstLine, secondLine, true);
}

/** Shows a toast to inform the user about an error.
 * @param {string} firstLine the main content of the toast
 * @param {string} [secondLine] an optional second line to be shown
 */
export function errorToast(firstLine, secondLine?) {
  $('#error-toast').find('.toast-content').text(firstLine);
  if (secondLine != null) {
    $('#error-toast').find('.toast-content').append($('<br/>'));
    $('#error-toast').find('.toast-content').append(secondLine);
  }
  $('#info-toast').fadeOut();
  $('#success-toast').fadeOut();
  $('#warning-toast').fadeOut();
  $('#error-toast').fadeIn();
  currentToastId++;
  const showedToastId = currentToastId;
  setTimeout(function() {
    if (showedToastId == currentToastId) {
      $('#error-toast').fadeOut();
    }
  }, toastTimeout);
}

/** Updates the page's base content. Shared across all pages.
 * @param {Object} state the new state that is used
 */
export function updateBaseState(state) {
  $('#users').text(state.users);
  $('#visitors').text(state.visitors);
  if (state.lightsEnabled) {
    $('#lights-indicator').addClass('icon-enabled');
    $('#lights-indicator').removeClass('icon-disabled');
  } else {
    $('#lights-indicator').removeClass('icon-enabled');
    $('#lights-indicator').addClass('icon-disabled');
  }
  if (state.partymode) {
    $('#navbar-icon').addClass('partymode');
  } else {
    $('#navbar-icon').removeClass('partymode');
  }
  if (state.alarm) {
    $('body').addClass('alarm');
    $('#progress-bar').addClass('alarm');
  } else {
    $('body').removeClass('alarm');
    $('#progress-bar').removeClass('alarm');
  }

  if (localStorageGet('platform') === null) {
    localStorageSet('platform', state.defaultPlatform, 1);
  }

  updatePlatformClasses();
}

// this default behaviors can be overwritten by individual pages
const specificStates = [];

/** Adds a new function that is called with a received state update.
 * @param {callback} f function that should be called on every state update
 */
export function registerSpecificState(f) {
  specificStates.push(f);
}

/** This function is called everytime a new state is received from the server.
 * @param {Object} newState the state that was received
 */
export function updateState(newState) {
  updateBaseState(newState);

  for (const specificState of specificStates) {
    specificState(newState);
  }
}

/** Requests a state update from the server and applies it. */
export function getState() {
  $.get(urls['state'], function(state) {
    updateState(state);
  });
}

/** Resync the state with the server. */
export function reconnect() {
  getState();
}

/** Applies autoscrolling for the given span if necessary.
 * @param {HTMLElement} span the span whose text content is checked.
 * @param {number} secondsPerPixel the scroll rate
 * @param {number} staticSeconds how long the text should rest between scrolls
 */
export function decideScrolling(span, secondsPerPixel, staticSeconds) {
  const spaceAvailable = span.parent().width();
  const spaceNeeded = span.width();
  if (spaceAvailable < spaceNeeded) {
    // an overflow is happening, start scrolling

    const spaceOverflowed = spaceNeeded - spaceAvailable;
    const ratio = spaceOverflowed / spaceNeeded;

    const movingSeconds = spaceOverflowed * secondsPerPixel;
    const duration = (staticSeconds + movingSeconds) * 2;

    const animationName = 'marquee-' + span.attr('id') + '-' + $.now();
    const keyframes = {};
    keyframes['name'] = animationName;
    keyframes['0%'] = {transform: 'translate(0, 0)'};
    keyframes[staticSeconds / duration * 100 + '%'] =
      {transform: 'translate(0, 0)'};
    keyframes[(staticSeconds + movingSeconds) / duration * 100 + '%'] =
      {transform: 'translate(-' + ratio * 100 + '%, 0)'};
    keyframes[(staticSeconds * 2 + movingSeconds) / duration * 100 + '%'] =
      {transform: 'translate(-' + ratio * 100 + '%, 0)'};
    keyframes[(staticSeconds * 2 + movingSeconds * 2) / duration * 100 + '%'] =
      {transform: 'translate(0, 0)'};
    $.keyframe.define([keyframes]);

    span.css('animation-name', animationName);
    span.css('animation-duration', duration + 's');
    span.css('animation-timing-function', 'linear');
    span.css('animation-iteration-count', 'infinite');

    span.addClass('autoscrolling');
  } else {
    span.removeClass('autoscrolling');
  }
}

/** Reads the preferred platform from local storage and updates the icons. */
function updatePlatformClasses() {
  $('#local').removeClass('icon-enabled');
  $('#youtube').removeClass('icon-enabled');
  $('#spotify').removeClass('icon-enabled');
  $('#soundcloud').removeClass('icon-enabled');
  $('#jamendo').removeClass('icon-enabled');
  $('#local').addClass('icon-disabled');
  $('#youtube').addClass('icon-disabled');
  $('#spotify').addClass('icon-disabled');
  $('#soundcloud').addClass('icon-disabled');
  $('#jamendo').addClass('icon-disabled');
  if (localStorageGet('platform') == 'local') {
    $('#local').removeClass('icon-disabled');
    $('#local').addClass('icon-enabled');
  } else if (localStorageGet('platform') == 'youtube') {
    $('#youtube').removeClass('icon-disabled');
    $('#youtube').addClass('icon-enabled');
  } else if (localStorageGet('platform') == 'spotify') {
    $('#spotify').removeClass('icon-disabled');
    $('#spotify').addClass('icon-enabled');
  } else if (localStorageGet('platform') == 'soundcloud') {
    $('#soundcloud').removeClass('icon-disabled');
    $('#soundcloud').addClass('icon-enabled');
  } else if (localStorageGet('platform') == 'jamendo') {
    $('#jamendo').removeClass('icon-disabled');
    $('#jamendo').addClass('icon-enabled');
  }
}

/** Toggles between light and dark mode. */
function toggleTheme() {
  if ($('html').hasClass('light')) {
    $('html').removeClass('light');

    $('#light-theme').removeClass('icon-enabled');
    $('#light-theme').addClass('icon-disabled');
    $('#dark-theme').removeClass('icon-disabled');
    $('#dark-theme').addClass('icon-enabled');
  } else {
    $('html').addClass('light');

    $('#light-theme').removeClass('icon-disabled');
    $('#light-theme').addClass('icon-enabled');
    $('#dark-theme').removeClass('icon-enabled');
    $('#dark-theme').addClass('icon-disabled');
  }
}

/** Updates the height of the container so toasts always show at the bottom. */
function setToastHeight() {
  $('#toast-container').css('height', window.innerHeight);
}

/** Adds the ripple effect to clickable buttons */
function ripple() {
  // Remove any old one
  $('.ripple').remove();

  let buttonWidth = $(this).width();
  let buttonHeight = $(this).height();
  let x = null;
  let y = null;
  if ($(this).parent().hasClass('anim-container')) {
    x = parseInt($(this).css('margin-left')) +
      parseInt($(this).css('padding-left'));
    y = parseInt($(this).css('margin-top')) +
      parseInt($(this).css('padding-top'));
    // compensate one-sided margin hack
    x += (parseInt($(this).parent().css('margin-right')) -
      parseInt($(this).parent().css('margin-left'))) / 3;

    // Add the element to the parent element, since it does not move
    $(this).parent().prepend('<span class=\'ripple\'></span>');
  } else {
    // Get the center of the $(this)
    x = $(this).position().left +
      parseInt($(this).css('margin-left')) +
      parseInt($(this).css('padding-left'));
    y = $(this).position().top +
      parseInt($(this).css('margin-top')) +
      parseInt($(this).css('padding-top'));

    // Add the element
    $(this).prepend('<span class=\'ripple\'></span>');
  }

  // Make it round!
  buttonWidth = buttonHeight = Math.max(buttonWidth, buttonHeight);

  // Add the ripples CSS and start the animation
  $('.ripple').css({
    width: buttonWidth,
    height: buttonHeight,
    top: y + 'px',
    left: x + 'px',
  }).addClass('rippleEffect');
}

/** Apply autoscrolling to the hashtag if necessary. */
function decideHashtagScrolling() {
  decideScrolling($('#hashtag-text'), 0.030, 2);
}

/** Show the update banner if an update is available. */
export function handleUpdateBanner() {
  $('#goto-update').on('click tap', function() {
    location.href = '/settings/#show-changelog';
    if (location.pathname.endsWith('/settings/')) {
      location.reload();
    }
  });
  $('#remind-updates').on('click tap', function() {
    localStorageSet('ignore-updates', '', 1);
    $('#update-banner').slideUp('fast');
  });
  $('#ignore-updates').on('click tap', function() {
    localStorageSet('ignore-updates', '', 365);
    $('#update-banner').slideUp('fast');
  });
  if (ADMIN) {
    if (localStorageGet('ignore-updates') === null) {
      $.get(urls['upgrade-available']).done(function(response) {
        if (response) {
          $('#update-banner').slideDown('fast');
        }
      });
    }
  }
}

/** General setup of the page. */
export function onReady() {
  if (localStorageGet('theme') == 'light') {
    $('html').addClass('light');
    $('#light-theme').addClass('icon-enabled');
    $('#dark-theme').addClass('icon-disabled');
  } else {
    $('#light-theme').addClass('icon-disabled');
    $('#dark-theme').addClass('icon-enabled');
  }

  // add the csrf token to every post request
  $.ajaxPrefilter(function(options, originalOptions, jqXHR) {
    if (options.type.toLowerCase() === 'post') {
      // initialize `data` to empty string if it does not exist
      options.data = options.data || '';
      // add leading ampersand if `data` is non-empty
      options.data += options.data ? '&' : '';
      // add csrf token entry
      options.data += 'csrfmiddlewaretoken=' + encodeURIComponent(CSRF_TOKEN);
    }
  });

  // initialize toasts
  $('.toast').toast({
    delay: 3000,
  });

  $(window).on('resize', setToastHeight);
  setToastHeight();

  $(document).on('click tap', '.fas', ripple);
  $(document).on('click tap', '.fab', ripple);

  // Hashtag transition animation
  const text = $('#hashtag-text-container');
  const input = $('#hashtag-input');

  // toggles the view between the hashtags text and the input form
  const hashtagToggler = function() {
    if (input.css('max-width').startsWith('0')) {
      // if the input is invisible, initiate the texts removal transition
      text.removeClass('shown');
      text.addClass('hidden');
    } else {
      // if the text is invisible, the input is visible. remove it
      input.removeClass('shown');
      input.addClass('hidden');
    }
  };

  text.on('click', hashtagToggler);
  // bind input enter

  text.bind('transitionend', function() {
    // if the text finished its removal transition,
    // initiate the input's appearance
    if (text.css('max-width').startsWith('0')) {
      input.css('visibility', 'visible');
      input.removeClass('hidden');
      input.addClass('shown');
    }
  });
  input.bind('transitionend', function() {
    // if the input finished its removal transition,
    // initiate the text's appearance
    if (input.css('max-width').startsWith('0')) {
      input.css('visibility', 'hidden');
      text.removeClass('hidden');
      text.addClass('shown');
    } else {
      // if it is now visible, give it focus
      input.focus();
    }
  });
  $(window).on('resize', decideHashtagScrolling);
  decideHashtagScrolling();

  // submit hashtags
  const submitHashtag = function() {
    $.post(urls['submit-hashtag'],
        {
          hashtag: $('#hashtag-input').val(),
        });
    $('#hashtag-input').val('');
    hashtagToggler();
  };
  $('#hashtag-plus').on('click tap', function(e) {
    if (text.css('max-width').startsWith('0')) {
      submitHashtag();
    } else {
      hashtagToggler();
    }
  });
  $('#hashtag-input').on('keypress', function(e) {
    if (e.which === 13) {
      submitHashtag();
    }
  });

  // enable/disable lights
  $('#lights-indicator').on('click tap', function() {
    $.post(urls['set-lights-shortcut'], {
      value: !$(this).hasClass('icon-enabled'),
    });
  });

  $('#light-theme').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    toggleTheme();
    localStorageSet('theme', 'light');
  });
  $('#dark-theme').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    toggleTheme();
    localStorageSet('theme', 'dark');
  });

  $('#local').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    localStorageSet('platform', 'local', 1);
    updatePlatformClasses();
  });
  $('#youtube').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    localStorageSet('platform', 'youtube', 1);
    updatePlatformClasses();
  });
  $('#spotify').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    localStorageSet('platform', 'spotify', 1);
    updatePlatformClasses();
  });
  $('#soundcloud').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    localStorageSet('platform', 'soundcloud', 1);
    updatePlatformClasses();
  });
  $('#jamendo').on('click tap', function() {
    if ($(this).hasClass('icon-enabled')) {
      return;
    }
    localStorageSet('platform', 'jamendo', 1);
    updatePlatformClasses();
  });

  // request initial state update
  getState();

  handleUpdateBanner();
}

$(document).ready(onReady);
