updateState = function (newState) {
	updateBaseState(newState);
	if (!('ring_connected' in newState)) {
		// this state is not meant for a lights update
		return;
	}

	if (newState.ring_connected) {
		$('#ring_options').removeClass('disabled');
		$('#ring_options .list_item').show();
	} else {
		$('#ring_options').addClass('disabled');
		$('#ring_options .list_item').hide();
	}
	if (newState.wled_connected) {
		$('#wled_options').removeClass('disabled');
		$('#wled_options .list_item').show();
	} else {
		$('#wled_options').addClass('disabled');
		$('#wled_options .list_item').hide();
	}
	if (newState.strip_connected) {
		$('#strip_options').removeClass('disabled');
		$('#strip_options .list_item').show();
	} else {
		$('#strip_options').addClass('disabled');
		$('#strip_options .list_item').hide();
	}
	if (newState.screen_connected) {
		$('#screen_options').removeClass('disabled');
		$('#screen_options .list_item').show();
	} else {
		$('#screen_options').addClass('disabled');
		$('#screen_options .list_item').hide();
	}


	$('#ring_program').val(newState.ring_program);
	$('#ring_brightness').val(newState.ring_brightness);
	$('#ring_monochrome').prop("checked", newState.ring_monochrome);
	$('#wled_led_count').val(newState.wled_led_count);
	$('#wled_ip').val(newState.wled_ip);
	$('#wled_port').val(newState.wled_port);
	$('#wled_program').val(newState.wled_program);
	$('#wled_brightness').val(newState.wled_brightness);
	$('#wled_monochrome').prop("checked", newState.wled_monochrome);
	$('#strip_program').val(newState.strip_program);
	$('#strip_brightness').val(newState.strip_brightness);
	$('#screen_program').val(newState.screen_program);
	$('#program_speed').val(newState.program_speed);
	$('#fixed_color').val(newState.fixed_color);
}

$(document).ready(function() {
	$('#ring_program').change(function() {
		let selected = $("#ring_program option:selected").val();
		$.post(urls['set_ring_program'], {
			program: selected,
		});
	});
	$('#ring_brightness').change(function() {
		$.post(urls['set_ring_brightness'], {
			value: $(this).val(),
		});
	});
	$('#ring_monochrome').change(function() {
		$.post(urls['set_ring_monochrome'], {
			value: $(this).is(":checked"),
		});
	});


	$('#wled_led_count').change(function() {
		$.post(urls['set_wled_led_count'], {
			value: $(this).val(),
		}).done(function() {
			successToast('');
		});
	});
	$('#wled_ip').change(function() {
		$.post(urls['set_wled_ip'], {
			value: $(this).val(),
		}).done(function() {
			successToast('');
		});
	});
	$('#wled_port').change(function() {
		$.post(urls['set_wled_port'], {
			value: $(this).val(),
		}).done(function() {
			successToast('');
		});
	});
	$('#wled_program').change(function() {
		let selected = $("#wled_program option:selected").val();
		$.post(urls['set_wled_program'], {
			program: selected,
		});
	});
	$('#wled_brightness').change(function() {
		$.post(urls['set_wled_brightness'], {
			value: $(this).val(),
		});
	});
	$('#wled_monochrome').change(function() {
		$.post(urls['set_wled_monochrome'], {
			value: $(this).is(":checked"),
		});
	});


	$('#strip_program').change(function() {
		let selected = $("#strip_program option:selected").val();
		$.post(urls['set_strip_program'], {
			program: selected,
		});
	});
	$('#strip_brightness').change(function() {
		$.post(urls['set_strip_brightness'], {
			value: $(this).val(),
		});
	});

	$('#adjust_screen').on('click tap', function() {
		$.get(urls['adjust_screen']).done(function() {
			successToast('');
		}).fail(function(response) {
			errorToast(response.responseText);
		});
	});
	$('#screen_program').change(function() {
		let selected = $("#screen_program option:selected").val();
		$.post(urls['set_screen_program'], {
			program: selected,
		});
	});

	$('#program_speed').change(function() {
		$.post(urls['set_program_speed'], {
			value: $(this).val(),
		});
	});
	$('#fixed_color').change(function() {
		$.post(urls['set_fixed_color'], {
			value: $(this).val(),
		});
	});
});
