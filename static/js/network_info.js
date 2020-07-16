$(document).ready(function() {
    let password_plaintext = $("#password").text();
    let password_hidden = password_plaintext.replace(/./g, "•")
    $("#password").text(password_hidden);
    $("#show_password").on("click tap", function() {
        $("#password").text(password_plaintext);
    })
});
