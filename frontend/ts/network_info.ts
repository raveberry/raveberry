import $ from "jquery";

export function onReady() {
	if (!window.location.pathname.endsWith('network_info/')) {
		return;
	}
    let password_plaintext = $("#password").text();
    if (password_plaintext != "Unknown") {
        let password_hidden = password_plaintext.replace(/./g, "•")
        $("#password").text(password_hidden);
        $("#show_password").on("click tap", function () {
            $("#password").text(password_plaintext);
        })
    }
}

$(document).ready(onReady);
