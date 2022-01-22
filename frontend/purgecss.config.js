module.exports = {
  // this needs to be specified in a config file
  // because the CLI does not handle multiple globs correctly
  content: ['ts/**/*.ts', '../backend/templates/*.html'],
  safelist: [
    'collapsing', // menu transition
    'modal-backdrop', // dimmed background behind modals
    'modal-open', // scrollable modals
    'svg', // network info qr codes
    'ui-helper-hidden-accessible', // dropdown helper text
  ],
};
