/** Register input handlers. */
export function onReady() {
  if (!window.location.pathname.endsWith('network_info/')) {
    return;
  }
  const passwordPlaintext = $('#password').text();
  if (passwordPlaintext != 'Unknown') {
    const passwordHidden = passwordPlaintext.replace(/./g, '•');
    $('#password').text(passwordHidden);
    $('#show_password').on('click tap', function() {
      $('#password').text(passwordPlaintext);
    });
  }
}

$(document).ready(onReady);
