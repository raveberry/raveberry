import * as child from 'child_process';
import * as fs from 'fs';

export function renderTemplate(template, options?) {
  options = JSON.stringify(options) || '';
  const p = child.spawnSync('python3', ['../manage.py', 'rendertemplate', template, 'head.html', 'body.html', options]);
  if (p.error) {
    throw p.error;
  }
  if (p.status != 0) {
    console.error(p.stderr.toString());
  }
}

export function prepareDocument() {
  const head = fs.readFileSync('head.html', 'utf8');
  const body = fs.readFileSync('body.html', 'utf8');
  const css = fs.readFileSync('../static/style.css', 'utf8');
  document.head.innerHTML = head;
  document.body.innerHTML = body;
  // execute script that is included in head html
  eval($('script')[0].innerHTML);
  // prevent onReady functions from firing on their own
  (<any>$).isReady = true;
  const style = document.createElement('style');
  style.type = 'text/css';
  style.innerHTML = css;
  document.head.appendChild(style);
}
