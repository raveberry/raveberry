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
function request_archived_song(key, query) {
	$.post(urls['request_archived_song'],
		{
			key: key,
			query: query,
		}).done(function(response) {
			successToast(response, '"' + query + '"');
		}).fail(function(response) {
			errorToast(response.responseText, '"' + query + '"');
		});
		infoToast('searching...', '"' + query + '"');
	$('#song_input').val('').trigger('change');
}
function request_new_song(query) {
	$.post(urls['request_new_song'],
		{
			query: $('#song_input').val(),
		}).done(function(response) {
			successToast(response, '"' + query + '"');
		}).fail(function(response) {
			errorToast(response.responseText, '"' + query + '"');
		});
		infoToast('searching...', '"' + query + '"');
	$('#song_input').val('').trigger('change');
};
$(document).ready(function() {
	// the key of the song that was suggested via random suggest
	let randomKey = null;
	$('#random_suggestion').on('click tap', function() {
		$.get(urls['random_suggestion'], function(response) {
			$('#song_input').val(response.suggestion).trigger('change');
			randomKey = response.key;
			// change the search icon into the go icon to indicate the absence of search
			$("#request_archived_song").before($("#request_new_song"));
			// wait until the change was applied, then initiate the animation
			setTimeout(function(){
				$('#request_button_container').addClass('morphed');
			}, 50);
		});
	});
	function showSearchIcon() {
		// change back to the search icon when the user focuses the input field
		$("#request_new_song").before($("#request_archived_song"));
		// wait until the change was applied, then initiate the animation
		setTimeout(function(){
			$('#request_button_container').removeClass('morphed');
		}, 50);
	}
	$('#request_new_song').on('click tap', function() {
		request_new_song($('#song_input').val());
	});
	$('#request_archived_song').on('click tap', function() {
		request_archived_song(randomKey, $('#song_input').val());
		showSearchIcon();
	});
	$('#song_input').focus(function() {
		showSearchIcon();
	});
	$('#clearbutton').on('click tap', function() {
		$(this).prev('input').val('').trigger('change').focus();
	});
	$("#song_input").on('change input copy paste cut', function() {
		let icon = $(this).next('i');
		if (!this.value) {
			icon.css('opacity', '0');
		} else {
			icon.css('opacity', '1');
		}
	});
	$('#song_input').on('keydown', function (e) {
		if(e.which === 13){
			if (randomKey == null)
				request_new_song($('#song_input').val());
			else
				request_archived_song(randomKey, $('#song_input').val());
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

	// info popups for songs with long text
	$('#song_queue').on('click tap', '.queue_title', function() {
		index = $(this).closest('.queue_entry').parent().index();
		let url = state.song_queue[index].url;

		let new_modal_text = $(this).contents().clone();
		if (new_modal_text.length > 1) {
			// cut the character that connects artist and title
			new_modal_text.get(1).data = new_modal_text.get(1).data.substring(3);
		}
		new_modal_text.append('<br/>');
		$('#title_modal .modal-text').html(new_modal_text);
		$('#youtube_link').attr('href', url);
		$('#title_modal').modal('show');
	});
	// close modals on click
	$('#title_modal .modal-content').on('click tap', function() {
		$('#title_modal').modal('hide');
	});
});
