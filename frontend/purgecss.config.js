module.exports = {
  // this needs to be specified in a config file because the CLI does not handle multiple globs correctly
  content: ['ts/**/*.ts', '../templates/*.html'],
  safelist: [
    'collapsing', // menu transition
    'modal-backdrop', // dimmed background behind modals
    'svg' // network info qr codes
  ],
}
