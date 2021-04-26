import * as buttons from '@src/musiq/buttons';
import * as update from '@src/musiq/update';
import * as util from './util';

beforeAll(() => {
  util.renderTemplate('musiq.html', {'is_admin': true});
});

beforeEach(() => {
  util.prepareDocument();
  update.clearState();
});

afterEach(() => {
  localStorage.clear();
});

test('remove all', () => {
  buttons.onReady();

  $('#remove-all').click();
  expect($('#warning-toast')[0]).toBeVisible();

  const post = jest.fn().mockReturnValue($.Deferred());
  $.post = post;
  $('#playlist-mode').click();
  $('#remove-all').click();
  expect(post).toHaveBeenCalledWith(urls['remove-all']);
});

