import ReconnectingWebSocket from 'reconnecting-websocket';
import {updateState, reconnect} from './base.js';

let socketUrl = window.location.host + '/state/';
if (window.location.protocol == 'https:') {
  socketUrl = 'wss://' + socketUrl;
} else {
  socketUrl = 'ws://' + socketUrl;
}
const stateSocket = new ReconnectingWebSocket(socketUrl, [], {});
let unloading = false;

stateSocket.addEventListener('message', (e) => {
  const newState = JSON.parse(e.data);
  updateState(newState);
});

let firstConnect = true;
stateSocket.addEventListener('open', (e) => {
  if (!firstConnect) {
    reconnect();
    $('#disconnected-banner').slideUp('fast');
    $('#reconnected-banner').slideDown('fast', function() {
      setInterval(function() {
        $('#reconnected-banner').slideUp('fast');
      }, 2000);
    });
  }
  firstConnect = false;
});

stateSocket.addEventListener('close', (e) => {
  if (unloading)
    return;
  $('#disconnected-banner').slideDown('fast');
});

addEventListener("beforeunload", () => {
  unloading = true;
}, {capture: true});
