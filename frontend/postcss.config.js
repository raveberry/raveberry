module.exports = {
  plugins: [
    require('cssnano')({
      // https://github.com/facebook/create-react-app/issues/11685
      preset: ['default', {
        colormin: false,
      }],
    }),
  ],
};
