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
      let firstResponse = true;
      let offlineSuggestions = [];
      let onlineSuggestions = [];
      const searchEntry = {
        'value': request.term,
        'type': 'search',
      };
      const suggestionCounts = {
        'youtube': YOUTUBE_SUGGESTIONS,
        'spotify': SPOTIFY_SUGGESTIONS,
        'soundcloud': SOUNDCLOUD_SUGGESTIONS,
        'jamendo': JAMENDO_SUGGESTIONS,
      };
      let totalSuggestionCount = 0;
      const placeholders = [];
      for (const platform in suggestionCounts) {
        totalSuggestionCount += suggestionCounts[platform];
        for (let i = 0; i < suggestionCounts[platform]; i++) {
          placeholders.push({
            'value': '...',
            'type': platform + '-placeholder',
          });
        }
      }
      response([searchEntry].concat(placeholders));

      // autocomplete does not apply results from previous queries,
      // so we do not need to check whether to call response
      // depending on which request finishes first
      $.get(urls['musiq']['offline-suggestions'], {
        'term': request.term,
        'playlist': playlistEnabled(),
      }).done(function(suggestions) {
        if (firstResponse) {
          firstResponse = false;
          offlineSuggestions = suggestions;
          suggestions = placeholders.concat(suggestions);
          suggestions.unshift(searchEntry);
          response(suggestions);
        } else {
          suggestions = onlineSuggestions.concat(suggestions);
          // don't prepend the searchEntry,
          // it was already added to the onlineSuggestions
          response(suggestions);
        }
      });
      $.get(urls['musiq']['online-suggestions'], {
        'term': request.term,
        'playlist': playlistEnabled(),
      }).done(function(suggestions) {
        // Ensure that the suggestion contains as many entries
        // as there were placeholders.
        // This prevents content changes before user input.
        while (suggestions.length < totalSuggestionCount) {
          suggestions.push({
            'value': '...',
            'type': 'error',
          });
        }
        if (firstResponse) {
          firstResponse = false;
          suggestions.unshift(searchEntry);
          onlineSuggestions = suggestions;
          response(suggestions);
        } else {
          suggestions = suggestions.concat(offlineSuggestions);
          suggestions.unshift(searchEntry);
          response(suggestions);
        }
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
      if (elem.hasClass('.suggestion-inserter') ||
          elem.parents('.suggestion-inserter').length > 0) {
        // the insert button was clicked,
        // insert the text (default behavior)
        return true;
      }

      // the text was clicked, push the song and clear the input box
      if (ui.item.type == 'search') {
        requestNewMusic(ui.item.label);
      } else if (ui.item.type == 'search' || ui.item.type == 'error') {
        // do nothing
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

    if (item.type == 'error') {
      const suggestionDiv = $('<div>')
          .append('<i class="fas fa-exclamation-circle suggestion-type"></i>')
          .append($('<em>').text('error'));
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

    let suggestionDiv;
    if (item.type.endsWith('placeholder')) {
      const placeholder = $('<span>')
          .addClass('placeholder')
          .css('width', (30 + Math.random() * 50) + '%')
          .css('animation-delay', (Math.random() * -10 - 60) + 's');
      suggestionDiv = $('<div>')
          .css('width', '100%')
          .append(icon)
          .append(placeholder);
    } else {
      suggestionDiv = $('<div>')
          .text(item.label)
          .prepend(icon);
    }

    let infoText = '';
    // add duration where the name is not identifying
    if (item.confusable && item.hasOwnProperty('durationFormatted')) {
      infoText += '[' + item.durationFormatted + '] ';
    }
    if (item.hasOwnProperty('counter')) {
      infoText += '(' + item.counter + ')';
    }

    const infoDiv = $('<div>')
        .addClass('autocomplete-info')
        .text(infoText);
    if (item.type.endsWith('online')) {
      infoDiv.addClass('suggestion-inserter');
      const insertIcon = $('<i>')
          .addClass('fas')
          .addClass('fa-reply')
          .addClass('insert-icon');
      infoDiv.append(insertIcon);
    }

    // For some reason, placeholder entries are assigned the ui-menu-divider
    // class instead of the ui-menu-item class.
    // It is unclear to me why, but since this leads to them being unclickable,
    // the behavior is exactly what we want.

    // modify the suggestions to contain an icon
    return $('<li class="ui-menu-item-with-icon"></li>')
        .data('item.autocomplete', item)
        .append(suggestionDiv)
        .append(infoDiv)
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
