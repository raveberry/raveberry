/** Register input handlers. */
export function onReady() {
  if (!window.location.pathname.endsWith('network-info/')) {
    return;
  }
  const passwordPlaintext = $('#password').text();
  if (passwordPlaintext != 'Unknown') {
    const passwordHidden = passwordPlaintext.replace(/./g, '•');
    $('#password').text(passwordHidden);
    $('#show-password').on('click tap', function() {
      $('#password').text(passwordPlaintext);
    });
  }
}

$(document).ready(onReady);
