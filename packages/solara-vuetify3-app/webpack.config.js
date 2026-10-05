const path = require('path');
const webpack = require('webpack');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const TerserPlugin = require("terser-webpack-plugin");
const { slotInsert, cssChunkFilename, MoveCssPlugin, DropCssPlugin, WrapUmdFactoryPlugin, ChunkGuardPlugin, DedupePackagesPlugin } = require("../solara-widget-manager/webpack-plugins");

// Each frontend feature (vuetify, katex, jupyter-controls, ...) is a named async chunk:
// solara-vuetify-app{M}.{feature}{.min}.js and main{M}.{feature}.css.
// The server preloads the chunks of the enabled features, see solara/server/frontend_assets.py.

const rules = [
    { test: /\.css$/, use: [MiniCssExtractPlugin.loader, 'css-loader'] },
    // fonts are files, not data URIs: the browser fetches only the fonts a page uses
    // (KaTeX's CSS was 77 KB gzip with its fonts inlined, 4 KB without)
    {
        test: /\.(woff2?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
        type: 'asset/resource',
    },
];

const empty = path.resolve(__dirname, "src", "empty.js");

// one config per (ipywidgets major version, production|development)
function config(major, production) {
    const min = production ? '.min' : '';
    const widgetManager = major === 8 ? '@widgetti/solara-widget-manager8' : '@widgetti/solara-widget-manager';
    return {
        name: `solara-vuetify-app${major}${min}`,
        entry: './src/solara-vuetify-app.js',
        mode: production ? 'production' : 'development',
        // as before: no source map for prod 7, eval for dev 7
        devtool: major === 8 ? 'source-map' : (production ? false : 'eval'),
        output: {
            filename: `solara-vuetify-app${major}${min}.js`,
            chunkFilename: `solara-vuetify-app${major}.[name]${min}.js`,
            path: path.resolve(__dirname, 'dist'),
            libraryTarget: 'umd',
            // chunks load from where the core script came from (CDN, /_solara/cdn, solara-assets)
            publicPath: 'auto',
            // own JSONP global per build, so two builds can never share chunks
            uniqueName: `solara_vuetify3_app${major}${production ? '' : '_dev'}`,
            ...(production ? {} : { devtoolModuleFilenameTemplate: `webpack://@widgetti/solara-vuetify3-app` }),
        },
        plugins: [
            new MiniCssExtractPlugin({
                filename: `main${major}.css`,
                // main{M}.{chunk name}.css, but Vuetify's CSS (chunk vuetify-css) is main{M}.vuetify.css
                chunkFilename: cssChunkFilename(major),
                insert: slotInsert,
            }),
            // Vuetify's CSS (also the CSS its components import) loads with the vuetify-css feature, not with Vuetify
            new MoveCssPlugin('vuetify', 'vuetify-css'),
            // Vue's esm-bundler feature flags, as they are by default at runtime (options API on, hydration
            // mismatch details off); defined, terser drops the code behind them. __VUE_PROD_DEVTOOLS__ stays
            // a runtime global, so a page can still turn on the devtools in production, as before.
            new webpack.DefinePlugin({
                __VUE_OPTIONS_API__: 'true',
                __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
            }),
            new ChunkGuardPlugin(),
            new DedupePackagesPlugin(),
            // only the parts of the @jupyterlab/services index that we use (see solara-widget-manager/src/services.ts)
            new webpack.NormalModuleReplacementPlugin(
                /@jupyterlab[\\/]services[\\/]lib[\\/]index\.js$/,
                path.resolve(__dirname, 'node_modules', widgetManager, 'lib', 'services.js'),
            ),
            ...(production ? [] : [new DropCssPlugin(), new WrapUmdFactoryPlugin()]),
        ],
        module: {
            rules: rules
        },
        optimization: {
            // no shared chunks with generated names: every async chunk is one feature
            splitChunks: false,
            minimizer: [
                // without ascii_only, the chunks need <meta charset="utf-8"> on the page.
                // wrap_func_args (the default before terser 5.43) keeps a function passed as an argument in
                // parentheses, as in the published bundles: V8 then compiles the UMD factory, "(self,(()=>...))",
                // eagerly and off the main thread, instead of lazily on the main thread (see WrapUmdFactoryPlugin)
                new TerserPlugin({ terserOptions: { format: { ascii_only: true, wrap_func_args: true } } }),
                // also removes the duplicate Vuetify rules (dist + lib CSS), keeping the last copy.
                // mergeLonghand off: merging var() longhands into a shorthand changes the cascade, e.g.
                // Vuetify's .v-main padding-top/left longhands became one padding shorthand, and one invalid
                // var (--v-layout-left: NaN with a width="min-content" drawer) then voided padding-top as well
                new CssMinimizerPlugin({ minimizerOptions: { preset: ['default', { mergeLonghand: false }] } }),
            ],
        },
        resolve: {
            alias: {
                ...(major === 8 ? { "@widgetti/solara-widget-manager": widgetManager } : {}),
                vue$: 'vue/dist/vue.esm-bundler.js',
                // CodeMirror (markdown code highlighting) is a lazy chunk (see solara-widget-manager/src/codemirror.ts)
                '@jupyterlab/codemirror$': path.resolve(__dirname, 'node_modules', widgetManager, 'lib', 'codemirror.js'),
                // do not think we use this
                'moment': empty,
                // one sanitize-html copy, in the "sanitizer" chunk (see solara-widget-manager/src/sanitize.ts)
                'sanitize-html$': path.resolve(__dirname, 'node_modules', widgetManager, 'lib', 'sanitize.js'),
            }
        },
    };
}

module.exports = [config(7, true), config(7, false), config(8, true), config(8, false)];
