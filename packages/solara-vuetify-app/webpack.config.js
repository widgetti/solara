var path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;

const analyzerPlugins = process.env.ANALYZE === "true" ? [
    new BundleAnalyzerPlugin({analyzerPort: 9999})] : [];

var rules = [
    { test: /\.css$/, use: [MiniCssExtractPlugin.loader, 'css-loader'] },
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

module.exports = [
    {
        plugins: [new MiniCssExtractPlugin({filename: 'fonts.css'})],
        entry: './src/fonts.js',
        output: {
            filename: 'fonts.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
        },
        module: {
            rules: rules
        },
        mode: 'production',
    },
    {
        plugins: [new MiniCssExtractPlugin({filename: 'main7.css'})],
        entry: './src/solara-vuetify-app.js',
        output: {
            filename: 'solara-vuetify-app7.min.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
        },
        module: {
            rules: rules
        },
        mode: 'production',
    },
    {
        plugins: [new MiniCssExtractPlugin({filename: 'main7.css'})],
        entry: './src/solara-vuetify-app.js',
        output: {
            filename: 'solara-vuetify-app7.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
            devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-vuetify-app`
        },
        module: {
            rules: rules
        },
        mode: 'development',
    },
    {
        plugins: [new MiniCssExtractPlugin({filename: 'main8.css'}), ...analyzerPlugins],
        entry: './src/solara-vuetify-app.js',
        output: {
            filename: 'solara-vuetify-app8.min.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
        },
        devtool: 'source-map',
        module: {
            rules: rules
        },
        optimization: {
            concatenateModules: false,
        },
        resolve: {
            alias: {
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager8",
                // why would we need codemirror?
                '@jupyterlab/codemirror': path.resolve(__dirname, "src", "empty.js"),
                // used in @jupyterlab/rendermine/lib/registry
                '@jupyterlab/apputils/lib/sanitizer': path.resolve(__dirname, "src", "empty.js"),
                // do not think we use these
                'htmlparser2': path.resolve(__dirname, "src", "empty.js"),
                'postcss': path.resolve(__dirname, "src", "empty.js"),
                'moment': path.resolve(__dirname, "src", "empty.js"),
            }
        },
        mode: 'production',
    }, {
        plugins: [new MiniCssExtractPlugin({filename: 'main8.css'})],
        entry: './src/solara-vuetify-app.js',
        output: {
            filename: 'solara-vuetify-app8.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
            devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-vuetify-app`
        },
        devtool: 'source-map',
        module: {
            rules: rules
        },
        resolve: {
            alias: {
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager8",
            }
        },
        mode: 'development',
    },
];
