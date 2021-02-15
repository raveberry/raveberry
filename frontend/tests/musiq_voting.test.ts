import * as buttons_voting from '@src/musiq/buttons_voting';
import * as update from '@src/musiq/update';
import * as util from './util';

beforeAll(() => {
	util.render_template('musiq.html', {'voting_system': true});
});

beforeEach(() => {
	util.prepareDocument();
	update.clearState();
});

afterEach(() => {
	util.clearCookies();
});

test.each(['.vote_up', '.vote_down'])
('voting frequency', (buttonClass) => {
	buttons_voting.onReady();

	for (let i = 0; i < 10; i++) {
		$('#current_song_card ' + buttonClass).click();
	}
	expect($('#warning-toast')[0]).not.toBeVisible();
	for (let i = 0; i < 100; i++) {
		$('#current_song_card ' + buttonClass).click();
	}
	expect($('#warning-toast')[0]).toBeVisible();
});

