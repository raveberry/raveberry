import {
  requestNewMusic,
  requestArchivedMusic,
  playlistEnabled,
} from './buttons';
import 'jquery-ui/ui/version';
import 'jquery-ui/ui/widget';
import 'jquery-ui/ui/position';
import 'jquery-ui/ui/keycode';
import 'jquery-ui/ui/unique-id';
import 'jquery-ui/ui/widgets/menu';
import 'jquery-ui/ui/widgets/autocomplete';

/** Add autocomplete handler. */
export function onReady() {
  $('.autocomplete').autocomplete({
    source: function(request, response) {
      $.get(urls['musiq']['get-suggestions'], {
        'term': request.term,
        'playlist': playlistEnabled(),
      }).done(function(suggestions) {
        const searchEntry = {
          'value': request.term,
          'type': 'search',
        };

        suggestions.unshift(searchEntry);
        response(suggestions);
      });
    },
    appendTo: '#music-input-card',
    open: function() {
      // align the autocomplete box with the card instead of the input field
      $('#music-input-card > ul').css({left: '0px'});
    },
    select: function(event, ui) {
      let origEvent = event;
      while (origEvent.originalEvent !== undefined) {
        // @ts-ignore https://stackoverflow.com/a/7317068
        origEvent = origEvent.originalEvent;
      }

      const elem = $(origEvent.target);
      if (elem.hasClass('autocomplete-info') ||
          elem.parents('.autocomplete-info').length > 0) {
        // the info or insert button was clicked,
        // insert the text (default behavior)
        return true;
      }

      // the text was clicked, push the song and clear the input box
      if (ui.item.type == 'search') {
        requestNewMusic(ui.item.label);
      } else if (ui.item.type == 'youtube-online') {
        requestNewMusic(ui.item.label, 'youtube');
      } else if (ui.item.type == 'spotify-online') {
        requestNewMusic(ui.item.key, 'spotify');
      } else if (ui.item.type == 'soundcloud-online') {
        requestNewMusic(ui.item.label, 'soundcloud');
      } else if (ui.item.type == 'jamendo-online') {
        requestNewMusic(ui.item.label, 'jamendo');
      } else {
        requestArchivedMusic(ui.item.key, ui.item.label);
      }
      return false;
    },
    focus: function(event, ui) {
      return false;
    },
  }).data('ui-autocomplete')._renderItem = function(ul, item) {
    if (item.type == 'search') {
      const term = $('<span>').text(item.label);
      const additionalKeywords = $('<span>')
          .addClass('additional-keywords')
          .text(ADDITIONAL_KEYWORDS);
      const forbiddenKeywords = $('<span>')
          .addClass('forbidden-keywords')
          .text(FORBIDDEN_KEYWORDS.split(/[\s,]+/).join(' '));
      const suggestionDiv = $('<div>')
          .append('<i class="fas fa-search suggestion-type"></i>')
          .append(term)
          .append(additionalKeywords);
      suggestionDiv.append(forbiddenKeywords);
      return $('<li class="ui-menu-item-with-icon"></li>')
          .data('item.autocomplete', item)
          .append(suggestionDiv)
          .appendTo(ul);
    }

    const icon = $('<i>')
        .addClass('suggestion-type')
        .addClass(item.type);
    if (item.type.startsWith('local')) {
      icon.addClass('fas')
          .addClass('fa-hdd');
    } else if (item.type.startsWith('youtube')) {
      icon.addClass('fab')
          .addClass('fa-youtube');
    } else if (item.type.startsWith('spotify')) {
      icon.addClass('fab')
          .addClass('fa-spotify');
    } else if (item.type.startsWith('soundcloud')) {
      icon.addClass('fab')
          .addClass('fa-soundcloud');
    } else if (item.type.startsWith('jamendo')) {
      icon.addClass('fas')
          .addClass('fa-jamendo');
    } else if (item.type.startsWith('playlog')) {
      icon.addClass('fas')
          .addClass('fa-wrench');
    }

    let counter = '(' + item.counter + ')';
    if (item.type.endsWith('online')) {
      counter = '';
    }

    const suggestionDiv = $('<div>')
        .text(item.label)
        .prepend(icon);

    // modify the suggestions to contain an icon
    return $('<li class="ui-menu-item-with-icon"></li>')
        .data('item.autocomplete', item)
        .append(suggestionDiv)
        .append('<div class="autocomplete-info">' + counter +
            '<i class="fas fa-reply insert-icon"></i>')
        .appendTo(ul);
  };

  // set the autocomplete box's width to that of the card
  jQuery.ui.autocomplete.prototype._resizeMenu = function() {
    const ul = this.menu.element;
    ul.outerWidth(this.element.outerWidth());
    ul.outerWidth($('#current-song-card').outerWidth());
    ul.css('left', $('#current-song-card').position()['left']);
  };
}

$(document).ready(() => {
  if (!window.location.pathname.endsWith('musiq/')) {
    return;
  }
  onReady();
});
