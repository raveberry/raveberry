import {state} from "./update";
import {keyOfElement} from "./buttons";
import * as jqueryProxy from 'jquery'
const $: JQueryStatic = (<any>jqueryProxy).default || jqueryProxy

export function onReady() {
	// enable drag and drop for the song queue
	$("#current_song").disableSelection();
	$("#song_queue").disableSelection();

	if (VOTING_SYSTEM)
		return;

	$("#song_queue").sortable({ 
		handle: '.queue_handle',
		stop: function(e, ui) {
			let key = keyOfElement(ui.item);
			let prev = ui.item.prev();
			let prevKey = null;
			if (prev.length)
				prevKey = keyOfElement(prev);
			let next = ui.item.next();
			let nextKey = null;
			if (next.length)
				nextKey = keyOfElement(next);

			// change our state so the animation does not trigger
			let newIndex = ui.item.index();
			let oldIndex = parseInt(ui.item.find('.queue_index').text()) - 1;
			let queueEntry = state.song_queue.splice(oldIndex, 1);
			state.song_queue.splice(newIndex, 0, queueEntry[0]);

			$.post(urls['reorder'], {
				prev: prevKey,
				element: key,
				next: nextKey,
			});
		},
	});
}

$(document).ready(() => {
	if (!window.location.pathname.endsWith('musiq/')) {
		return;
	}
	onReady();
});
