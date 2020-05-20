$(document).ready(function() {
	// enable drag and drop for the song queue
	$("#current_song").disableSelection();
	$("#song_queue").disableSelection();

	if (VOTING_SYSTEM && !CONTROLS_ENABLED)
		return;

	$("#song_queue").sortable({ 
		handle: '.queue_handle',
		stop: function(e, ui) {
			key = keyOfElement(ui.item);
			let prev = ui.item.prev();
			let prevKey = null;
			if (prev.length)
				prevKey = keyOfElement(prev);
			let next = ui.item.next();
			let nextKey = null;
			if (next.length)
				nextKey = keyOfElement(next);

			// change our state so the animation does not trigger
			newIndex = ui.item.index();
			oldIndex = parseInt(ui.item.find('.queue_index').text()) - 1;
			let queueEntry = state.song_queue.splice(oldIndex, 1);
			state.song_queue.splice(newIndex, 0, queueEntry[0]);

			$.post(urls['reorder'], {
				prev: prevKey,
				element: key,
				next: nextKey,
			});
		},
	});
});
