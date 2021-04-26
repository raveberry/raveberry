import * as buttonsVoting from '@src/musiq/buttons-voting';
import * as update from '@src/musiq/update';
import * as util from './util';

beforeAll(() => {
  util.renderTemplate('musiq.html', {'voting-system': true});
});

beforeEach(() => {
  util.prepareDocument();
  update.clearState();
});

afterEach(() => {
  localStorage.clear();
});

test.each(['.vote-up', '.vote-down'])
('voting frequency', (buttonClass) => {
  buttonsVoting.onReady();

  for (let i = 0; i < 10; i++) {
    $('#current-song-card ' + buttonClass).click();
  }
  expect($('#warning-toast')[0]).not.toBeVisible();
  for (let i = 0; i < 100; i++) {
    $('#current-song-card ' + buttonClass).click();
  }
  expect($('#warning-toast')[0]).toBeVisible();
});

