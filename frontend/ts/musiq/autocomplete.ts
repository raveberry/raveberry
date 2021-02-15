import {request_new_music, request_archived_music, playlistEnabled} from "./buttons";
import * as jqueryProxy from 'jquery'
const $: JQueryStatic = (<any>jqueryProxy).default || jqueryProxy
import * as Cookies from 'js-cookie'
import 'jquery-ui-dist/jquery-ui';

export function onReady() {
	$(".autocomplete").autocomplete({
		source: function(request, response) {
			$.get(urls['suggestions'], {
				'term': request.term,
				'playlist': playlistEnabled(),
			}).done(function(suggestions) {

				let search_entry = {
					'value': request.term,
					'type': 'search',
				};

				suggestions.unshift(search_entry);
				response(suggestions);
			})
		},
		appendTo: '#music_input_card',
		open: function() {
			// align the autocomplete box with the card instead of the input field
			$("#music_input_card > ul").css({left: '0px'});

		},
		select: function(event, ui) {
			let origEvent = event;
			while (origEvent.originalEvent !== undefined){
				// @ts-ignore https://stackoverflow.com/a/7317068
				origEvent = origEvent.originalEvent;
			}

			let elem = $(origEvent.target);
			if (elem.hasClass('autocomplete_info') || elem.parents('.autocomplete_info').length > 0) {
				// the info or insert button was clicked, insert the text (default behavior)
				return true;
			}

			// the text was clicked, push the song and clear the input box
			if (ui.item.type == 'search') {
				request_new_music(ui.item.label);
			} else if (ui.item.type == 'youtube-online') {
				request_new_music(ui.item.label, 'youtube');
			} else if (ui.item.type == 'spotify-online') {
				request_new_music(ui.item.key, 'spotify');
			} else if (ui.item.type == 'soundcloud-online') {
				request_new_music(ui.item.label, 'soundcloud');
			} else {
				request_archived_music(ui.item.key, ui.item.label);
			}
			return false;
		},
		focus: function (event, ui) {
			return false;
		}
	})
		.data("ui-autocomplete")._renderItem = function (ul, item) {
			if (item.type == 'search') {
				let term = $('<span>').text(item.label);
				let additional_keywords = $('<span>')
					.addClass('additional_keywords')
					.text(ADDITIONAL_KEYWORDS);
				let forbidden_keywords = $('<span>')
					.addClass('forbidden_keywords')
					.text(FORBIDDEN_KEYWORDS.split(/[\s,]+/).join(" "));
				let suggestion_div = $('<div>')
					.append('<i class="fas fa-search suggestion_type"></i>')
					.append(term)
					.append(additional_keywords);
				if (Cookies.get('platform') == 'spotify' || Cookies.get('platform') == 'soundcloud') {
					suggestion_div.append(forbidden_keywords);
				}
				return $('<li class="ui-menu-item-with-icon"></li>')
					.data("item.autocomplete", item)
					.append(suggestion_div)
					.appendTo(ul);
			}

			let icon = $('<i>')
				.addClass('suggestion_type')
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
			}

			let counter = '(' + item.counter + ')';
			if (item.type.endsWith('online')) {
				counter = '';
			}

			let suggestion_div = $('<div>')
				.text(item.label)
				.prepend(icon);

			// modify the suggestions to contain an icon
			return $('<li class="ui-menu-item-with-icon"></li>')
				.data("item.autocomplete", item)
				.append(suggestion_div)
				.append('<div class="autocomplete_info">' + counter + '<i class="fas fa-reply insert_icon"></i>')
				.appendTo(ul);
		};

	// set the autocomplete box's width to that of the card
	jQuery.ui.autocomplete.prototype._resizeMenu = function () {
		let ul = this.menu.element;
		ul.outerWidth(this.element.outerWidth());
		ul.outerWidth($('#current_song_card').outerWidth());
		ul.css('left', $('#current_song_card').position()['left']);
	}
}

$(document).ready(() => {
	if (!window.location.pathname.endsWith('musiq/')) {
		return;
	}
	onReady();
});
