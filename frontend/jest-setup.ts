import '@testing-library/jest-dom';
import * as fs from 'fs';
import * as child from 'child_process';

// Explicitly declaring the global object for tests gets rid of this jest error:
// Property <property> does not exist on type 'typeof globalThis'.
declare const global: any;

// add jQuery to the global scope so libraries depending on it can be loaded
import * as $ from 'jquery';
global['$'] = global['jQuery'] = $;

global['CSRF_TOKEN'] = '';
global['urls'] = {};
global['VOTING_ENABLED'] = false;
global['ADMIN'] = false;
global['CONTROLS_ENABLED'] = false;
// used in musiq tests
// needs to set here because it raises typing errors in  the test module
global['ADDITIONAL_KEYWORDS'] = '';
global['FORBIDDEN_KEYWORDS'] = '';
global['YOUTUBE_SUGGESTIONS'] = 0;
global['SPOTIFY_SUGGESTIONS'] = 0;
global['SOUNDCLOUD_SUGGESTIONS'] = 0;
global['JAMENDO_SUGGESTIONS'] = 0;


// create the css file if necessary
try {
  fs.statSync('../static/dark.css');
} catch (err) {
  if (err.code == 'ENOENT') {
    child.spawnSync('yarn', ['sass', 'scss/dark.scss', '../static/dark.css']);
  }
}
