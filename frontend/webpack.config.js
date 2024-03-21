const glob = require('glob');
const TerserPlugin = require('terser-webpack-plugin');
const webpack = require('webpack');

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
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        extractComments: false,
        terserOptions: {
          format: {
            comments: false,
          },
        },
      }),
    ],
  },
  performance: {
    maxEntrypointSize: 512000,
    maxAssetSize: 512000,
  },
  externals: {
    // Popper is only used for dropdowns and tooltips, neither of which is used
    // https://getbootstrap.com/docs/5.0/getting-started/introduction/
    'popper.js': 'Popper',
  },
};
