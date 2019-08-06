$(document).ready(function() {
	$('#restart_song').on('click tap', function (e) {
		$.post(urls['restart']);
	});
	$('#seek_backward').on('click tap', function (e) {
		$.post(urls['seek_backward']);
	});
	$('#play').on('click tap', function (e) {
		// don't allow play command without a song
		if (state == null || state.current_song == null) return;
		showPauseButton();
		$.post(urls['play']);
	});
	$('#pause').on('click tap', function (e) {
		showPlayButton();
		$.post(urls['pause']);
	});
	$('#seek_forward').on('click tap', function (e) {
		$.post(urls['seek_forward']);
	});
	$('#skip_song').on('click tap', function (e) {
		$.post(urls['skip']);
	});
	$('#set_shuffle').on('click tap', function (e) {
		// send True if it is currently disabled to enable it (and the other way round)
		$.post(urls['set_shuffle'],
			{
				value: $(this).hasClass('icon_disabled'),
			});
	});
	$('#set_repeat').on('click tap', function (e) {
		$.post(urls['set_repeat'],
			{
				value: $(this).hasClass('icon_disabled'),
			});
	});
	$('#set_autoplay').on('click tap', function (e) {
		$.post(urls['set_autoplay'],
			{
				value: $(this).hasClass('icon_disabled'),
			});
	});
	$('#song_queue').on('click tap', '.prioritize', function() {
		$.post(urls['prioritize'], {
			key: keyOfElement($(this)),
		});
	});
	$('#song_queue').on('click tap', '.remove', function() {
		$.post(urls['remove'], {
			key: keyOfElement($(this)),
		});
	});

});
