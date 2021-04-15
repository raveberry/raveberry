import {
  registerSpecificState,
  successToast,
  errorToast,
} from './base.js';


/** Update the lights state.
 * @param {Object} state an object containing all state information */
function updateState(state) {
  if (!('lights' in state)) {
    // this state is not meant for a lights update
    return;
  }

  for (const key in state.lights) {
    if (!state.lights.hasOwnProperty(key)) {
      continue;
    }
    const value = state.lights[key];
    const element = $('#' + key );
    if (element.is(':checkbox')) {
      element.prop('checked', value);
    } else if (element.is('input')) {
      element.val(value);
    }
  }

  for (const leds of ['ring', 'wled', 'strip', 'screen']) {
    if (state.lights[leds + '_connected']) {
      $('#' + leds + '_options').removeClass('disabled');
      $('#' + leds + '_options .list_item').show();
    } else {
      $('#' + leds + '_options').addClass('disabled');
      $('#' + leds + '_options .list_item').hide();
    }
  }
}

/** Register input handlers. */
export function onReady() {
  if (!window.location.pathname.endsWith('lights/')) {
    return;
  }
  registerSpecificState(updateState);
  $('#ring_program').change(function() {
    const selected = $('#ring_program option:selected').val();
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
      value: $(this).is(':checked'),
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
    const selected = $('#wled_program option:selected').val();
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
      value: $(this).is(':checked'),
    });
  });


  $('#strip_program').change(function() {
    const selected = $('#strip_program option:selected').val();
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
    const selected = $('#screen_program option:selected').val();
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
}

$(document).ready(onReady);
