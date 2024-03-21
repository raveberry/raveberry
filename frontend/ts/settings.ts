import {
  localStorageGet,
  localStorageSet,
  localStorageRemove,
  registerSpecificState,
  infoToast,
  successToast,
  errorToast,
} from './base.js';
import {kebabize} from './util.js';
import 'jquery-ui/ui/widgets/autocomplete';
import snarkdown from 'snarkdown';

/** Update the settings state.
 * @param {Object} state an object containing all state information */
function updateState(state) {
  if (!('settings' in state)) {
    // this state is not meant for a settings update
    return;
  }

  for (const key in state.settings) {
    // Almost all keys in the state dictionary have a corresponding html element
    // Iterate through all of the keys and update the respective element.
    // Keys with no corresponding element are updated afterwards.
    if (!state.settings.hasOwnProperty(key)) {
      continue;
    }
    const value = state.settings[key];
    const element = $('#' + kebabize(key));
    if (element.is(':checkbox')) {
      element.prop('checked', value);
    } else if (element.is('input')) {
      element.val(value);
    } else if (element.is('select')) {
      element.val(value);
    } else if (element.is('div')) {
      element.text(value);
    } else if (element.is('span')) {
      element.text(value);
    }
  }

  $.each(state.settings.bluetoothDevices, function(index: number, device) {
    if (device.address ==$('.bluetooth-device').eq(index)
        .children().last().attr('id')) {
      return true;
    }
    const li = $('<li/>')
        .addClass('list-group-item')
        .addClass('list-item')
        .addClass('bluetooth-device');
    $('<label/>')
        .attr('for', 'bluetooth-device-' + index)
        .text(device.name)
        .appendTo(li);
    $('<input/>')
        .attr('type', 'radio')
        .attr('name', 'bluetooth-device')
        .attr('id', device.address)
        .appendTo(li);
    li.insertBefore($('#connect-bluetooth').parent());
  });

  // this field is not included in the generic values,
  // because the error is stored in the base state
  // and the settings state is not updated when the error changes
  if (state.playbackError) {
    $('#player-status').text('error');
  } else {
    $('#player-status').text('seems fine');
  }

  if (!state.settings.systemInstall) {
    $('.install-only').addClass('is-disabled');
    $('.install-only').attr('disabled-note',
        'This feature is only available in a system install.');
  } else {
    for (const module of
      ['hotspot', 'remote', 'youtube', 'spotify', 'soundcloud', 'jamendo']) {
      if (!state.settings[module + 'Configured']) {
        $('.' + module + '-functionality').addClass('is-disabled');
        $('.' + module + '-functionality').attr('disabled-note',
            'Please configure ' + module +
            ' during installation to use this feature.');
      }
    }
  }

  if (localStorageGet('ignore-updates') === null) {
    $('#update-information-policy option[value=yes]')
        .attr('selected', 'selected');
  } else {
    $('#update-information-policy option[value=no]')
        .attr('selected', 'selected');
  }
}

/** Add input handlers. */
export function onReady() {
  if (!window.location.pathname.endsWith('settings/')) {
    return;
  }
  registerSpecificState(updateState);

  /** Post the given data to the given url
   * @param {string} url the endpoint for the post
   * @param {Object} data the data that is sent
   * @param {function=} onSuccess a function that is called on success. */
  function post(url, data=undefined, onSuccess = () => {}) {
    $.post(url, data).done(function(response) {
      onSuccess();
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    infoToast('');
  }

  /** Register a handler for the given element that posts data on click
   * @param {string} key the id of the button and the key of the url
   * @param {function=} prePost a function that is called before the request.
   *                           needs to return the data that is transferred.
   * @param {function=} onSuccess a function that is called on success. */
  function registerPostOnClick(key, prePost = () => {
    return {};
  }, onSuccess = () => {}) {
    $('#' + key).on('click tap', function() {
      const data = prePost();
      post(urls['settings'][key], data, onSuccess);
    });
  }

  for (const key in urls['settings']) {
    if (!urls['settings'].hasOwnProperty(key)) {
      continue;
    }
    const url = urls['settings'][key];

    // all set-x urls post some data and show a toast with the result.
    // most of them are inputs or checkboxes with a simple 'value' field.
    // add this behavior to each of these elements
    if (key.startsWith('set-')) {
      const id = key.substr('set-'.length);
      const element = $('#' + id);
      if (element.is(':checkbox') || element.is('input')) {
        element.change(function() {
          let data;
          if (element.is(':checkbox')) {
            data = {value: element.is(':checked')};
          } else if (element.is('input')) {
            data = {value: element.val()};
          }
          post(url, data);
        });
      }
    }

    // all enable-x and disable-x urls send an empty post.
    // add this behaviour to each of the corresponding buttons
    if (key.startsWith('enable-') || key.startsWith('disable-')) {
      registerPostOnClick(key);
    }
  }

  $('#interactivity').on('change', function() {
    post(urls['settings']['set-interactivity'],
        {value: (<HTMLInputElement> this).value});
  });

  $('#color-indication').on('change', function() {
    post(urls['settings']['set-color-indication'],
        {value: (<HTMLInputElement> this).value});
  });

  registerPostOnClick('trigger-alarm');

  registerPostOnClick('check-internet');
  registerPostOnClick('update-user-count');

  function update_authorize_url() {
    const client_id = $('#spotify-device-client-id').val();
    const redirect_uri = $('#spotify-redirect-uri').val();

    if (!client_id || !redirect_uri) {
      $('#spotify-authorize-url').empty();
      $('#spotify-authorize-url').text("Fill out previous fields");
      return;
    }

    const parameters = {
      "client_id": client_id,
      "response_type": "code",
      "redirect_uri": redirect_uri,
      "scope": SPOTIFY_SCOPE,
    }
    let url = SPOTIFY_OAUTH_AUTHORIZE_URL + "?";
    let first = true;
    for (const key in parameters) {
      if (first) {
        first = false;
      } else {
        url += "&";
      }
      url += key + "=" + encodeURIComponent(parameters[key]);
    }

    $('#spotify-authorize-url').empty();
    $("<a>")
        .attr("href",url)
        .attr("target","_blank")
        .attr("rel", "noopener")
        .text("click me")
        .appendTo($('#spotify-authorize-url'));

  }
  $('#spotify-client-id').on("change", update_authorize_url);
  $('#spotify-redirect-uri').on("change", update_authorize_url);
  update_authorize_url();

  registerPostOnClick('set-spotify-device-credentials', () => {
    return {
      client_id: $('#spotify-device-client-id').val(),
      client_secret: $('#spotify-device-client-secret').val(),
      redirect_uri: $('#spotify-redirect-uri').val(),
      authorized_url: $('#spotify-authorized-url').val(),
    };
  });

  registerPostOnClick('set-spotify-mopidy-credentials', () => {
    return {
      username: $('#spotify-username').val(),
      password: $('#spotify-password').val(),
      client_id: $('#spotify-mopidy-client-id').val(),
      client_secret: $('#spotify-mopidy-client-secret').val(),
    };
  });

  registerPostOnClick('set-soundcloud-credentials', () => {
    return {
      auth_token: $('#soundcloud-auth-token').val(),
    };
  });

  registerPostOnClick('set-jamendo-credentials', () => {
    return {
      client_id: $('#jamendo-client-id').val(),
    };
  });

  // Remove old devices when restarting scanning. Don't use registerPostOnClick,
  // as the generic approach already assigns post functionality to this element.
  $('#bluetooth-scanning').on('click tap', () => {
    const checked = $('#bluetooth-scanning').is(':checked');
    if (checked) {
      $('.bluetooth-device').remove();
    }
  });

  registerPostOnClick('connect-bluetooth', () => {
    return {address: $('input[name=bluetooth-device]:checked').attr('id')};
  });

  registerPostOnClick('disconnect-bluetooth');

  $('#output').on('focus', function() {
    $.get(urls['settings']['list-outputs']).done(function(devices) {
      $('#output').empty();
      $.each(devices, function(index: number, device) {
        $('<option>').attr('data-id', device.id).text(device.name).appendTo($('#output'));
      });
    });
  });
  $('#output').on('change', function() {
    const selected = $("#output option:selected");
    post(urls['settings']['set-output'], {value: selected.data("id")});
  });

  registerPostOnClick('delete-current-song');
  registerPostOnClick('restart-player');

  $('#wifi-ssid').focus(function() {
    $.get(urls['settings']['available-ssids']).done(function(ssids) {
      const availableSsids = ssids;
      $('#wifi-ssid').autocomplete({
        source: availableSsids,
        minLength: 0,
      });
      $('#wifi-ssid').autocomplete('search');
    });
  });

  registerPostOnClick('connect-to-wifi', () => {
    return {
      ssid: $('#wifi-ssid').val(),
      password: $('#wifi-password').val(),
    };
  }, () => {
    $('#wifi-ssid').val('');
    $('#wifi-password').val('');
  });

  $('#homewifi-ssid').focus(function() {
    $.get(urls['settings']['stored-ssids']).done(function(ssids) {
      const storedSsids = ssids;
      $('#homewifi-ssid').autocomplete({
        source: storedSsids,
        minLength: 0,
      });
      $('#homewifi-ssid').autocomplete('search');
    });
  });

  let keepSubdirsOpen = true;
  $('#library-path').autocomplete({
    source: function(request, response) {
      $.get(urls['settings']['list-subdirectories'], {
        'path': request.term,
      }).done(function(subdirectories) {
        const doneEntry = {
          'value': 'done',
        };
        subdirectories.unshift(doneEntry);
        response(subdirectories);
      });
    },
    select: function(event, ui) {
      if (ui.item.value == 'done') {
        keepSubdirsOpen = false;
        return false;
      }
    },
    close: function() {
      if (keepSubdirsOpen) {
        $('.ui-autocomplete').show();
        $('#library-path').autocomplete('search');
      }
    },
  });
  $('#library-path').on('click tap', function() {
    keepSubdirsOpen = true;
    $('#library-path').autocomplete('search');
  });
  registerPostOnClick('scan-library', () => {
    return {
      library_path: $('#library-path').val(),
    };
  });
  registerPostOnClick('create-playlists');

  const today = new Date();
  const yesterday = new Date();
  // https://stackoverflow.com/a/13052187
  const toDateInputValue = function(date) {
    const local = new Date(date);
    local.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return local.toJSON().slice(0, 10);
  };
  yesterday.setDate(today.getDate() - 1);
  $('#startdate').val(toDateInputValue(yesterday));
  $('#starttime').val('12:00');
  $('#enddate').val(toDateInputValue(today));
  $('#endtime').val(today.toLocaleTimeString('en-GB', {
    hour: 'numeric',
    minute: 'numeric',
  }));
  $('#analyse').on('click tap', function() {
    $.get(urls['settings']['analyse'], {
      startdate: $('#startdate').val(),
      starttime: $('#starttime').val(),
      enddate: $('#enddate').val(),
      endtime: $('#endtime').val(),
    }).done(function(data) {
      $('#songs-played').text(data['songsPlayed']);
      $('#most-played-song').text(data['mostPlayedSong']);
      $('#votes-cast').text(data['votesCast']);
      $('#highest-voted-song').text(data['highestVotedSong']);
      $('#most-active-device').text(data['mostActiveDevice']);
      $('#request-activity').text(data['requestActivity']);
      $('#playlist').text(data['playlist']);
      successToast('');
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#copy-playlist').on('click tap', function() {
    const temp = $('<textarea>');
    $('body').append(temp);
    temp.val($('#playlist').text()).select();
    document.execCommand('copy');
    temp.remove();
  });
  registerPostOnClick('save-as-playlist', () => {
    return {
      startdate: $('#startdate').val(),
      starttime: $('#starttime').val(),
      enddate: $('#enddate').val(),
      endtime: $('#endtime').val(),
      name: $('#saved-playlist-name').val(),
    };
  });

  registerPostOnClick('restart-server');
  registerPostOnClick('kill-workers');
  registerPostOnClick('reboot-system');
  registerPostOnClick('shutdown-system');

  $('#get-latest-version').on('click tap', function() {
    $.get(urls['settings']['get-latest-version']).done(function(response) {
      $('#latest-version').text(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#update-information-policy').on('change', function() {
    if ((<HTMLInputElement> this).value == 'yes') {
      localStorageRemove('ignore-updates');
    } else {
      localStorageSet('ignore-updates', '', 365);
    }
  });
  $('#open-changelog').on('click tap', function() {
    $.get(urls['settings']['get-changelog']).done(function(response) {
      $('#changelog').html(snarkdown(response));
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    $('#changelog-modal').modal('show');
  });
  $('#changelog-ok').on('click tap', function() {
    $('#changelog-modal').modal('hide');
  });
  $('#open-upgrade-dialog').on('click tap', function() {
    $.get(urls['settings']['get-upgrade-config']).done(function(response) {
      $('#upgrade-config').text(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    $('#upgrade-modal').modal('show');
  });
  $('#confirm-upgrade').on('click tap', function() {
    $('#upgrade-modal').modal('hide');
    post(urls['settings']['upgrade-raveberry']);
  });

  const collapseAnimationOptions = {
    // slideToggle
    height: 'toggle',
    marginTop: 'toggle',
    marginBottom: 'toggle',
    paddingTop: 'toggle',
    paddingBottom: 'toggle',
    // fadeToggle
    opacity: 'toggle',
  };

  // show basic settings by default
  if (localStorageGet('Basic Settings:collapsed') === null) {
    localStorageSet('Basic Settings:collapsed', false);
  }

  $('.list-header').each((_, li) => {
    const storageKey = $(li).children('span').text() + ':collapsed';
    if (localStorageGet(storageKey) === false) {
      $(li).siblings('.list-item').animate(collapseAnimationOptions, 'fast');
      // explicitly set display: flex, otherwise the layout is broken.
      $(li).siblings('.list-item').css('display', 'flex');
      $(li).children('.settings-collapser').toggleClass('collapsed');
    }
  });

  $('.list-header').on('click tap', function() {
    $(this).siblings('.list-item').animate(collapseAnimationOptions, 'fast');
    $(this).siblings('.list-item').css('display', 'flex');
    $(this).children('.settings-collapser').toggleClass('collapsed');

    const storageKey = $(this).children('span').text() + ':collapsed';
    localStorageSet(storageKey,
        $(this).children('.settings-collapser').hasClass('collapsed'));
  });

  const fragment = window.location.hash.substr(1);
  if (fragment == 'show-changelog') {
    $('#about').siblings('.list-item')
        .animate(collapseAnimationOptions, 'fast');
    $('#about').siblings('.list-item').css('display', 'flex');
    $('#about').children('.settings-collapser').toggleClass('collapsed');
    $('#update-banner').remove();
    $.get(urls['settings']['get-changelog']).done(function(response) {
      $('#changelog').html(snarkdown(response));
      $.each(response.split('\n'), (_, line) => {
        const tokens = line.split(/\s+/);
        if (tokens[0] == '##') {
          const version = tokens[1];
          $('#latest-version').text(version);
          return false;
        }
      });
    });
    const scrollDuration = 1000;
    $('html, body').animate({scrollTop: $('#about').offset().top},
        scrollDuration);
    setTimeout(function() {
      $('#changelog-modal').modal('show');
    }, scrollDuration);
  }
}

$(document).ready(onReady);
