$(document).ready(function() {
	$(function() {
		$(".autocomplete").autocomplete({
			source: function(request, response) {
				$.get(urls['suggestions'], {
					'term': request.term,
					'playlist': playlistEnabled(),
				}).done(function(data) {
					let suggestions = JSON.parse(data);

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
				let card_position = $("#music_input_card").position();
				let input_position = $("#music_input").position();

				$("#music_input_card > ul").css({left: '0px',
					top: (input_position.bottom - card_position.bottom) + "px" });

			},
			select: function(event, ui) {
				let origEvent = event;
				while (origEvent.originalEvent !== undefined){
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
				return $('<li class="ui-menu-item-with-icon"></li>')
					.data("item.autocomplete", item)
					.append('<div><i class="fas fa-search suggestion_type"></i>' + item.label + '</div>')
					.appendTo(ul);
				}

				let icon = '<i class="fas fa-'
				if (item.type == 'cached') {
					icon += 'database';
				} else if (item.type == 'online') {
					icon += 'cloud';
				}
				icon += ' suggestion_type"></i>';
				// modify the suggestions to contain an icon
				return $('<li class="ui-menu-item-with-icon"></li>')
					.data("item.autocomplete", item)
					.append('<div>' + icon + item.label + '</div><div class="autocomplete_info">(' + item.counter + ')<i class="fas fa-reply insert_icon"></i>')
					.appendTo(ul);
			};
	});

	// set the autocomplete box's width to that of the card
	jQuery.ui.autocomplete.prototype._resizeMenu = function () {
		let ul = this.menu.element;
		ul.outerWidth(this.element.outerWidth());
		ul.outerWidth($('#current_song_card').outerWidth());
		ul.css('left', $('#current_song_card').position()['left']);
	}
});
