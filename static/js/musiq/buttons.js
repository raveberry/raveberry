function keyOfElement(element) {
	// takes a jquery element and returns the index of it in the song queue
	index = element.closest('.queue_entry').parent().index();
	// if the element is currently being reordered, look into its index span for the index 
	if (index == -1) {
		el = element.find('.queue_index');
		if (index.length == 0)
			el = element.closest('.queue_entry').find('.queue_index');
		index = el.text() - 1;
	}
	return state.song_queue[index].id;
}
function playlistEnabled() {
	return $('#playlist_mode').hasClass('icon_enabled');
}

function disablePlaylistMode() {
	$('#playlist_mode').removeClass('icon_enabled');
	$('#playlist_mode').addClass('icon_disabled');
	$('#request_radio').removeClass('icon_enabled');
	$('#request_radio').addClass('icon_disabled');
	$('#remove_all').removeClass('icon_enabled');
	$('#remove_all').addClass('icon_disabled');
}
function showPlayButton() {
	$("#play").before($("#pause"));
	setTimeout(function(){
		$('#play_button_container').removeClass('morphed');
	}, 50);
}
function showPauseButton() {
	$("#pause").before($("#play"));
	setTimeout(function(){
		$('#play_button_container').addClass('morphed');
	}, 50);
}
function request_archived_music(key, query, platform=Cookies.get('platform')) {
	$.post(urls['request_music'],
		{
			key: key,
			query: query,
			playlist: playlistEnabled(),
			platform: platform,
		}).done(function(response) {
			successToast(response.message, '"' + query + '"');
			Cookies.set('vote_' + response.key, '+', { expires: 7 });
		}).fail(function(response) {
			errorToast(response.responseText, '"' + query + '"');
		});
		infoToast('searching...', '"' + query + '"');
	$('#music_input').val('').trigger('change');
	disablePlaylistMode();
}

function request_new_music(query, platform=Cookies.get('platform')) {
	$.post(urls['request_music'],
		{
			query: query,
			playlist: playlistEnabled(),
			platform: platform,
		}).done(function(response) {
			successToast(response.message, '"' + query + '"');
			Cookies.set('vote_' + response.key, '+', { expires: 7 });
		}).fail(function(response) {
			errorToast(response.responseText, '"' + query + '"');
		});
		infoToast('searching...', '"' + query + '"');
	$('#music_input').val('').trigger('change');
	disablePlaylistMode();
}

$(document).ready(function() {
	$('#playlist_mode').on('click tap', function (e) {
		if ($(this).hasClass('icon_disabled')) {
			$(this).removeClass('icon_disabled');
			$(this).addClass('icon_enabled');
			$('#request_radio').removeClass('icon_disabled');
			$('#request_radio').addClass('icon_enabled');
			$('#remove_all').removeClass('icon_disabled');
			$('#remove_all').addClass('icon_enabled');
			warningToast('Use this power wisely');
		} else {
			disablePlaylistMode();
		}
	});
	// the key of the song that was suggested via random suggest
	let randomKey = null;
	$('#random_suggestion').on('click tap', function() {
		$.get(urls['random_suggestion'], { playlist: playlistEnabled() }, function(response) {
			$('#music_input').val(response.suggestion).trigger('change');
			randomKey = response.key;
			// change the search icon into the go icon to indicate the absence of search
			$("#request_archived_music").before($("#request_new_music"));
			// wait until the change was applied, then initiate the animation
			setTimeout(function(){
				$('#request_button_container').addClass('morphed');
			}, 50);
		}).fail(function(response) {
			errorToast(response.responseText);
		});
	});
	function showSearchIcon() {
		// change back to the search icon when the user focuses the input field
		$("#request_new_music").before($("#request_archived_music"));
		// wait until the change was applied, then initiate the animation
		setTimeout(function(){
			$('#request_button_container').removeClass('morphed');
		}, 50);
	}
	$('#request_new_music').on('click tap', function() {
		request_new_music($('#music_input').val());
	});
	$('#request_archived_music').on('click tap', function() {
		request_archived_music(randomKey, $('#music_input').val());
		showSearchIcon();
	});
	$('#music_input').focus(function() {
		showSearchIcon();
	});
	$('#clearbutton').on('click tap', function() {
		$(this).prev('input').val('').trigger('change').focus();
	});
	$("#music_input").on('change input copy paste cut', function() {
		let icon = $(this).next('i');
		if (!this.value) {
			icon.css('opacity', '0');
		} else {
			icon.css('opacity', '1');
		}
	});
	$('#music_input').on('keydown', function (e) {
		if(e.which === 13){
			if (randomKey == null)
				request_new_music($('#music_input').val());
			else
				request_archived_music(randomKey, $('#music_input').val());
		} else {
			// another key was pressed -> the input changed, clear the stored key from random suggestion
			randomKey = null;
		}
	});

	$('#volume_slider').change(function() {
		$.post(urls['set_volume'], {
			value: $(this).val(),
		});
	});
	$('#remove_all').on('click tap', function() {
		if (!playlistEnabled()) {
			warningToast('Please enable playlists to use this');
			return;
		}
		$.post(urls['remove_all']).done(function(response) {
			successToast(response);
		}).fail(function(response) {
			errorToast(response.responseText);
		});
		disablePlaylistMode();
	});

	// info popups for songs with long text
	$('#song_queue').on('click tap', '.queue_title', function() {
		index = $(this).closest('.queue_entry').parent().index();
		let url = state.song_queue[index].external_url;

		let new_modal_text = $(this).contents().clone();
		if (new_modal_text.length > 1) {
			// cut the character that connects artist and title
			new_modal_text.get(1).data = new_modal_text.get(1).data.substring(3);
		}
		new_modal_text.append('<br/>');
		$('#title_modal .modal-text').html(new_modal_text);
		$('#external_link').attr('href', url);
		$('#title_modal').modal('show');
	});
	// close modals on click
	$('#title_modal .modal-content').on('click tap', function() {
		$('#title_modal').modal('hide');
	});
});
