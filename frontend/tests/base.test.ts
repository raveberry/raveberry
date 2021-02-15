import * as base from '@src/base';
import * as util from './util';
import * as Cookies from 'js-cookie';

beforeAll(() => {
	util.render_template('base.html', {"local_enabled": true, "youtube_enabled": true});
});

beforeEach(() => {
	util.prepareDocument();
});

afterEach(() => {
	util.clearCookies();
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
	let state = {
		"partymode": true,
		"users": 7,
		"visitors": 318,
		"lights_enabled": true,
		"alarm": true,
		"default_platform": "youtube",
	}
	base.updateBaseState(state);
	expect($('#favicon').attr('href')).toEqual(urls['party_icon']);
	expect($('#users')[0]).toHaveTextContent('7');
	expect($('#visitors')[0]).toHaveTextContent('318');
	expect($('#lights_indicator')[0]).toHaveClass('icon_enabled');
	expect($('#lights_indicator')[0]).not.toHaveClass('icon_disabled');
	expect($('body')[0]).toHaveClass('alarm');
});

test('hashtag is submitted', () => {
	base.onReady();
	const post = jest.fn();
	$.post = post;
	$('#hashtag_plus').click();
	$('#hashtag_input').val('raveberry');
	$('#hashtag_plus').click();
	expect(post.mock.calls[0]).toEqual([urls['submit_hashtag'], {'hashtag': 'raveberry'}]);
});

test('platform cookies are set', () => {
	base.onReady();
	expect(Cookies.get('platform')).toBeUndefined();
	$('#local').click();
	expect(Cookies.get('platform')).toEqual('local');
	$('#youtube').click();
	expect(Cookies.get('platform')).toEqual('youtube');
});

test.each([
	[true, false, true, true],
	[true, true, true, false],
	[true, false, false, false],
	[false, false, true, false],
])('update notifications', (isAdmin, updatesIgnored, updateAvailable, bannerShouldBeShown) => {
	ADMIN = isAdmin;
	if (updatesIgnored)
		Cookies.set('ignore_updates', '');

	// create a promise that will be returned
	// the test will only complete after this promise resolved
	// this way, we can wait for the $.get function to finish
	let done;
	let p = new Promise((resolve) => {
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
		setImmediate(() => {
			check();
		})
		return $.Deferred().resolve(updateAvailable);
	});

	$.get = get;
	base.handleUpdateBanner();

	// get is called if the admin does not have the cookie set.
	// in this case we return the promise, otherwise we return immediately
	if (isAdmin && !updatesIgnored) {
		return p;
	} else {
		check();
	}
});
