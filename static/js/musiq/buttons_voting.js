$(document).ready(function() {
	// Use a token bucket implementation to allow 10 Votes per minute.
    let maxTokens = 10;
    let currentTokens = maxTokens;
	let bucketLifetime = 30000; // half a minute
	let currentBucket = $.now();
	function can_vote() {
		let now = $.now();
		let timePassed = now - currentBucket;
		if (timePassed > bucketLifetime) {
			currentBucket = now;
			currentTokens = maxTokens - 1;
			return true;
		}

		if (currentTokens > 0) {
			currentTokens --;
			return true;
		}

		let ratio = (bucketLifetime - timePassed) / bucketLifetime;
		warningToastWithBar("You're doing that too often");
		$('#vote_timeout_bar').css('transition', 'none');
		$('#vote_timeout_bar').css('width', ratio * 100 + '%');
		$('#vote_timeout_bar')[0].offsetHeight;
		$('#vote_timeout_bar').css({
			'transition': 'width ' + ratio * bucketLifetime / 1000 + 's linear',
			'width': '0%',
		});
		return false;
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
