import {decideScrolling} from "../base";
import * as jqueryProxy from 'jquery'
const $: JQueryStatic = (<any>jqueryProxy).default || jqueryProxy

export function onReady() {
	// rotate the currently playing song if its title is too long
	function decideTitleScrolling() {
		decideScrolling($('#current_song_title'), 0.030, 2)
	}
	$('#current_song_title').on('change', decideTitleScrolling);
	$(window).on('resize', decideTitleScrolling);
}

$(document).ready(() => {
	if (!window.location.pathname.endsWith('musiq/')) {
		return;
	}
	onReady();
});
