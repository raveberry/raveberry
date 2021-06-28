/* eslint no-unused-vars: off */
declare let CSRF_TOKEN: string;
declare let urls: { string: string; };
declare let VOTING_SYSTEM: boolean;
declare let ADMIN: boolean;
declare let CONTROLS_ENABLED: boolean;

declare let ADDITIONAL_KEYWORDS: string;
declare let FORBIDDEN_KEYWORDS: string;
declare let DYNAMIC_EMBEDDED_STREAM: boolean;

interface JQuery {
  // unfortunately, bootstrap and jqueryui introduce conflicts with types 'button' and 'tooltip'
  // mock the types for the few jqueryui elements we use
  autocomplete: any;
  sortable: any;
}
interface JQueryStatic {
  keyframe: any;
  // jqueryui
  ui: any;
}
