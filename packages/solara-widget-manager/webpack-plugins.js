// Webpack helpers shared by the app bundles (solara-vuetify-app and solara-vuetify3-app),
// which bundle this widget manager with its feature chunks.
const fs = require('fs');
const path = require('path');

const PLUGIN = 'SolaraFeatureChunks';

// Lazy loaded chunk CSS main{M}.{name}.css goes to the <template data-solara-css-slot="name"> the
// server put where a preloaded link of that feature would be, so the CSS order is the same.
// This function runs in the browser: mini-css-extract-plugin inlines its source.
function slotInsert(linkTag) {
    var match = /main\d\.([a-z-]+)\.css/.exec(linkTag.href);
    var slot = match && document.querySelector('template[data-solara-css-slot="' + match[1] + '"]');
    if (slot) {
        slot.parentNode.insertBefore(linkTag, slot);
    } else {
        document.head.appendChild(linkTag);
    }
}

// The CSS file of an async chunk is main{M}.{chunk name}.css, except for the chunks in CSS_NAMES. The chunk of
// the vuetify-css feature (Vuetify's CSS) writes main{M}.vuetify.css, the name of Vuetify's CSS before it was a
// feature of its own, so a page with Vuetify's CSS stays the same. slotInsert takes the slot name from the file
// name ("vuetify"), and so does the server (css_name in solara/server/frontend_assets.py).
const CSS_NAMES = { 'vuetify-css': 'vuetify' };

function cssChunkFilename(major) {
    return pathData => `main${major}.${CSS_NAMES[pathData.chunk.name] || '[name]'}.css`;
}

// Moves the CSS of the chunk named `from` into the chunk named `to`, so the CSS loads with `to`, not with `from`.
// On Vue 3, Vuetify's components import their own CSS, so Vuetify's CSS would load with the vuetify JS chunk; it
// goes to the vuetify-css chunk instead (a CSS-only feature), and "-vuetify-css" leaves it out, also when Vuetify
// loads on first use. The CSS file stays the same: mini-css-extract-plugin orders the CSS of a chunk by each
// module's post-order index in the chunk group, and the modules keep the index they had in the group of `from`.
class MoveCssPlugin {
    constructor(from, to) {
        this.from = from;
        this.to = to;
    }

    apply(compiler) {
        const { WebpackError } = compiler.webpack;
        compiler.hooks.thisCompilation.tap(PLUGIN, compilation => {
            compilation.hooks.afterOptimizeChunks.tap(PLUGIN, () => {
                const error = message => compilation.errors.push(new WebpackError(`MoveCssPlugin: ${message}`));
                const chunkGraph = compilation.chunkGraph;
                const from = compilation.namedChunks.get(this.from);
                const to = compilation.namedChunks.get(this.to);
                if (!from || !to) {
                    return error(`no chunk named ${from ? this.to : this.from}`);
                }
                const fromGroups = [...from.groupsIterable];
                const toGroups = [...to.groupsIterable];
                if (fromGroups.length !== 1 || toGroups.length !== 1) {
                    return error(`chunks ${this.from} and ${this.to} must each be in one chunk group, so the CSS order is known`);
                }
                const css = chunkGraph.getChunkModules(from).filter(module => module.type === 'css/mini-extract');
                if (!css.length) {
                    return error(`chunk ${this.from} has no CSS`);
                }
                for (const module of css) {
                    toGroups[0].setModulePostOrderIndex(module, fromGroups[0].getModulePostOrderIndex(module));
                    chunkGraph.disconnectChunkAndModule(from, module);
                    chunkGraph.connectChunkAndModule(to, module);
                }
            });
        });
    }
}

// Only the production builds write CSS and fonts. The development builds use the same
// CSS file names, so they do not race with the production build on the same files.
class DropCssPlugin {
    apply(compiler) {
        const { Compilation } = compiler.webpack;
        compiler.hooks.thisCompilation.tap(PLUGIN, compilation => {
            compilation.hooks.processAssets.tap({ name: PLUGIN, stage: Compilation.PROCESS_ASSETS_STAGE_REPORT }, assets => {
                Object.keys(assets)
                    .filter(name => /\.(css|woff2?|ttf|eot|svg)(\.map)?$/.test(name))
                    .forEach(name => compilation.deleteAsset(name));
            });
        });
    }
}

// V8 compiles a function in parentheses eagerly, as part of the script compile, which Chrome streams
// off the main thread. A function without them compiles lazily on the main thread when it is called.
// The UMD wrapper calls its factory at once, so the factory needs the parentheses:
// "})(self, (() => {...}));". The production builds get them from terser (format.wrap_func_args);
// the development builds are not minified, so this plugin adds them. It fails the build when the
// wrapper does not look as expected, so the parentheses cannot get lost without notice.
// webpack's development UMD output, for comparison: "})(self, () => {...});" (also in the published bundles).
const UMD_FACTORY_START = /^\}\)\([A-Za-z_$][\w$]*, \(\) => \{$/m;

class WrapUmdFactoryPlugin {
    apply(compiler) {
        const { Compilation, sources } = compiler.webpack;
        compiler.hooks.thisCompilation.tap(PLUGIN, compilation => {
            // before the source map (dev tooling stage) is made, so the map accounts for the two characters
            compilation.hooks.processAssets.tap({ name: PLUGIN, stage: Compilation.PROCESS_ASSETS_STAGE_OPTIMIZE }, () => {
                for (const chunk of compilation.chunks) {
                    if (!chunk.canBeInitial()) {
                        continue; // async chunks have no UMD wrapper
                    }
                    for (const file of chunk.files) {
                        if (!file.endsWith('.js')) {
                            continue;
                        }
                        const asset = compilation.getAsset(file);
                        const text = asset.source.source().toString();
                        const start = UMD_FACTORY_START.exec(text);
                        const end = text.lastIndexOf('\n});');
                        if (!start || start.index > 2000 || end === -1 || text.slice(end + 4).trim() !== '') {
                            throw new Error(`${PLUGIN}: ${file} does not have the expected UMD wrapper, cannot wrap its factory`);
                        }
                        const source = new sources.ReplaceSource(asset.source);
                        // "})(self, () => {" -> "})(self, (() => {" and the final "});" -> "}));"
                        source.insert(start.index + start[0].indexOf('() =>'), '(');
                        source.insert(end + 2, ')');
                        compilation.updateAsset(file, source);
                    }
                }
            });
        });
    }
}

// Fails the build on a chunk without a name (the server computes the file names), and on
// a module over 2 KB that is in more than one chunk (it would be downloaded twice; give
// it its own named chunk instead, as for the sanitizer).
// Async chunks that no webpackChunkName comment can name get their name from a module in them.
// The AMD require() in @jupyterlab/codemirror/lib/mode.js loads the less common CodeMirror modes.
const NAME_BY_MODULE = [
    { test: /[\\/]codemirror[\\/]mode[\\/]/, name: 'codemirror-modes' },
];

class ChunkGuardPlugin {
    apply(compiler) {
        const { WebpackError } = compiler.webpack;
        compiler.hooks.thisCompilation.tap(PLUGIN, compilation => {
            compilation.hooks.optimizeChunks.tap(PLUGIN, chunks => {
                for (const chunk of chunks) {
                    if (chunk.name) {
                        continue;
                    }
                    for (const module of compilation.chunkGraph.getChunkModulesIterable(chunk)) {
                        const found = module.resource && NAME_BY_MODULE.find(({ test }) => test.test(module.resource));
                        if (found && !compilation.namedChunks.has(found.name)) {
                            chunk.name = found.name;
                            compilation.namedChunks.set(found.name, chunk);
                            break;
                        }
                    }
                }
            });
            compilation.hooks.afterSeal.tap(PLUGIN, () => {
                const chunkGraph = compilation.chunkGraph;
                const describe = module => module.readableIdentifier(compilation.requestShortener);
                for (const chunk of compilation.chunks) {
                    if (!chunk.name) {
                        const modules = chunkGraph.getChunkModules(chunk).slice(0, 3).map(describe);
                        compilation.errors.push(new WebpackError(`ChunkGuardPlugin: unnamed chunk ${chunk.id} (${modules.join(', ')})`));
                    }
                }
                for (const module of compilation.modules) {
                    const chunks = chunkGraph.getModuleChunks(module);
                    if (chunks.length > 1 && module.size() > 2048) {
                        compilation.errors.push(new WebpackError(
                            `ChunkGuardPlugin: ${describe(module)} (${module.size()} B) is in chunks ${chunks.map(c => c.name).join(', ')}`
                        ));
                    }
                }
            });
        });
    }
}

// npm installs one copy of a package per dependent when versions conflict higher up, e.g.
// 7 copies of @lumino/coreutils 1.12.1 in solara-widget-manager8. This resolves every
// copy of the same name@version to one copy (only for byte-identical files, so a
// patch-package patch on one copy is never lost).
class DedupePackagesPlugin {
    constructor() {
        this.packages = new Map(); // node_modules root -> Map(name@version -> [package dirs])
        this.versions = new Map(); // package dir -> version
        this.same = new Map(); // "file|file" -> bool
        this.count = 0;
    }

    version(dir) {
        if (!this.versions.has(dir)) {
            let version = null;
            try {
                version = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8')).version;
            } catch (e) {
                // no package.json: not a package root
            }
            this.versions.set(dir, version);
        }
        return this.versions.get(dir);
    }

    // all package dirs under a top-level node_modules dir, by name@version
    scan(root) {
        if (!this.packages.has(root)) {
            const byKey = new Map();
            const walk = (nodeModules, depth) => {
                let entries = [];
                try {
                    entries = fs.readdirSync(nodeModules, { withFileTypes: true });
                } catch (e) {
                    return;
                }
                for (const entry of entries) {
                    if (!entry.isDirectory() || entry.name.startsWith('.')) {
                        continue;
                    }
                    const names = entry.name.startsWith('@')
                        ? fs.readdirSync(path.join(nodeModules, entry.name)).map(n => `${entry.name}/${n}`)
                        : [entry.name];
                    for (const name of names) {
                        const dir = path.join(nodeModules, name);
                        const version = this.version(dir);
                        if (version) {
                            const key = `${name}@${version}`;
                            byKey.set(key, [...(byKey.get(key) || []), dir]);
                        }
                        if (depth < 8) {
                            walk(path.join(dir, 'node_modules'), depth + 1);
                        }
                    }
                }
            };
            walk(root, 0);
            for (const dirs of byKey.values()) {
                dirs.sort((a, b) => a.length - b.length || (a < b ? -1 : 1));
            }
            this.packages.set(root, byKey);
        }
        return this.packages.get(root);
    }

    sameFile(a, b) {
        const key = `${a}|${b}`;
        if (!this.same.has(key)) {
            let same = false;
            try {
                same = fs.readFileSync(a).equals(fs.readFileSync(b));
            } catch (e) {
                // missing in the other copy
            }
            this.same.set(key, same);
        }
        return this.same.get(key);
    }

    apply(compiler) {
        compiler.hooks.normalModuleFactory.tap(PLUGIN, nmf => {
            nmf.hooks.afterResolve.tap(PLUGIN, resolveData => {
                const data = resolveData.createData;
                const resource = data.resource;
                const first = resource && resource.indexOf(`${path.sep}node_modules${path.sep}`);
                if (!resource || first === -1) {
                    return;
                }
                // the package that owns the file: after the last node_modules
                const match = /^(.*[\\/]node_modules[\\/])((?:@[^\\/]+[\\/])?[^\\/]+)([\\/].*)$/.exec(resource);
                if (!match) {
                    return;
                }
                const [, prefix, name, rest] = match;
                const dir = prefix + name;
                const version = this.version(dir);
                if (!version) {
                    return;
                }
                const root = resource.slice(0, first + `${path.sep}node_modules`.length);
                const dirs = this.scan(root).get(`${name.split(path.sep).join('/')}@${version}`) || [];
                const canonical = dirs[0];
                if (!canonical || canonical === dir) {
                    return;
                }
                const file = rest.split('?')[0];
                if (!this.sameFile(dir + file, canonical + file)) {
                    return;
                }
                const replace = value => (typeof value === 'string' ? value.split(dir + path.sep).join(canonical + path.sep) : value);
                data.resource = replace(data.resource);
                data.request = replace(data.request);
                data.userRequest = replace(data.userRequest);
                if (data.resourceResolveData) {
                    const r = data.resourceResolveData;
                    r.path = replace(r.path);
                    r.descriptionFilePath = replace(r.descriptionFilePath);
                    r.descriptionFileRoot = r.descriptionFileRoot === dir ? canonical : replace(r.descriptionFileRoot);
                }
                this.count += 1;
            });
        });
    }
}

module.exports = { slotInsert, cssChunkFilename, MoveCssPlugin, DropCssPlugin, WrapUmdFactoryPlugin, ChunkGuardPlugin, DedupePackagesPlugin };
