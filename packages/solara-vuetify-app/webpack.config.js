var path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

var rules = [
    { test: /\.css$/, use: [MiniCssExtractPlugin.loader, 'css-loader'] },
    {
        test: /\.(woff|woff2|eot|ttf|otf)$/,
        loader: 'file-loader',
    }
]

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
        resolve: {
            alias: {
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager/dist/solara-widget-manager7.min.js"
            }
        },
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
        resolve: {
            alias: {
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager/dist/solara-widget-manager7.js"
            }
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
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager/dist/solara-widget-manager8.min.js"
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
                "@widgetti/solara-widget-manager": "@widgetti/solara-widget-manager/dist/solara-widget-manager8.js"
            }
        },
        mode: 'development',
    },
];
