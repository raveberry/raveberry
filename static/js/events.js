const options = {
    maxReconnectionDelay: 2000,
	minReconnectionDelay: 100 + Math.random() * 1000,
    connectionTimeout: 1000,
};

let socketUrl = window.location.host + '/state/';
if (window.location.protocol == 'https:') {
	socketUrl = 'wss://' + socketUrl;
} else {
	socketUrl = 'ws://' + socketUrl;
}
let stateSocket = new ReconnectingWebSocket(socketUrl, [], options);

stateSocket.addEventListener('message', (e) => {
	let newState = JSON.parse(e.data);
	updateState(newState);
});

let firstConnect = true;
stateSocket.addEventListener('open', (e) => {
	if(!firstConnect) {
		reconnect();
    	$('#disconnected-banner').slideUp('fast');
		$('#reconnected-banner').slideDown('fast', function() {
			setInterval(function () {
				$('#reconnected-banner').slideUp('fast');
			}, 2000);
		});
	}
	firstConnect = false;
});

stateSocket.addEventListener('close', (e) => {
	if (e.code != 1000) {
		// closed unexpectedly
		$('#disconnected-banner').slideDown('fast');
	}
});

$(window).on('beforeunload', function(){
	stateSocket.close();
});
