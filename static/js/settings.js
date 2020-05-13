specificState = function (newState) {
	updateBaseState(newState);
	if (!('voting_system' in newState)) {
		// this state is not meant for a settings update
		return;
	}

	$('#voting_system').prop("checked", newState.voting_system);
	$('#logging_enabled').prop("checked", newState.logging_enabled);
	$('#people_to_party').val(newState.people_to_party);
	$('#alarm_probability').val(newState.alarm_probability);
	$('#downvotes_to_kick').val(newState.downvotes_to_kick);
	$('#max_download_size').val(newState.max_download_size);
	$('#max_playlist_items').val(newState.max_playlist_items);
	$('#has_internet').prop("checked", newState.has_internet);

	$('#youtube_enabled').prop("checked", newState.youtube_enabled);

	$('#spotify_credentials_valid').prop("checked", newState.spotify_credentials_valid);

	$('#bluetooth_scanning').prop("checked", newState.bluetooth_scanning);
	$.each(newState.bluetooth_devices, function(index, device) {
		if (device.address == $('.bluetooth_device').eq(index).children().last().attr('id'))
			return true;
		let li = $('<li/>')
			.addClass('list-group-item')
			.addClass('list_item')
			.addClass('bluetooth_device');
		let label = $('<label/>')
			.attr('for', 'bluetooth_device_' + index)
			.text(device.name)
			.appendTo(li);
		let input = $('<input/>')
			.attr('type', 'radio')
			.attr('name', 'bluetooth_device')
			.attr('id', device.address)
			.appendTo(li);
		li.insertBefore($('#connect_bluetooth').parent());
	});

	$('#homewifi_enabled').text(newState.homewifi_enabled);
	$('#homewifi_ssid').val(newState.homewifi_ssid);

	$('#scan_progress').text(newState.scan_progress);

	$('#streaming_enabled').text(newState.streaming_enabled);
	$('#events_enabled').text(newState.events_enabled);
	$('#hotspot_enabled').text(newState.hotspot_enabled);
	$('#wifi_protected').text(newState.wifi_protected);
	$('#tunneling_enabled').text(newState.tunneling_enabled);
	$('#remote_enabled').text(newState.remote_enabled);

	if(!newState.hotspot_available){
		$('.hotspot-function').addClass('is-disabled');
	}
}

$(document).ready(function() {
	$('#voting_system').change(function() {
		$.post(urls['set_voting_system'], {
			value: $(this).is(":checked"),
		}).done(function() {
			successToast('');
		});
	});
	$('#logging_enabled').change(function() {
		$.post(urls['set_logging_enabled'], {
			value: $(this).is(":checked"),
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
		});
	});
	$('#max_playlist_items').change(function() {
		$.post(urls['set_max_playlist_items'], {
			value: $(this).val(),
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
			value: $(this).is(":checked"),
		}).done(function() {
			successToast('');
		});
	});

	$('#check_spotify_credentials').on('click tap', function() {
		$.get(urls['check_spotify_credentials']).done(function(response) {
			successToast(response);
		}).fail(function(response) {
			errorToast(response.responseText);
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

	$('#bluetooth_scanning').on('click tap', function() {
		let checked = $(this).is(":checked");
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

	$('#wifi_ssid').focus(function () {
		$.get(urls['available_ssids']).done(function(ssids) {
			let available_ssids = ssids;
			$('#wifi_ssid').autocomplete({
				source: available_ssids,
				minLength: 0,
			});
			$('#wifi_ssid').autocomplete("search");
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
	$('#homewifi_ssid').focus(function () {
		$.get(urls['stored_ssids']).done(function(ssids) {
			let stored_ssids = ssids;
			$('#homewifi_ssid').autocomplete({
				source: stored_ssids,
				minLength: 0,
			});
			$('#homewifi_ssid').autocomplete("search");
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
				let done_entry = {
					'value': 'done',
				};
				subdirectories.unshift(done_entry);
				response(subdirectories);
			});
		},
		select: function(event, ui) {
			if (ui.item.value == 'done') {
				keepSubdirsOpen = false;
				return false;
			}
		},
		close: function () {
			if (keepSubdirsOpen) {
				$('.ui-autocomplete').show();
				$('#library_path').autocomplete("search");
			}
		}
	});
	$('#library_path').on('click tap', function () {
		keepSubdirsOpen = true;
		$('#library_path').autocomplete("search");
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

	let today = new Date();
	let yesterday = new Date();
	yesterday.setDate(today.getDate() - 1);
	$('#startdate').val($.datepicker.formatDate('yy-mm-dd', yesterday));
	$('#starttime').val('12:00');
	$('#enddate').val($.datepicker.formatDate('yy-mm-dd', today));
	$('#endtime').val(today.toLocaleTimeString('en-GB', {hour: 'numeric', minute: 'numeric'}));
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
			successToast();
		}).fail(function(response) {
			errorToast(response.responseText);
		});
	});
	$('#copy_playlist').on('click tap', function() {
		let temp = $("<textarea>");
		$("body").append(temp);
		temp.val($('#playlist').text()).select();
		document.execCommand("copy");
		temp.remove();
	});

	$('#disable_streaming').on('click tap', function() {
		$.post(urls['disable_streaming']).done(function() {
			successToast('');
		}).fail(function(response) {
			errorToast(response.responseText);
		});
	});
	$('#enable_streaming').on('click tap', function() {
		$.post(urls['enable_streaming']).done(function() {
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
});
