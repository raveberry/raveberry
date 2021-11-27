import * as autocomplete from '@src/musiq/autocomplete';
import * as buttons from '@src/musiq/buttons';
import * as update from '@src/musiq/update';
import * as util from './util';

beforeAll(() => {
  util.renderTemplate('musiq.html');
});

beforeEach(() => {
  util.prepareDocument();
  update.clearState();
});

afterEach(() => {
  localStorage.clear();
});

test('autocomplete list', () => {
  autocomplete.onReady();

  // this get is called twice, once for online and once for offline suggestions
  const get = jest.fn().mockImplementation(() => {
    const suggestions = [
      {'type': 'local'},
      {'type': 'youtube'},
      {'type': 'youtube'},
      {'type': 'spotify'},
    ];
    return $.Deferred().resolve(suggestions);
  });
  $.get = get;

  $('#music-input').val('test');
  $('#music-input').autocomplete('search');
  const suggestions = $('.ui-autocomplete li');

  function iconClassesOf(element) {
    return $(element).find('i')[0].className;
  }
  expect(suggestions.length).toBe(9);
  expect(iconClassesOf(suggestions[0])).not.toEqual(iconClassesOf(suggestions[1]));
  expect(iconClassesOf(suggestions[1])).not.toEqual(iconClassesOf(suggestions[2]));
  expect(iconClassesOf(suggestions[2])).toEqual(iconClassesOf(suggestions[3]));
  expect(iconClassesOf(suggestions[3])).not.toEqual(iconClassesOf(suggestions[4]));
  expect(iconClassesOf(suggestions[1])).toEqual(iconClassesOf(suggestions[5]));
  expect(iconClassesOf(suggestions[2])).toEqual(iconClassesOf(suggestions[6]));
  expect(iconClassesOf(suggestions[3])).toEqual(iconClassesOf(suggestions[7]));
  expect(iconClassesOf(suggestions[4])).toEqual(iconClassesOf(suggestions[8]));
});

test('key retrieval of songs', () => {
  const ids = [14, 52, 59, 46, 73];
  update.updateState({
    'musiq': {
      'currentSong': {'queueKey': ids[0]},
      'songQueue': [
        {'id': ids[1]},
        {'id': ids[2]},
        {'id': ids[3]},
        {'id': ids[4]},
      ],
    },
  });
  expect(update.state.currentSong.queueKey).toEqual(ids[0]);
  $('.queue-info-time').each((index, element) => {
    expect(buttons.keyOfElement($(element))).toEqual(ids[index+1]);
  });
});

test('request random archived song', (done) => {
  buttons.onReady();

  const get = jest.fn().mockImplementation(() => {
    const suggestion = {
      'suggestion': 'random suggestion',
      'key': 54,
    };
    return $.Deferred().resolve(suggestion);
  });
  $.get = get;

  $('#random-suggestion').click();
  expect($('#music-input')[0]).toHaveValue('random suggestion');
  setTimeout(() => {
    expect($('#request-archived-music')[0]).toBeVisible();
    expect($('#request-new-music')[0]).not.toBeVisible();

    const post = jest.fn().mockImplementation((url, data) => {
      expect(data).toMatchObject({
        'query': 'random suggestion',
        'key': 54,
      });
      done();
      return $.Deferred();
    });
    $.post = post;
    $('#request-archived-music').click();
  }, 60);
});

test('request new song', (done) => {
  buttons.onReady();

  $('#music-input').val('test');
  expect($('#request-archived-music')[0]).not.toBeVisible();
  expect($('#request-new-music')[0]).toBeVisible();

  const post = jest.fn().mockImplementation((url, data) => {
    expect(data).toMatchObject({
      'query': 'test',
    });
    expect(data).not.toHaveProperty('key');
    done();
    return $.Deferred();
  });
  $.post = post;

  $('#request-new-music').click();
});

test('additional song info', (done) => {
  buttons.onReady();

  update.updateState({
    'musiq': {
      'currentSong': {
        'title': 'test title',
        'externalUrl': 'testurl',
      },
    },
  });

  $('#current-song-title').click();

  setTimeout(() => {
    expect($('#title-modal')[0]).toBeVisible();
    expect($('#title-modal')[0]).toHaveTextContent('test title');
    done();
  }, 50);
});

test('queue updates', () => {
  function getState(songKeys) {
    return {
      'musiq': {
        'currentSong': {},
        'songQueue': [
          {'id': songKeys[0]},
          {'id': songKeys[1]},
          {'id': songKeys[2]},
          {'id': songKeys[3]},
        ],
      },
    };
  }
  function getSongKeys() {
    return Array.from($('.queue-info-time')
        .map((i, e) => buttons.keyOfElement($(e))));
  }

  let songKeys = [1, 2, 3, 4];
  update.updateState(getState(songKeys));
  expect(getSongKeys()).toEqual(songKeys);

  songKeys = [2, 3, 1, 4];
  update.updateState(getState(songKeys));
  expect(getSongKeys()).toEqual(songKeys);

  songKeys = [2, 1, 3, 4];
  update.updateState(getState(songKeys));
  expect(getSongKeys()).toEqual(songKeys);
});

