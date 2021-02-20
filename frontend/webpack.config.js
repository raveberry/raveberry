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
};
