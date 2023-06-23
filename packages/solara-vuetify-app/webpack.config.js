var path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

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
        plugins: [new MiniCssExtractPlugin()],
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
        plugins: [new MiniCssExtractPlugin()],
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
        plugins: [new MiniCssExtractPlugin()],
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
        resolve: {
            alias: {
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager8",
            }
        },
        mode: 'production',
    }, {
        plugins: [new MiniCssExtractPlugin()],
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
