const webpack = require('webpack');
const glob = require('glob');

module.exports = {
  entry: glob.sync('./js/**/*.js'),
  devtool: false,
  plugins: [
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
    }),
  ],
  output: {
    filename: './bundle.js',
  },
  externals: {
    // Popper is only used for dropdowns and tooltips, neither of which is used
    // https://getbootstrap.com/docs/5.0/getting-started/introduction/
    'popper.js': 'Popper',
  },
};
