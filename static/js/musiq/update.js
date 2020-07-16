let animationInProgress = false;

specificState = function (newState) {
	updateBaseState(newState);

	if (!('current_song' in newState)) {
		// this state is not meant for a musiq update
		return;
	}
	// create deep copy
	let oldState = null;
	if (state != null) {
		oldState = jQuery.extend(true, {}, state);
	}
	let currentSong = newState.current_song;
	if (currentSong == null) {
		state = newState;
		$('#current_song_title').empty();
		$('#current_song_title').append($('<em/>').text('Currently Empty'));
		$('#current_song_title').trigger('change');
		$('#current_song').removeClass('present');
		$('#current_song').addClass('empty');

		$('#song_votes .vote_down').removeClass('pressed');
		$('#song_votes .vote_up').removeClass('pressed');
		$('#current_song_votes').text(0);

		$('#progress_bar').css('transition', 'none');
		$('#progress_bar').css('width', '0%');
		// Trigger a reflow, flushing the CSS changes
		$('#progress_bar')[0].offsetHeight;

		showPlayButton();
	} else {
		state = newState;

		if (oldState == null || 
			oldState.current_song == null ||
			oldState.current_song.id != state.current_song.id) {
			insertDisplayName($('#current_song_title'), currentSong);
			$('#current_song_title').trigger('change');
		}

		let previous_vote = Cookies.get('vote_' + currentSong.queue_key);
		if (previous_vote == '+') {
			$('#song_votes .vote_up').addClass('pressed');
			$('#song_votes .vote_down').removeClass('pressed');
		} else if (previous_vote == '-') {
			$('#song_votes .vote_down').addClass('pressed');
			$('#song_votes .vote_up').removeClass('pressed');
		} else {
			$('#song_votes .vote_down').removeClass('pressed');
			$('#song_votes .vote_up').removeClass('pressed');
		}

		$('#current_song_votes').text(currentSong.votes);

		$('#progress_bar').css('transition', 'none');
		$('#progress_bar').css('width', state.progress + '%');
		// Trigger a reflow, flushing the CSS changes
		$('#progress_bar')[0].offsetHeight;

		if (state.paused) {
			showPlayButton();
		} else {
			showPauseButton();

			let duration = state.current_song.duration;

			let played = state.progress / 100 * duration;
			let left = duration - played;

			$('#progress_bar').css({
				'transition': 'width ' + left + 's linear',
				'width': '100%',
			});
		}
	}

	if (state.shuffle) {
		$('#set_shuffle').removeClass('icon_disabled');
		$('#set_shuffle').addClass('icon_enabled');
	} else {
		$('#set_shuffle').removeClass('icon_enabled');
		$('#set_shuffle').addClass('icon_disabled');
	}
	if (state.repeat) {
		$('#set_repeat').removeClass('icon_disabled');
		$('#set_repeat').addClass('icon_enabled');
	} else {
		$('#set_repeat').removeClass('icon_enabled');
		$('#set_repeat').addClass('icon_disabled');
	}
	if (state.autoplay) {
		$('#set_autoplay').removeClass('icon_disabled');
		$('#set_autoplay').addClass('icon_enabled');
	} else {
		$('#set_autoplay').removeClass('icon_enabled');
		$('#set_autoplay').addClass('icon_disabled');
	}

	$('#volume_slider').val(state.volume);
	if (state.volume == 0) {
		$('#volume_indicator').addClass('fa-volume-off');
		$('#volume_indicator').removeClass('fa-volume-down');
		$('#volume_indicator').removeClass('fa-volume-up');
	} else if (state.volume <= 0.5) {
		$('#volume_indicator').removeClass('fa-volume-off');
		$('#volume_indicator').addClass('fa-volume-down');
		$('#volume_indicator').removeClass('fa-volume-up');
	} else {
		$('#volume_indicator').removeClass('fa-volume-off');
		$('#volume_indicator').removeClass('fa-volume-down');
		$('#volume_indicator').addClass('fa-volume-up');
	}

	/*
		<li class="list-group-item">
			<div class="queue_entry">
				<div class="download_icon queue_handle">
					<div class="download_overlay"></div>
					<img src="/static/graphics/download.png">
				</div>
				<div class="queue_index queue_handle"><fa-sort>{{ forloop.counter }}</div>
				<div class="queue_title">{{ song.artist }} - {{ song.title }}</div>
				<div class="queue_info">
					<span class="queue_info_time">{{ song.duration_formatted }}</span>
					<span class="queue_info_controls">
						{% if voting_system %}
						<i class="fas fa-chevron-circle-up vote_up"></i>
						<i class="fas fa-chevron-circle-down vote_down"></i>
						{% else %}
						<i class="fas level-up-alt prioritize"></i>
						<i class="fas fa-trash-alt remove"></i>
						{% endif %}
					</span>
				</div>
			</div>
		</li>
		*/

	// don't start a new animation when an old one is still in progress
	// the running animation will end in the (then) current state
	applyQueueChange(oldState, state);
}

function insertDisplayName(element, song) {
	if (song.artist == null || song.artist == '') {
		element.text(song.title);
	} else {
		element.text(' – ' + song.title);
		element.prepend($('<strong/>').text(song.artist));
	}
}
function createQueueItem(song) {
	let li = $('<li/>')
		.addClass('list-group-item')
	let entry_div = $('<div/>')
		.addClass('queue_entry')
		.appendTo(li);
	let download_icon = $('<div/>')
		.addClass('download_icon')
		.addClass('queue_handle')
		.appendTo(entry_div);
	let download_overlay = $('<div/>')
		.addClass('download_overlay')
		.appendTo(download_icon);
	let download_img = $('<img/>')
		.attr('src', '/static/graphics/download.png')
		.appendTo(download_icon);
	let index = $('<div/>')
		.addClass('queue_index')
		.addClass('queue_handle')
	if (VOTING_SYSTEM) {
		index.text(song.votes)
	} else {
		index.text(song.index)
	}
	index.appendTo(entry_div);
	if (song.internal_url) {
		download_icon.hide();
	} else {
		index.hide();
	}
	let title = $('<div/>');
	insertDisplayName(title, song);
	title.addClass('queue_title')
		.appendTo(entry_div);
	let info = $('<div/>')
		.addClass('queue_info')
		.appendTo(entry_div);
	let time = $('<span/>')
		.addClass('queue_info_time')
		.text(song.duration_formatted)
		.appendTo(info);
	let controls = $('<span/>')
		.addClass('queue_info_controls')
		.appendTo(info);
	if (VOTING_SYSTEM) {
		let previous_vote = Cookies.get('vote_' + song.id);
		let up = $('<i/>')
			.addClass('fas')
			.addClass('fa-chevron-circle-up')
			.addClass('vote_up');
		if (previous_vote == '+') {
			up.addClass('pressed');
		}
		up.appendTo(controls);
		let down = $('<i/>')
			.addClass('fas')
			.addClass('fa-chevron-circle-down')
			.addClass('vote_down');
		if (previous_vote == '-') {
			down.addClass('pressed');
		}
		down.appendTo(controls);
	}
	if (!VOTING_SYSTEM || CONTROLS_ENABLED) {
		let up = $('<i/>')
			.addClass('fas')
			.addClass('fa-level-up-alt')
			.addClass('prioritize')
			.appendTo(controls);
		let down = $('<i/>')
			.addClass('fas')
			.addClass('fa-trash-alt')
			.addClass('remove')
			.appendTo(controls);
	}
	return li;
}
function rebuildSongQueue(newState) {
	animationInProgress = false;
	$('#song_queue').empty();
	$.each(newState.song_queue, function(index, song) {
		queueEntry = createQueueItem(song);
		queueEntry.appendTo($('#song_queue'));
	});
}

function applyQueueChange(oldState, newState) {
	if (animationInProgress) return;
	animationInProgress = true;

	if (oldState == null) {
		rebuildSongQueue(newState);
	} else {
		// find mapping from old to new indices
		newIndices = []
		let songCount = 0;
		$.each(oldState.song_queue, function(oldIndex, song) {
			newIndex = newState.song_queue.findIndex((other) => {
				return other.id == song.id
			});
			newIndices.push(newIndex);
		});

		// add new songs
		$.each(newState.song_queue, function(newIndex, song) {
			if (!newIndices.includes(newIndex)) {

				// song was not present in old indices -> new song
				queueEntry = createQueueItem(song);
				queueEntry.css('opacity', '0');

				queueEntry.appendTo($('#song_queue'));
			}
		});

		// initiate transition to their new positions
		let animationNeeded = false;
		let transitionDuration = 0.5;
		$('#song_queue>li').css('top', '0px');
		$('#song_queue>li').css('transition', 'top ' + transitionDuration + 's ease, '
			+ 'opacity ' + transitionDuration + 's ease');

		let liHeight = $('#song_queue>li').first().outerHeight();
		liHeight -= parseFloat($('#song_queue>li').first().css('border-bottom-width'))

		$('#song_queue>li').each(function(index, li) {
			if (newIndices[index] == -1) {
				// item was deleted
				animationNeeded = true;
				$(li).css('opacity', '0');
			} else {
				// skip items that don't move at all
				if (newIndices[index] == index) {
					return true;
				}
				// item was moved
				animationNeeded = true;
				let delta = (newIndices[index] - index) * liHeight;
				$(li).css('top', delta + 'px');

				// make new songs visible
				$(li).css('opacity', '1');
			}
		})

		// update queue after animations
		setTimeout(function () {
			$('#song_queue>li').css('transition', 'none');
			// update the queue to the now current state
			rebuildSongQueue(state);
		}, animationNeeded * transitionDuration * 1000);

	}
}
