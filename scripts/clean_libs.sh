#!/bin/bash

cd static/libs || exit 1

KEEP=$(cat <<-EOF
	jquery/dist/jquery.min.js$
	bootstrap/dist/js/bootstrap.min.js$
	jquery-ui-dist/jquery-ui.min.js$
	jquery-ui-touch-punch/jquery.ui.touch-punch.min.js$
	jquerykeyframes/dist/jquery.keyframes.js$
	js-cookie/src/js.cookie.js$
	reconnecting-websocket/dist/reconnecting-websocket-iife.min.js$
	bootstrap/scss/.*
	markdown-it/dist/markdown-it.min.js$
	@fortawesome/fontawesome-free/webfonts/.*.woff2
	@fortawesome/fontawesome-free/scss/.*
EOF
)

KEEP=$(echo "$KEEP" | sed -z 's/\n/\\|/g' | sed 's/\\|$//')

find . -type f | grep -v "$KEEP" | xargs rm
find . -type d -empty -delete
