import 'bootstrap';
import 'jquerykeyframes';
import * as Cookies from 'js-cookie';

const toastTimeout = 2000;
let currentToastId = 0;

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
    $('#vote_timeout_bar').hide();
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
 * @param {Object} newState the new state that is used
 */
export function updateBaseState(newState) {
  $('#users').text(newState.users);
  $('#visitors').text(newState.visitors);
  if (newState.lights_enabled) {
    $('#lights_indicator').addClass('icon_enabled');
    $('#lights_indicator').removeClass('icon_disabled');
  } else {
    $('#lights_indicator').removeClass('icon_enabled');
    $('#lights_indicator').addClass('icon_disabled');
  }
  if (newState.partymode) {
    $('#favicon').attr('href', urls['party_icon']);
    $('#navbar_icon').attr('src', urls['party_icon']);
    $('#navbar_icon').css('visibility', 'visible');
    if (newState.alarm) {
      $('body').addClass('alarm');
      $('#progress_bar').addClass('alarm');
    } else {
      $('body').removeClass('alarm');
      $('#progress_bar').removeClass('alarm');
    }
  } else {
    $('#favicon').attr('href', urls['dark_icon']);
    if ($('#light_theme').hasClass('icon_enabled')) {
      $('#navbar_icon').attr('src', urls['normal_light_icon']);
    } else {
      $('#navbar_icon').attr('src', urls['normal_icon']);
    }
    $('#navbar_icon').css('visibility', 'visible');
  }

  if (Cookies.get('platform') === undefined) {
    Cookies.set('platform', newState.default_platform, {expires: 1});
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

    const animationName = 'marquee_' + span.attr('id') + '_' + $.now();
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

/** Reads the preferred platform from the cookies and updates the icons. */
function updatePlatformClasses() {
  $('#local').removeClass('icon_enabled');
  $('#youtube').removeClass('icon_enabled');
  $('#spotify').removeClass('icon_enabled');
  $('#soundcloud').removeClass('icon_enabled');
  $('#local').addClass('icon_disabled');
  $('#youtube').addClass('icon_disabled');
  $('#spotify').addClass('icon_disabled');
  $('#soundcloud').addClass('icon_disabled');
  if (Cookies.get('platform') == 'local') {
    $('#local').removeClass('icon_disabled');
    $('#local').addClass('icon_enabled');
  } else if (Cookies.get('platform') == 'youtube') {
    $('#youtube').removeClass('icon_disabled');
    $('#youtube').addClass('icon_enabled');
  } else if (Cookies.get('platform') == 'spotify') {
    $('#spotify').removeClass('icon_disabled');
    $('#spotify').addClass('icon_enabled');
  } else if (Cookies.get('platform') == 'soundcloud') {
    $('#soundcloud').removeClass('icon_disabled');
    $('#soundcloud').addClass('icon_enabled');
  }
}

/** Toggles between light and dark mode. */
function toggleTheme() {
  const oldStyleLink = $('#active-stylesheet').attr('href');
  const newStyleLink = $('#inactive-stylesheet').attr('href');
  if ($('#light_theme').hasClass('icon_enabled')) {
    $('#light_theme').removeClass('icon_enabled');
    $('#light_theme').addClass('icon_disabled');
    $('#dark_theme').removeClass('icon_disabled');
    $('#dark_theme').addClass('icon_enabled');
    if ($('#navbar_icon').attr('src') != urls['party_icon']) {
      $('#navbar_icon').attr('src', urls['normal_icon']);
    }
    $('#shareberry_icon').attr('src', urls['shareberry_dark_icon']);
  } else {
    $('#light_theme').removeClass('icon_disabled');
    $('#light_theme').addClass('icon_enabled');
    $('#dark_theme').removeClass('icon_enabled');
    $('#dark_theme').addClass('icon_disabled');
    if ($('#navbar_icon').attr('src') != urls['party_icon']) {
      $('#navbar_icon').attr('src', urls['normal_light_icon']);
    }
    $('#shareberry_icon').attr('src', urls['shareberry_light_icon']);
  }
  $('#active-stylesheet').attr('href', newStyleLink);
  $('#inactive-stylesheet').attr('href', oldStyleLink);
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
  decideScrolling($('#hashtag_text'), 0.030, 2);
}

/** Show the update banner if an update is available. */
export function handleUpdateBanner() {
  $('#goto_update').on('click tap', function() {
    location.href = '/settings/#show_changelog';
    if (location.pathname.endsWith('/settings/')) {
      location.reload();
    }
  });
  $('#remind_updates').on('click tap', function() {
    const tomorrow = new Date(new Date().getTime() + 24 * 60 * 60 * 1000);
    Cookies.set('ignore_updates', '', {expires: tomorrow});
    $('#update-banner').slideUp('fast');
  });
  $('#ignore_updates').on('click tap', function() {
    Cookies.set('ignore_updates', '', {expires: 365});
    $('#update-banner').slideUp('fast');
  });
  if (ADMIN) {
    if (Cookies.get('ignore_updates') === undefined) {
      $.get(urls['upgrade_available']).done(function(response) {
        if (response) {
          $('#update-banner').slideDown('fast');
        }
      });
    }
  }
}

/** General setup of the page. */
export function onReady() {
  // add the csrf token to every post request
  $.ajaxPrefilter(function(options, originalOptions, jqXHR) {
    if (options.type.toLowerCase() === 'post') {
      // initialize `data` to empty string if it does not exist
      options.data = options.data || '';
      // add leading ampersand if `data` is non-empty
      options.data += options.data ? '&' : '';
      // add _token entry
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
  const text = $('#hashtag_text_container');
  const input = $('#hashtag_input');

  // toggles the view between the hashtags text and the input form
  const hashtagToggler = function() {
    if (input.css('max-width') == '0') {
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
    if (text.css('max-width') == '0') {
      input.css('visibility', 'visible');
      input.removeClass('hidden');
      input.addClass('shown');
    }
  });
  input.bind('transitionend', function() {
    // if the input finished its removal transition,
    // initiate the text's appearance
    if (input.css('max-width') == '0') {
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
    $.post(urls['submit_hashtag'],
        {
          hashtag: $('#hashtag_input').val(),
        });
    $('#hashtag_input').val('');
    hashtagToggler();
  };
  $('#hashtag_plus').on('click tap', function(e) {
    if (text.css('max-width') == '0') {
      submitHashtag();
    } else {
      hashtagToggler();
    }
  });
  $('#hashtag_input').on('keypress', function(e) {
    if (e.which === 13) {
      submitHashtag();
    }
  });

  // enable/disable lights
  $('#lights_indicator').on('click tap', function() {
    $.post(urls['set_lights_shortcut'], {
      value: !$(this).hasClass('icon_enabled'),
    });
  });


  if ($('#active-stylesheet').attr('href').endsWith('dark.css')) {
    $('#light_theme').addClass('icon_disabled');
    $('#dark_theme').addClass('icon_enabled');
    if (Cookies.get('theme') == 'light') {
      toggleTheme();
    }
  } else {
    $('#light_theme').addClass('icon_enabled');
    $('#dark_theme').addClass('icon_disabled');
    $('#navbar_icon').attr('src', urls['normal_light_icon']);
    if (Cookies.get('theme') == 'dark') {
      toggleTheme();
    }
  }

  $('#light_theme').on('click tap', function() {
    if ($(this).hasClass('icon_enabled')) {
      return;
    }
    toggleTheme();
    Cookies.set('theme', 'light', {expires: 7});
  });
  $('#dark_theme').on('click tap', function() {
    if ($(this).hasClass('icon_enabled')) {
      return;
    }
    toggleTheme();
    Cookies.set('theme', 'dark', {expires: 7});
  });

  $('#local').on('click tap', function() {
    if ($(this).hasClass('icon_enabled')) {
      return;
    }
    Cookies.set('platform', 'local', {expires: 1});
    updatePlatformClasses();
  });
  $('#youtube').on('click tap', function() {
    if ($(this).hasClass('icon_enabled')) {
      return;
    }
    Cookies.set('platform', 'youtube', {expires: 1});
    updatePlatformClasses();
  });
  $('#spotify').on('click tap', function() {
    if ($(this).hasClass('icon_enabled')) {
      return;
    }
    Cookies.set('platform', 'spotify', {expires: 1});
    updatePlatformClasses();
  });
  $('#soundcloud').on('click tap', function() {
    if ($(this).hasClass('icon_enabled')) {
      return;
    }
    Cookies.set('platform', 'soundcloud', {expires: 1});
    updatePlatformClasses();
  });

  // request initial state update
  getState();

  // When called directly, the long running request to fetch the current version
  // prevents the websocket from being opened.
  setTimeout(handleUpdateBanner, 5000);
}

$(document).ready(onReady);
