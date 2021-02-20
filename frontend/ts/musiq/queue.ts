import {state} from './update';
import {keyOfElement} from './buttons';

/** Allows reordering of the queue when not voting. */
export function onReady() {
  // enable drag and drop for the song queue
  if (VOTING_SYSTEM) {
    return;
  }

  $('#song_queue').sortable({
    handle: '.queue_handle',
    stop: function(e, ui) {
      const key = keyOfElement(ui.item);
      const prev = ui.item.prev();
      let prevKey = null;
      if (prev.length) {
        prevKey = keyOfElement(prev);
      }
      const next = ui.item.next();
      let nextKey = null;
      if (next.length) {
        nextKey = keyOfElement(next);
      }

      // change our state so the animation does not trigger
      const newIndex = ui.item.index();
      const oldIndex = parseInt(ui.item.find('.queue_index').text()) - 1;
      const queueEntry = state.song_queue.splice(oldIndex, 1);
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
