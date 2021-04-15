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
    // Almost all keys in the state dictionary have a corresponding html element.
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
  $('#voting_system').change(function() {
    $.post(urls['set_voting_system'], {
      value: $(this).is(':checked'),
    }).done(function() {
      successToast('');
    });
  });
  $('#new_music_only').change(function() {
    $.post(urls['set_new_music_only'], {
      value: $(this).is(':checked'),
    }).done(function() {
      successToast('');
    });
  });
  $('#logging_enabled').change(function() {
    $.post(urls['set_logging_enabled'], {
      value: $(this).is(':checked'),
    }).done(function() {
      successToast('');
    });
  });
  $('#online_suggestions').change(function() {
    $.post(urls['set_online_suggestions'], {
      value: $(this).is(':checked'),
    }).done(function() {
      successToast('');
    });
  });
  $('#number_of_suggestions').change(function() {
    $.post(urls['set_number_of_suggestions'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#people_to_party').change(function() {
    $.post(urls['set_people_to_party'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#alarm_probability').change(function() {
    $.post(urls['set_alarm_probability'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#downvotes_to_kick').change(function() {
    $.post(urls['set_downvotes_to_kick'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#max_download_size').change(function() {
    $.post(urls['set_max_download_size'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#max_playlist_items').change(function() {
    $.post(urls['set_max_playlist_items'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#additional_keywords').change(function() {
    $.post(urls['set_additional_keywords'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#forbidden_keywords').change(function() {
    $.post(urls['set_forbidden_keywords'], {
      value: $(this).val(),
    }).done(function() {
      successToast('');
    });
  });
  $('#check_internet').on('click tap', function() {
    $.get(urls['check_internet']).done(function() {
      successToast('');
    });
  });
  $('#update_user_count').on('click tap', function() {
    $.get(urls['update_user_count']).done(function() {
      successToast('');
    });
  });

  $('#youtube_enabled').change(function() {
    $.post(urls['set_youtube_enabled'], {
      value: $(this).is(':checked'),
    }).done(function(response) {
      successToast(response);
    });
  });
  $('#youtube_suggestions').change(function() {
    $.post(urls['set_youtube_suggestions'], {
      value: $(this).val(),
    }).done(function(response) {
      successToast(response);
    });
  });

  $('#spotify_enabled').on('click tap', function() {
    $.post(urls['set_spotify_enabled'], {
      value: $(this).is(':checked'),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#spotify_suggestions').change(function() {
    $.post(urls['set_spotify_suggestions'], {
      value: $(this).val(),
    }).done(function(response) {
      successToast(response);
    });
  });
  $('#set_spotify_credentials').on('click tap', function() {
    $.post(urls['set_spotify_credentials'], {
      username: $('#spotify_username').val(),
      password: $('#spotify_password').val(),
      client_id: $('#spotify_client_id').val(),
      client_secret: $('#spotify_client_secret').val(),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  $('#soundcloud_enabled').on('click tap', function() {
    $.post(urls['set_soundcloud_enabled'], {
      value: $(this).is(':checked'),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#soundcloud_suggestions').change(function() {
    $.post(urls['set_soundcloud_suggestions'], {
      value: $(this).val(),
    }).done(function(response) {
      successToast(response);
    });
  });
  $('#set_soundcloud_credentials').on('click tap', function() {
    $.post(urls['set_soundcloud_credentials'], {
      auth_token: $('#soundcloud_auth_token').val(),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  $('#set_backup_stream').on('click tap', function() {
    $.post(urls['set_backup_stream'], {
      stream: $('#backup_stream').val(),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  $('#bluetooth_scanning').on('click tap', function() {
    const checked = $(this).is(':checked');
    if (checked) {
      $('.bluetooth_device').remove();
    }
    $.post(urls['set_bluetooth_scanning'], {
      value: checked,
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    if (checked) {
      infoToast('Started Scanning');
    }
  });
  $('#connect_bluetooth').on('click tap', function() {
    $.post(urls['connect_bluetooth'], {
      address: $('input[name=bluetooth_device]:checked').attr('id'),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#disconnect_bluetooth').on('click tap', function() {
    $.post(urls['disconnect_bluetooth']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  $('#output').focus(function() {
    $.get(urls['list_outputs']).done(function(devices) {
      $('#output').autocomplete({
        // always show all possible output devices,
        // regardless of current input content
        source: function(request, response) {
          response(devices);
        },
        minLength: 0,
      });
      $('#output').autocomplete('search');
    });
  });
  $('#set_output').on('click tap', function() {
    const selected = $('#output').val();
    $.post(urls['set_output'], {
      output: selected,
    }, function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  $('#wifi_ssid').focus(function() {
    $.get(urls['available_ssids']).done(function(ssids) {
      const availableSsids = ssids;
      $('#wifi_ssid').autocomplete({
        source: availableSsids,
        minLength: 0,
      });
      $('#wifi_ssid').autocomplete('search');
    });
  });
  $('#connect_to_wifi').on('click tap', function() {
    $.post(urls['connect_to_wifi'], {
      ssid: $('#wifi_ssid').val(),
      password: $('#wifi_password').val(),
    }).done(function(response) {
      $('#wifi_ssid').val('');
      $('#wifi_password').val('');
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#disable_homewifi').on('click tap', function() {
    $.post(urls['disable_homewifi']).done(function() {
      successToast('');
    });
  });
  $('#enable_homewifi').on('click tap', function() {
    $.post(urls['enable_homewifi']).done(function() {
      successToast('');
    });
  });
  $('#homewifi_ssid').focus(function() {
    $.get(urls['stored_ssids']).done(function(ssids) {
      const storedSsids = ssids;
      $('#homewifi_ssid').autocomplete({
        source: storedSsids,
        minLength: 0,
      });
      $('#homewifi_ssid').autocomplete('search');
    });
  });
  $('#set_homewifi_ssid').on('click tap', function() {
    $.post(urls['set_homewifi_ssid'], {
      homewifi_ssid: $('#homewifi_ssid').val(),
    }).done(function(response) {
      successToast('');
    });
  });

  let keepSubdirsOpen = true;
  $('#library_path').autocomplete({
    source: function(request, response) {
      $.get(urls['list_subdirectories'], {
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
  $('#scan_library').on('click tap', function() {
    $.post(urls['scan_library'], {
      library_path: $('#library_path').val(),
    }).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });
  $('#create_playlists').on('click tap', function() {
    $.post(urls['create_playlists']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

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
    $.post(urls['analyse'], {
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
  $('#save_as_playlist').on('click tap', function() {
    $.post(urls['save_as_playlist'], {
      startdate: $('#startdate').val(),
      starttime: $('#starttime').val(),
      enddate: $('#enddate').val(),
      endtime: $('#endtime').val(),
      name: $('#saved_playlist_name').val(),
    }).done(function() {
      successToast('');
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  $('#disable_events').on('click tap', function() {
    $.post(urls['disable_events']).done(function() {
      successToast('');
    });
  });
  $('#enable_events').on('click tap', function() {
    $.post(urls['enable_events']).done(function() {
      successToast('');
    });
  });
  $('#disable_hotspot').on('click tap', function() {
    $.post(urls['disable_hotspot']).done(function() {
      successToast('');
    });
  });
  $('#enable_hotspot').on('click tap', function() {
    $.post(urls['enable_hotspot']).done(function() {
      successToast('');
    });
  });
  $('#unprotect_wifi').on('click tap', function() {
    $.post(urls['unprotect_wifi']).done(function() {
      successToast('');
    });
  });
  $('#protect_wifi').on('click tap', function() {
    $.post(urls['protect_wifi']).done(function() {
      successToast('');
    });
  });
  $('#disable_tunneling').on('click tap', function() {
    $.post(urls['disable_tunneling']).done(function() {
      successToast('');
    });
  });
  $('#enable_tunneling').on('click tap', function() {
    $.post(urls['enable_tunneling']).done(function() {
      successToast('');
    });
  });
  $('#disable_remote').on('click tap', function() {
    $.post(urls['disable_remote']).done(function() {
      successToast('');
    });
  });
  $('#enable_remote').on('click tap', function() {
    $.post(urls['enable_remote']).done(function() {
      successToast('');
    });
  });
  $('#reboot_server').on('click tap', function() {
    $.post(urls['reboot_server']).done(function() {
      successToast('');
    });
  });
  $('#reboot_system').on('click tap', function() {
    $.post(urls['reboot_system']).done(function() {
      successToast('');
    });
  });
  $('#shutdown_system').on('click tap', function() {
    $.post(urls['shutdown_system']).done(function() {
      successToast('');
    });
  });
  $('#get_latest_version').on('click tap', function() {
    $.get(urls['get_latest_version']).done(function(response) {
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
    $.get(urls['get_changelog']).done(function(response) {
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
    $.get(urls['get_upgrade_config']).done(function(response) {
      $('#upgrade_config').text(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
    $('#upgrade_modal').modal('show');
  });
  $('#confirm_upgrade').on('click tap', function() {
    $('#upgrade_modal').modal('hide');
    $.post(urls['upgrade_raveberry']).done(function(response) {
      successToast(response);
    }).fail(function(response) {
      errorToast(response.responseText);
    });
  });

  const fragment = window.location.hash.substr(1);
  if (fragment == 'show_changelog') {
    $('#update-banner').remove();
    $.get(urls['get_changelog']).done(function(response) {
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
