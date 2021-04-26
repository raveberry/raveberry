import * as base from '@src/base';
import * as util from './util';

beforeAll(() => {
  util.renderTemplate('base.html', {
    'local_enabled': true,
    'youtube_enabled': true,
  });
});

beforeEach(() => {
  util.prepareDocument();
});

afterEach(() => {
  localStorage.clear();
});

test.each([
  [base.infoToast, 'info-toast'],
  [base.successToast, 'success-toast'],
  [base.warningToast, 'warning-toast'],
  [base.errorToast, 'error-toast'],
])('toasts become visible', (toastCallable, elementId) => {
  base.onReady();
  expect($('#' + elementId)[0]).not.toBeVisible();
  toastCallable('');
  expect($('#' + elementId)[0]).toBeVisible();
});

test('base state is updated', () => {
  const state = {
    'partymode': true,
    'users': 7,
    'visitors': 318,
    'lightsEnabled': true,
    'alarm': true,
    'defaultPlatform': 'youtube',
  };
  base.updateBaseState(state);
  expect($('#navbar-icon')[0]).toHaveClass('partymode');
  expect($('#users')[0]).toHaveTextContent('7');
  expect($('#visitors')[0]).toHaveTextContent('318');
  expect($('#lights-indicator')[0]).toHaveClass('icon-enabled');
  expect($('#lights-indicator')[0]).not.toHaveClass('icon-disabled');
  expect($('body')[0]).toHaveClass('alarm');
});

test('hashtag is submitted', () => {
  base.onReady();
  const post = jest.fn();
  $.post = post;
  $('#hashtag-plus').click();
  $('#hashtag-input').val('raveberry');
  $('#hashtag-plus').click();
  expect(post.mock.calls[0])
      .toEqual([urls['submit-hashtag'], {'hashtag': 'raveberry'}]);
});

test('platform are set in storage', () => {
  base.onReady();
  expect(base.localStorageGet('platform')).toBeNull();
  $('#local').click();
  expect(base.localStorageGet('platform')).toEqual('local');
  $('#youtube').click();
  expect(base.localStorageGet('platform')).toEqual('youtube');
});

test.each([
  [true, false, true, true],
  [true, true, true, false],
  [true, false, false, false],
  [false, false, true, false],
])('update notifications', (
    isAdmin,
    updatesIgnored,
    updateAvailable,
    bannerShouldBeShown) => {
  ADMIN = isAdmin;
  if (updatesIgnored) {
    base.localStorageSet('ignore-updates', '');
  }

  // create a promise that will be returned
  // the test will only complete after this promise resolved
  // this way, we can wait for the $.get function to finish
  let done;
  new Promise((resolve) => {
    done = resolve;
  });

  function check() {
    if (bannerShouldBeShown) {
      expect($('#update-banner')[0]).toBeVisible();
    } else {
      expect($('#update-banner')[0]).not.toBeVisible();
    }
    done();
  }

  const get = jest.fn().mockImplementation(() => {
    setTimeout(() => {
      check();
    }, 50);
    return $.Deferred().resolve(updateAvailable);
  });

  $.get = get;
  base.handleUpdateBanner();

  // get is called if the admin does not have the value in local storage.
  // in this case we check when the get returns
  // for all other cases, directly check here
  if (!isAdmin || updatesIgnored) {
    check();
  }
});
