/* eslint no-unused-vars: off */
declare const CSRF_TOKEN: string;
declare const urls: { string: string; };
declare const INTERACTIVITY: string;
declare const INTERACTIVITIES: {
    fullControl: string;
    fullVoting: string;
    upvotesOnly: string;
    noControl: string;
};
declare const COLOR_INDICATION: boolean;
// needs to be writable for tests
declare let ADMIN: boolean;
declare const CONTROLS_ENABLED: boolean;

declare const ADDITIONAL_KEYWORDS: string;
declare const FORBIDDEN_KEYWORDS: string;
declare const CLIENT_STREAMING: boolean;
declare const YOUTUBE_SUGGESTIONS: number;
declare const SPOTIFY_SUGGESTIONS: number;
declare const SOUNDCLOUD_SUGGESTIONS: number;
declare const JAMENDO_SUGGESTIONS: number;

declare const SPOTIFY_SCOPE: string;
declare const SPOTIFY_OAUTH_AUTHORIZE_URL: string;

interface JQuery {
  // unfortunately, bootstrap and jqueryui
  // introduce conflicts with types 'button' and 'tooltip'
  // mock the types for the few jqueryui elements we use
  autocomplete: any;
  sortable: any;
}
interface JQueryStatic {
  keyframe: any;
  // jqueryui
  ui: any;
}
