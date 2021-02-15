import * as autocomplete from '@src/musiq/autocomplete';
import * as buttons from '@src/musiq/buttons';
import * as update from '@src/musiq/update';
import * as util from './util';

beforeAll(() => {
	util.render_template('musiq.html');
});

beforeEach(() => {
	util.prepareDocument();
	global['ADDITIONAL_KEYWORDS'] = "";
	global['FORBIDDEN_KEYWORDS'] = "";
	update.clearState();
});

afterEach(() => {
	util.clearCookies();
});

test('autocomplete list', () => {
	autocomplete.onReady();

	const get = jest.fn().mockImplementation(() => {
		let suggestions = [
			{"type": 'local'},
			{"type": 'youtube'},
			{"type": 'youtube'},
			{"type": 'spotify'}
		]
		return $.Deferred().resolve(suggestions);
	});
	$.get = get;

	$('#music_input').val('test');
	$('#music_input').autocomplete('search');
	let suggestions = $('.ui-autocomplete li');

	function iconClassesOf(element) {
		return $(element).find('i')[0].className;
	}
	expect(suggestions.length).toBe(5);
	expect(iconClassesOf(suggestions[0])).not.toEqual(iconClassesOf(suggestions[1]));
	expect(iconClassesOf(suggestions[1])).not.toEqual(iconClassesOf(suggestions[2]));
	expect(iconClassesOf(suggestions[2])).toEqual(iconClassesOf(suggestions[3]));
	expect(iconClassesOf(suggestions[3])).not.toEqual(iconClassesOf(suggestions[4]));
});

test('key retrieval of songs', () => {
	let ids = [14, 52, 59, 46, 73];
	update.updateState({
		'current_song': {'queue_key': ids[0]},
		'song_queue': [
			{'id': ids[1]},
			{'id': ids[2]},
			{'id': ids[3]},
			{'id': ids[4]},
		]
	});
	expect(update.state.current_song.queue_key).toEqual(ids[0]);
	$('.queue_info_time').each((index, element) => {
		expect(buttons.keyOfElement($(element))).toEqual(ids[index+1]);
	});
});

test('request random archived song', done => {
	buttons.onReady();

	const get = jest.fn().mockImplementation(() => {
		let suggestion = {
			"suggestion": "random_suggestion",
			"key": 54,
		}
		return $.Deferred().resolve(suggestion);
	});
	$.get = get;

	$('#random_suggestion').click();
	expect($('#music_input')[0]).toHaveValue('random_suggestion');
	setTimeout(() => {
		expect($('#request_archived_music')[0]).toBeVisible();
		expect($('#request_new_music')[0]).not.toBeVisible();

		const post = jest.fn().mockImplementation((url, data) => {
			expect(data).toMatchObject({
				"query": "random_suggestion",
				"key": 54
			});
			done();
			return $.Deferred();
		});
		$.post = post;
		$('#request_archived_music').click();

	}, 60);
});

test('request new song', done => {
	buttons.onReady();

	$('#music_input').val('test');
	expect($('#request_archived_music')[0]).not.toBeVisible();
	expect($('#request_new_music')[0]).toBeVisible();

	const post = jest.fn().mockImplementation((url, data) => {
		expect(data).toMatchObject({
			"query": "test",
		});
		expect(data).not.toHaveProperty('key');
		done();
		return $.Deferred();
	});
	$.post = post;

	$('#request_new_music').click();
});

test('additional song info', done => {
	buttons.onReady();

	update.updateState({
		'current_song': {
			'title': 'test_title',
			'external_url': 'test_url',
		},
	});

	$('#current_song_title').click();

	setTimeout(() => {
		expect($('#title_modal')[0]).toBeVisible();
		expect($('#title_modal')[0]).toHaveTextContent('test_title');
		done()
	}, 50);
});

test('queue updates', () => {
	function getState(songKeys) {
		return {
			'current_song': {},
			'song_queue': [
				{'id': songKeys[0]},
				{'id': songKeys[1]},
				{'id': songKeys[2]},
				{'id': songKeys[3]},
			]
		}
	}
	function getSongKeys() {
		return Array.from($('.queue_info_time').map((i, e) => buttons.keyOfElement($(e))));
	}

	let songKeys = [1,2,3,4];
	update.updateState(getState(songKeys));
	expect(getSongKeys()).toEqual(songKeys);

	songKeys = [2,3,1,4];
	update.updateState(getState(songKeys));
	expect(getSongKeys()).toEqual(songKeys);

	songKeys = [2,1,3,4];
	update.updateState(getState(songKeys));
	expect(getSongKeys()).toEqual(songKeys);
});

