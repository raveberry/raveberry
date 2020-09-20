let state = null;
let toastTimeout = 2000;
let currentToastId = 0;
function infoToast(firstLine, secondLine) {
	$('#info-toast').find('.toast-content').text(firstLine);
	if (secondLine != null) {
		$('#info-toast').find('.toast-content').append($('<br/>'));
		$('#info-toast').find('.toast-content').append(secondLine);
	}
	$('#success-toast').fadeOut();
	$('#warning-toast').fadeOut();
	$('#error-toast').fadeOut();
	$('#info-toast').fadeIn();
	currentToastId ++;
	let showedToastId = currentToastId;
	setTimeout( function(){
		if (showedToastId == currentToastId)
			$('#info-toast').fadeOut();
	}, toastTimeout);
}
function successToast(firstLine, secondLine) {
	$('#success-toast').find('.toast-content').text(firstLine);
	if (secondLine != null) {
		$('#success-toast').find('.toast-content').append($('<br/>'));
		$('#success-toast').find('.toast-content').append(secondLine);
	}
	$('#info-toast').fadeOut();
	$('#warning-toast').fadeOut();
	$('#error-toast').fadeOut();
	$('#success-toast').fadeIn();
	currentToastId ++;
	let showedToastId = currentToastId;
	setTimeout( function(){
		if (showedToastId == currentToastId)
			$('#success-toast').fadeOut();
	}, toastTimeout);
}
function warningToast(firstLine, secondLine, showBar) {
	if (!showBar) {
		$('#vote_timeout_bar').hide();
	}
	$('#warning-toast').find('.toast-content').text(firstLine);
	if (secondLine != null) {
		$('#warning-toast').find('.toast-content').append($('<br/>'));
		$('#warning-toast').find('.toast-content').append(secondLine);
	}
	$('#info-toast').fadeOut();
	$('#success-toast').fadeOut();
	$('#error-toast').fadeOut();
	$('#warning-toast').fadeIn();
	currentToastId ++;
	let showedToastId = currentToastId;
	setTimeout( function(){
		if (showedToastId == currentToastId)
			$('#warning-toast').fadeOut();
	}, toastTimeout);
}
function warningToastWithBar(firstLine, secondLine) {
	warningToast(firstLine, secondLine, true);
}
function errorToast(firstLine, secondLine) {
	$('#error-toast').find('.toast-content').text(firstLine);
	if (secondLine != null) {
		$('#error-toast').find('.toast-content').append($('<br/>'));
		$('#error-toast').find('.toast-content').append(secondLine);
	}
	$('#info-toast').fadeOut();
	$('#success-toast').fadeOut();
	$('#warning-toast').fadeOut();
	$('#error-toast').fadeIn();
	currentToastId ++;
	let showedToastId = currentToastId;
	setTimeout( function(){
		if (showedToastId == currentToastId)
			$('#error-toast').fadeOut();
	}, toastTimeout);
}
function updateBaseState(newState) {
	$('#users').text(newState.users);
	$('#visitors').text(newState.visitors);
	if (newState.lights_enabled) {
		$('#lights_indicator').addClass('icon_enabled');
		$('#lights_indicator').removeClass('icon_disabled');
	} else {
		$('#lights_indicator').removeClass('icon_enabled');
		$('#lights_indicator').addClass('icon_disabled');
	}
	if (newState.partymode) {
		$('#favicon').attr('href', urls['party_icon']);
		$('#navbar_icon').attr('src', urls['party_icon']);
		$('#navbar_icon').css('visibility', 'visible');
		if (newState.alarm) {
			$('body').addClass('alarm')
			$('#progress_bar').addClass('alarm')
		} else {
			$('body').removeClass('alarm')
			$('#progress_bar').removeClass('alarm')
		}
	} else {
		$('#favicon').attr('href', urls['dark_icon']);
		if ($('#light_theme').hasClass('icon_enabled')) {
			$('#navbar_icon').attr('src', urls['normal_light_icon']);
		} else {
			$('#navbar_icon').attr('src', urls['normal_icon']);
		}
		$('#navbar_icon').css('visibility', 'visible');
	}

	if (Cookies.get('platform') === undefined) {
		Cookies.set('platform', newState.default_platform, { expires: 1 });
	}

	updatePlatformClasses();
}

// this default behaviors can be overwritten by individual pages
let specificState;

function updateState(newState) {
	updateBaseState(newState);

	if (specificState !== undefined) {
		specificState(newState);
	}
}

function getState() {
	$.get(urls['state'], function(state) {
		updateState(state);
	});
}
function reconnect() {
	getState();
}

function decideScrolling(span, seconds_per_pixel, static_seconds) {
	let space_available = span.parent().width();
	let space_needed = span.width();
	if (space_available < space_needed) {
		// an overflow is happening, start scrolling
		
		let space_overflowed = space_needed - space_available;
		let ratio = space_overflowed / space_needed;

		let moving_seconds = space_overflowed * seconds_per_pixel;
		let duration = (static_seconds + moving_seconds) * 2;

		let animation_name = 'marquee_' + span.attr('id') + '_'  + $.now();
		let keyframes = {};
		keyframes['name'] = animation_name;
		keyframes['0%'] = {transform: 'translate(0, 0)'};
		keyframes[static_seconds / duration * 100 + '%'] 
			= {transform: 'translate(0, 0)'};
		keyframes[(static_seconds + moving_seconds) / duration * 100 + '%'] 
			= {transform: 'translate(-' + ratio*100 + '%, 0)'};
		keyframes[(static_seconds * 2 + moving_seconds) / duration * 100 + '%'] 
			= {transform: 'translate(-' + ratio*100 + '%, 0)'};
		keyframes[(static_seconds * 2 + moving_seconds * 2) / duration * 100 + '%']
			= {transform: 'translate(0, 0)'};
		$.keyframe.define([keyframes]);

		span.css('animation-name', animation_name);
		span.css('animation-duration', duration + 's');
		span.css('animation-timing-function', 'linear');
		span.css('animation-iteration-count', 'infinite');

		span.addClass('autoscrolling');
	} else {
		span.removeClass('autoscrolling');
	}
}

function updatePlatformClasses() {
	$('#local').removeClass('icon_enabled');
	$('#youtube').removeClass('icon_enabled');
	$('#spotify').removeClass('icon_enabled');
	$('#soundcloud').removeClass('icon_enabled');
	$('#local').addClass('icon_disabled');
	$('#youtube').addClass('icon_disabled');
	$('#spotify').addClass('icon_disabled');
	$('#soundcloud').addClass('icon_disabled');
	if (Cookies.get('platform') == 'local') {
		$('#local').removeClass('icon_disabled');
		$('#local').addClass('icon_enabled');
	} else if (Cookies.get('platform') == 'youtube') {
		$('#youtube').removeClass('icon_disabled');
		$('#youtube').addClass('icon_enabled');
	} else if (Cookies.get('platform') == 'spotify') {
		$('#spotify').removeClass('icon_disabled');
		$('#spotify').addClass('icon_enabled');
	} else if (Cookies.get('platform') == 'soundcloud') {
		$('#soundcloud').removeClass('icon_disabled');
		$('#soundcloud').addClass('icon_enabled');
	}
}

// dark/light mode
function toggle_theme() {
	let old_style_link = $('#active-stylesheet').attr('href');
	let new_style_link = $('#inactive-stylesheet').attr('href');
	if ($('#light_theme').hasClass('icon_enabled')) {
		$('#light_theme').removeClass('icon_enabled');
		$('#light_theme').addClass('icon_disabled');
		$('#dark_theme').removeClass('icon_disabled');
		$('#dark_theme').addClass('icon_enabled');
		if (state != null && !state.partymode) {
			$('#navbar_icon').attr('src', urls['normal_icon']);
		}
		$('#shareberry_icon').attr('src', urls['shareberry_dark_icon']);
	} else {
		$('#light_theme').removeClass('icon_disabled');
		$('#light_theme').addClass('icon_enabled');
		$('#dark_theme').removeClass('icon_enabled');
		$('#dark_theme').addClass('icon_disabled');
		if (state != null && !state.partymode) {
			$('#navbar_icon').attr('src', urls['normal_light_icon']);
		}
		$('#shareberry_icon').attr('src', urls['shareberry_light_icon']);
	}
	$('#active-stylesheet').attr('href', new_style_link);
	$('#inactive-stylesheet').attr('href', old_style_link);
}

function setToastHeight() {
	$('#toast-container').css('height', window.innerHeight);
}

// add the ripple effect to clickable buttons
function ripple() {
	// Remove any old one
	$(".ripple").remove();

	let buttonWidth = $(this).width(),
		buttonHeight =  $(this).height();
	let x = null,
		y = null;
	if ($(this).parent().hasClass('anim-container')) {
		x = parseInt($(this).css('margin-left')) + parseInt($(this).css('padding-left'));
		y = parseInt($(this).css('margin-top')) + parseInt($(this).css('padding-top'));
		// compensate one-sided margin hack
		x += (parseInt($(this).parent().css('margin-right')) - parseInt($(this).parent().css('margin-left'))) / 3;

		// Add the element to the parent element, since it does not move
		$(this).parent().prepend("<span class='ripple'></span>");
	} else {
		// Setup
		let posX = $(this).offset().left,
			posY = $(this).offset().top;
		// Get the center of the $(this)
		x = $(this).position().left + parseInt($(this).css('margin-left')) + parseInt($(this).css('padding-left'));
		y = $(this).position().top + parseInt($(this).css('margin-top')) + parseInt($(this).css('padding-top'));

		// Add the element
		$(this).prepend("<span class='ripple'></span>");
	}

	// Make it round!
	buttonWidth = buttonHeight = Math.max(buttonWidth, buttonHeight);

	// Add the ripples CSS and start the animation
	$(".ripple").css({
		width: buttonWidth,
		height: buttonHeight,
		top: y + 'px',
		left: x + 'px'
	}).addClass("rippleEffect");
}

// hashtag scrolling with too long tags
function decideHashtagScrolling() {
	decideScrolling($('#hashtag_text'), 0.030, 2);
}

$(document).ready(function() {
	// add the csrf token to every post request
	$.ajaxPrefilter(function(options, originalOptions, jqXHR){
		if (options.type.toLowerCase() === "post") {
			// initialize `data` to empty string if it does not exist
			options.data = options.data || "";
			// add leading ampersand if `data` is non-empty
			options.data += options.data?"&":"";
			// add _token entry
			options.data += "csrfmiddlewaretoken=" + encodeURIComponent(CSRF_TOKEN);
		}
	});

	// initialize toasts
	$('.toast').toast({
		delay: 3000,
	});

	$(window).on('resize', setToastHeight);
	setToastHeight();

	$(document).on('click tap', '.fas', ripple);
	$(document).on('click tap', '.fab', ripple);

	// Hashtag transition animation
	let text = $('#hashtag_text_container');
	let input = $('#hashtag_input');

	// toggles the view between the hashtags text and the input form
	let hashtag_toggler = function() {
		if (input.css('max-width') == '0%') {
			// if the input is invisible, initiate the texts removal transition
			text.removeClass('shown');
			text.addClass('hidden');
		} else {
			// if the text is invisible, the input is visible. remove it
			input.removeClass('shown');
			input.addClass('hidden');
		}
	};

	text.on('click', hashtag_toggler);
	// bind input enter

	text.bind('transitionend', function() {
		// if the text finished its removal transition initiate the inputs appearance
		if (text.css('max-width') == '0%') {
			input.css('visibility','visible');
			input.removeClass('hidden');
			input.addClass('shown');
		}
	});
	input.bind('transitionend', function() {
		// if the input finished its removal transition initiate the texts appearance
		if (input.css('max-width') == '0%') {
			input.css('visibility','hidden');
			text.removeClass('hidden');
			text.addClass('shown');
		} else {
			// if it is now visible, give it focus
			input.focus();
		}
	});
	$(window).on('resize', decideHashtagScrolling);
	decideHashtagScrolling();

	// submit hashtags
	let submit_hashtag = function() {
		$.post(urls['submit_hashtag'],
			{
				hashtag: $('#hashtag_input').val(),
			});
		$('#hashtag_input').val('');
		hashtag_toggler();
	}
	$('#hashtag_plus').on('click tap', function (e) {
		if (text.css('max-width') == '0%') {
			submit_hashtag();
		} else {
			hashtag_toggler();
		}
	});
	$('#hashtag_input').on('keypress', function (e) {
		if(e.which === 13){
			submit_hashtag();
		}
	});

	// enable/disable lights
	$('#lights_indicator').on('click tap', function() {
		$.post(urls['set_lights_shortcut'], {
			value: !$(this).hasClass('icon_enabled'),
		});
	});


	if ($('#active-stylesheet').attr('href').endsWith('dark.css')) {
		$('#light_theme').addClass('icon_disabled');
		$('#dark_theme').addClass('icon_enabled');
		if (Cookies.get('theme') == 'light') {
			toggle_theme();
		}
	} else {
		$('#light_theme').addClass('icon_enabled');
		$('#dark_theme').addClass('icon_disabled');
		$('#navbar_icon').attr('src', urls['normal_light_icon']);
		if (Cookies.get('theme') == 'dark') {
			toggle_theme();
		}
	}

	$('#light_theme').on('click tap', function() {
		if ($(this).hasClass('icon_enabled'))
			return
		toggle_theme();
		Cookies.set('theme', 'light', { expires: 7 });
	});
	$('#dark_theme').on('click tap', function() {
		if ($(this).hasClass('icon_enabled'))
			return
		toggle_theme();
		Cookies.set('theme', 'dark', { expires: 7 });
	});

	$('#local').on('click tap', function() {
		if ($(this).hasClass('icon_enabled'))
			return
		Cookies.set('platform', 'local', { expires: 1 });
		updatePlatformClasses();
	});
	$('#youtube').on('click tap', function() {
		if ($(this).hasClass('icon_enabled'))
			return
		Cookies.set('platform', 'youtube', { expires: 1 });
		updatePlatformClasses();
	});
	$('#spotify').on('click tap', function() {
		if ($(this).hasClass('icon_enabled'))
			return
		Cookies.set('platform', 'spotify', { expires: 1 });
		updatePlatformClasses();
	});
	$('#soundcloud').on('click tap', function() {
		if ($(this).hasClass('icon_enabled'))
			return
		Cookies.set('platform', 'soundcloud', { expires: 1 });
		updatePlatformClasses();
	});

	// request initial state update
	getState();

	$('#goto_update').on('click tap', function() {
		location.href = '/settings/#show_changelog';
		if (location.pathname.endsWith('/settings/')) {
			location.reload();
		}
	})
	$('#remind_updates').on('click tap', function() {
		let tomorrow = new Date(new Date().getTime() + 24 * 60 * 60 * 1000);
		Cookies.set('ignore_updates', '', {expires: tomorrow});
		$('#update-banner').slideUp('fast');
	})
	$('#ignore_updates').on('click tap', function() {
		Cookies.set('ignore_updates', '', {expires: 365});
		$('#update-banner').slideUp('fast');
	})
	if (ADMIN) {
		if (Cookies.get("ignore_updates") === undefined) {
			$.get(urls['upgrade_available']).done(function(response) {
				if (response) {
					$('#update-banner').slideDown('fast');
				}
			})
		}
	}
});
