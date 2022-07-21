const HtmlWebpackPlugin = require('html-webpack-plugin');
var path = require('path');

var rules = [
    { test: /\.css$/, use: ['style-loader', 'css-loader'] },
    {
        test: /\.(woff|woff2|eot|ttf|otf)$/,
        loader: 'file-loader',
    }
]


module.exports = [
    {
        entry: './src/index.js',
        output: {
            filename: 'index.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-milkdown`
        },
        module: {
            rules: rules
        },
        devtool: 'source-map',
        mode: 'development',
    },
    {
        entry: './src/index.js',
        output: {
            filename: 'index.min.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-milkdown`
        },
        module: {
            rules: rules
        },
        mode: 'production',
    }
];
