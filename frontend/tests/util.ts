import * as child from 'child_process';
import * as fs from 'fs';
import * as Cookies from 'js-cookie';

export function render_template(template, options?) {
	options = JSON.stringify(options) || '';
	const env = process.env;
	env["DJANGO_MOCK"] = "1";
	let p = child.spawnSync('python3', ['../manage.py', 'render_template', template, 'head.html', 'body.html', options], {
		env: env
	});
	if (p.error) {
		throw p.error;
	}
	if (p.status != 0) {
		console.error(p.stderr.toString('utf8'));
	}
}

export function prepareDocument() {
	let head = fs.readFileSync('head.html', 'utf8');
	let body = fs.readFileSync('body.html', 'utf8');
	let css = fs.readFileSync('../static/dark.css', 'utf8');
	document.head.innerHTML = head;
	document.body.innerHTML = body;
	// execute script that is included in head html
	eval($('script')[0].innerHTML);
	// prevent onReady functions from firing on their own
	(<any>$).isReady = true;
	let style = document.createElement("style");
	style.type = 'text/css';
	style.innerHTML = css;
	document.head.appendChild(style);
}

export function clearCookies() {
	for (let cookie in Cookies.get()) {
		Cookies.remove(cookie);
	}
}
