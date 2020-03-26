specificState = function (newState) {
	updateBaseState(newState);
	if (!('pad_version' in newState)) {
		// this state is not meant for a pad update
		return;
	}
	if (newState['pad_version'] != PAD_VERSION) {
		setDiverged();
	}
}

function setSynced() {
	if ($('#pad_status_icon').hasClass('fa-exclamation-circle')) {
		// do not overwrite the 'Diverged' state
		return;
	}
	$('#pad_status_icon').removeClass();
	$('#pad_status_icon').addClass('fas');
	$('#pad_status_icon').addClass('fa-check-circle');
	$('#pad_status_text').text('Synced');
}
function setChanged() {
	if ($('#pad_status_icon').hasClass('fa-exclamation-circle')) {
		// do not overwrite the 'Diverged' state
		return;
	}
	$('#pad_status_icon').removeClass();
	$('#pad_status_icon').addClass('fas');
	$('#pad_status_icon').addClass('fa-exclamation-triangle');
	$('#pad_status_text').text('Changed');
}
function setDiverged() {
	$('#pad_status_icon').removeClass();
	$('#pad_status_icon').addClass('fas');
	$('#pad_status_icon').addClass('fa-exclamation-circle');
	$('#pad_status_text').text('Diverged! Please reload.');
}

$(document).ready(function() {
	function setPadHeight() {
		let top_position = $('#pad').offset().top;
		let bottom_space = $('#pad').parent().next().outerHeight();
		$('#pad').css('height', window.innerHeight - top_position - bottom_space - 30);
	}
	$(window).on('resize', setPadHeight);
	setPadHeight();
	$('#pad').bind('input propertychange', function() {
		setChanged();
	});

	$('#submit_pad').on('click tap', function() {
		PAD_VERSION ++;
		$.post(urls['submit_pad'], {
			version: PAD_VERSION - 1,
			content: $('#pad').val(),
		}).done(function(response) {
			successToast(response);
			setSynced();
		}).fail(function(response) {
			PAD_VERSION --;
			errorToast(response.responseText);
		});
	});
});
