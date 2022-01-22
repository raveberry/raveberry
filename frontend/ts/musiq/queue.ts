import {state} from './update';
import {keyOfElement} from './buttons';
import 'jquery-ui/ui/widgets/sortable';
import 'jquery-ui-touch-punch';

/** Allows reordering of the queue when not voting. */
export function onReady() {
  // enable drag and drop for the song queue
  if (VOTING_ENABLED) {
    return;
  }

  $('#song-queue').sortable({
    handle: '.queue-handle',
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
      const oldIndex = parseInt(ui.item.find('.queue-index').text()) - 1;
      if (newIndex == oldIndex) {
        return;
      }

      // remove the entry from its old position
      const queueEntry = state.songQueue.splice(oldIndex, 1);
      // and insert it in the new position
      state.songQueue.splice(newIndex, 0, queueEntry[0]);
      // update the indices of all items
      $('#song-queue>li .queue-index').each(function(index, el) {
        $(el).text(index+1);
      });

      $.post(urls['musiq']['reorder'], {
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
