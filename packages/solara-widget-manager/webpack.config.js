var path = require('path');


var rules = [
  { test: /\.css$/, use: ['style-loader', 'css-loader'] },
  // required to load font-awesome
  {
    test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
    type: 'asset',
  },
  {
    test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
    type: 'asset',
  },
  {
    test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
    type: 'asset',
  },
  {
    test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
    type: 'asset',
  },
  {
    test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
    type: 'asset',
  }
];

var distRoot = path.resolve(
  __dirname,
  '..',
  '..',
  'solara',
  'server',
  'static',
  'dist',
);

module.exports = [
  {
    entry: ['./lib/index.js'],
    output: {
      filename: 'solara-widget-manager7.js',
      libraryTarget: 'umd',
      devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-widget-manager`
    },
    module: { rules: rules },
    devtool: 'source-map',
    mode: 'development',
  },
  {
    entry: ['./lib/index.js'],
    output: {
      filename: 'solara-widget-manager8.js',
      libraryTarget: 'umd',
      devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-widget-manager`
    },
    resolve: {
      alias: {
        "@jupyter-widgets/base": "@jupyter-widgets/base8",
        "@jupyter-widgets/controls": "@jupyter-widgets/controls8",
        "@jupyter-widgets/jupyterlab-manager": "@jupyter-widgets/jupyterlab-manager8",
      }
    },
    module: { rules: rules },
    devtool: 'source-map',
    mode: 'development',
  },
  {
    entry: ['./lib/index.js'],
    output: {
      filename: 'solara-widget-manager7.min.js',
      libraryTarget: 'umd',
      devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-widget-manager`
    },
    module: { rules: rules },
    mode: 'production',
  },
  {
    entry: ['./lib/index.js'],
    output: {
      filename: 'solara-widget-manager8.min.js',
      libraryTarget: 'umd',
      devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-widget-manager`
    },
    resolve: {
      alias: {
        "@jupyter-widgets/base": "@jupyter-widgets/base8",
        "@jupyter-widgets/controls": "@jupyter-widgets/controls8",
        "@jupyter-widgets/jupyterlab-manager": "@jupyter-widgets/jupyterlab-manager8",
      }
    },
    module: { rules: rules },
    mode: 'production',
  },
];
