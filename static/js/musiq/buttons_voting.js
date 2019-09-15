$(document).ready(function() {
	let voting_timeout = 5000;
	let last_vote = $.now() - voting_timeout;
	function can_vote() {
		let now = $.now();
		let time_passed = now - last_vote;
		if (time_passed < voting_timeout) {
			let ratio = (voting_timeout - time_passed) / voting_timeout;
			warningToastWithBar("You're doing that too often");
			$('#vote_timeout_bar').css('transition', 'none');
			$('#vote_timeout_bar').css('width', ratio * 100 + '%');
			$('#vote_timeout_bar')[0].offsetHeight;
			$('#vote_timeout_bar').css({
				'transition': 'width ' + ratio * voting_timeout / 1000 + 's linear',
				'width': '0%',
			});
			return false;
		}
		last_vote = $.now();
		return true;
	}
	function vote_down(button, key) {
		votes = button.closest('.queue_entry').find('.queue_index');
		if (votes.length == 0) {
			votes = button.siblings('#current_song_votes');
		}
		votes.text(parseInt(votes.text()) - 1);
		return $.post(urls['vote_down'], {
			key: key,
		});
	}
	function vote_up(button, key) {
		votes = button.closest('.queue_entry').find('.queue_index');
		if (votes.length == 0) {
			votes = button.siblings('#current_song_votes');
		}
		votes.text(parseInt(votes.text()) + 1);
		return $.post(urls['vote_up'], {
			key: key,
		});
	}
	$('#content').on('click tap', '.vote_up', function() {
		if (!can_vote())
			return;
		let key = -1;
		if ($(this).closest('#current_song_card').length > 0) {
			if (state == null || state.current_song == null)
				return;
			key = state.current_song.queue_key;
		} else {
			key = keyOfElement($(this));
		}
		let other = $(this).siblings('.vote_down');
		if ($(this).hasClass('pressed')) {
			$(this).removeClass('pressed');
			Cookies.set('vote_' + key, '0', { expires: 7 });
			vote_down($(this), key);
		} else {
			$(this).addClass('pressed');
			if (other.hasClass('pressed')) {
				other.removeClass('pressed');
				vote_up($(this), key);
			}
			Cookies.set('vote_' + key, '+', { expires: 7 });
			vote_up($(this), key);
		}
	});
	$('#content').on('click tap', '.vote_down', function() {
		if (!can_vote())
			return;
		let key = -1;
		if ($(this).closest('#current_song_card').length > 0) {
			if (state == null || state.current_song == null)
				return;
			key = state.current_song.queue_key;
		} else {
			key = keyOfElement($(this));
		}
		let other = $(this).siblings('.vote_up');
		if ($(this).hasClass('pressed')) {
			$(this).removeClass('pressed');
			Cookies.set('vote_' + key, '0', { expires: 7 });
			vote_up($(this), key);
		} else {
			$(this).addClass('pressed');
			if (other.hasClass('pressed')) {
				other.removeClass('pressed');
				vote_down($(this), key);
			}
			Cookies.set('vote_' + key, '-', { expires: 7 });
			vote_down($(this), key);
		}
	});
});
