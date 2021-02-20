import '@testing-library/jest-dom';
import * as fs from 'fs';
import * as child from 'child_process';

// add jQuery to the global scope so libraries depending on it can be loaded
import * as $ from 'jquery';
global['$'] = global['jQuery'] = $;

global['CSRF_TOKEN'] = '';
global['urls'] = {};
global['VOTING_SYSTEM'] = false;
global['ADMIN'] = false;
global['CONTROLS_ENABLED'] = false;

// create the css file if necessary
try {
  fs.statSync('../static/dark.css');
} catch (err) {
  if (err.code == 'ENOENT') {
    child.spawnSync('yarn', ['sass', 'scss/dark.scss', '../static/dark.css']);
  }
}
