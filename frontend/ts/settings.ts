import {
  localStorageGet,
  localStorageSet,
  localStorageRemove,
  registerSpecificState,
  infoToast,
  successToast,
  errorToast,
} from './base.js';
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
    const element = $('#' + key );
    if (element.is(':checkbox')) {
      element.prop('checked', value);
    } else if (element.is('input')) {
      element.val(value);
    } else if (element.is('div')) {
      element.text(value);
    } else if (element.is('span')) {
      element.text(value);
    }
  }

  $.each(state.settings.bluetooth_devices, function(index: number, device) {
    if (device.address ==$('.bluetooth_device').eq(index)
        .children().last().attr('id')) {
      return true;
    }
    const li = $('<li/>')
        .addClass('list-group-item')
        .addClass('list_item')
        .addClass('bluetooth_device');
    $('<label/>')
        .attr('for', 'bluetooth_device_' + index)
        .text(device.name)
        .appendTo(li);
    $('<input/>')
        .attr('type', 'radio')
        .attr('name', 'bluetooth_device')
        .attr('id', device.address)
        .appendTo(li);
    li.insertBefore($('#connect_bluetooth').parent());
  });

  if (!state.settings.system_install) {
    $('.system-install-only').addClass('is-disabled');
    $('.system-install-only').attr('disabled-note',
        'This feature is only available in a system install.');
  } else {
    for (const module of ['hotspot', 'remote', 'youtube', 'spotify', 'soundcloud']) {
      if (!state.settings[module + '_configured']) {
        $('.' + module + '-functionality').addClass('is-disabled');
        $('.' + module + '-functionality').attr('disabled-note',
            'Please configure ' + module + ' during installation to use this feature.');
      }
    }
  }

  if (localStorageGet('ignore_updates') === null) {
    $('#update_information_policy option[value=yes]')
        .attr('selected', 'selected');
  } else {
    $('#update_information_policy option[value=no]')
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

    // all set_x urls post some data and show a toast with the result.
    // most of them are inputs or checkboxes with a simple 'value' field.
    // add this behavior to each of these elements
    if (key.startsWith('set_')) {
      const id = key.substr('set_'.length);
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

    // all enable_x and disable_x urls send an empty post.
    // add this behaviour to each of the corresponding buttons
    if (key.startsWith('enable_') || key.startsWith('disable_')) {
      registerPostOnClick(key);
    }
  }

  registerPostOnClick('check_internet');
  registerPostOnClick('update_user_count');

  registerPostOnClick('set_spotify_credentials', () => {
    return {
      username: $('#spotify_username').val(),
      password: $('#spotify_password').val(),
      client_id: $('#spotify_client_id').val(),
      client_secret: $('#spotify_client_secret').val(),
    };
  });

  registerPostOnClick('set_soundcloud_credentials', () => {
    return {
      auth_token: $('#soundcloud_auth_token').val(),
    };
  });

  registerPostOnClick('set_bluetooth_scanning', () => {
    const checked = $('#set_bluetooth_scanning').is(':checked');
    if (checked) {
      $('.bluetooth_device').remove();
    }
    return {value: checked};
  });

  registerPostOnClick('connect_bluetooth', () => {
    return {address: $('input[name=bluetooth_device]:checked').attr('id')};
  });

  registerPostOnClick('disconnect_bluetooth');

  $('#output').focus(function() {
    $.get(urls['settings']['list_outputs']).done(function(devices) {
      $('#output').autocomplete({
        // always show all possible output devices,
        // regardless of current input content
        source: function(request, response) {
          response(devices);
        },
        close: function() {
          // manually trigger the change event when an element is clicked
          // in order to send the post request
          $('#output').trigger('change');
        },
        minLength: 0,
      });
      $('#output').autocomplete('search');
    });
  });

  $('#wifi_ssid').focus(function() {
    $.get(urls['settings']['available_ssids']).done(function(ssids) {
      const availableSsids = ssids;
      $('#wifi_ssid').autocomplete({
        source: availableSsids,
        minLength: 0,
      });
      $('#wifi_ssid').autocomplete('search');
    });
  });

  registerPostOnClick('connect_to_wifi', () => {
    return {
      ssid: $('#wifi_ssid').val(),
      password: $('#wifi_password').val(),
    };
  }, () => {
    $('#wifi_ssid').val('');
    $('#wifi_password').val('');
  });

  $('#homewifi_ssid').focus(function() {
    $.get(urls['settings']['stored_ssids']).done(function(ssids) {
      const storedSsids = ssids;
      $('#homewifi_ssid').autocomplete({
        source: storedSsids,
        minLength: 0,
      });
      $('#homewifi_ssid').autocomplete('search');
    });
  });

  let keepSubdirsOpen = true;
  $('#library_path').autocomplete({
    source: function(request, response) {
      $.get(urls['settings']['list_subdirectories'], {
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
        $('#library_path').autocomplete('search');
      }
    },
  });
  $('#library_path').on('click tap', function() {
    keepSubdirsOpen = true;
    $('#library_path').autocomplete('search');
  });
  registerPostOnClick('scan_library', () => {
    return {
      library_path: $('#library_path').val(),
    };
  });
  registerPostOnClick('create_playlists');

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
      $('#songs_played').text(data['songs_played']);
      $('#most_played_song').text(data['most_played_song']);
      $('#votes_cast').text(data['votes_cast']);
      $('#highest_voted_song').text(data['highest_voted_song']);
      $('#most_active_device').text(data['most_active_device']);
      $('#request_activity').text(data['request_activity']);
      $('#playlist').text(data['playlist']);
      successToast('');
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#copy_playlist').on('click tap', function() {
    const temp = $('<textarea>');
    $('body').append(temp);
    temp.val($('#playlist').text()).select();
    document.execCommand('copy');
    temp.remove();
  });
  registerPostOnClick('save_as_playlist', () => {
    return {
      startdate: $('#startdate').val(),
      starttime: $('#starttime').val(),
      enddate: $('#enddate').val(),
      endtime: $('#endtime').val(),
      name: $('#saved_playlist_name').val(),
    };
  });

  registerPostOnClick('reboot_server');
  registerPostOnClick('reboot_system');
  registerPostOnClick('shutdown_system');

  $('#get_latest_version').on('click tap', function() {
    $.get(urls['settings']['get_latest_version']).done(function(response) {
      $('#latest_version').text(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#update_information_policy').on('change', function() {
    if ((<HTMLInputElement> this).value == 'yes') {
      localStorageRemove('ignore_updates');
    } else {
      localStorageSet('ignore_updates', '', 365);
    }
  });
  $('#open_changelog').on('click tap', function() {
    $.get(urls['settings']['get_changelog']).done(function(response) {
      $('#changelog').html(snarkdown(response));
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    $('#changelog_modal').modal('show');
  });
  $('#changelog_ok').on('click tap', function() {
    $('#changelog_modal').modal('hide');
  });
  $('#open_upgrade_dialog').on('click tap', function() {
    $.get(urls['settings']['get_upgrade_config']).done(function(response) {
      $('#upgrade_config').text(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    $('#upgrade_modal').modal('show');
  });
  $('#confirm_upgrade').on('click tap', function() {
    $('#upgrade_modal').modal('hide');
    post(urls['settings']['upgrade_raveberry']);
  });

  const fragment = window.location.hash.substr(1);
  if (fragment == 'show_changelog') {
    $('#update-banner').remove();
    $.get(urls['settings']['get_changelog']).done(function(response) {
      $('#changelog').html(snarkdown(response));
      $.each(response.split('\n'), (_, line) => {
        const tokens = line.split(/\s+/);
        if (tokens[0] == '##') {
          const version = tokens[1];
          $('#latest_version').text(version);
          return false;
        }
      });
    });
    const scrollDuration = 1000;
    $('html, body').animate({scrollTop: $('#about').offset().top},
        scrollDuration);
    setTimeout(function() {
      $('#changelog_modal').modal('show');
    }, scrollDuration);
  }
}

$(document).ready(onReady);
