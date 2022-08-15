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
        entry: './src/solara-vuetify-app.js',
        output: {
            filename: 'solara-vuetify-app.min.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
        },
        devtool: 'source-map',
        module: {
            rules: rules
        },
        mode: 'production',
    }, {
        entry: './src/solara-vuetify-app.js',
        output: {
            filename: 'solara-vuetify-app.js',
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            publicPath: 'auto',
            devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-vuetify-app`
        },
        devtool: 'source-map',
        module: {
            rules: rules
        },
        mode: 'development',
    },
];
