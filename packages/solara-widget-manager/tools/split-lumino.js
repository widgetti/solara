// Compiles the TypeScript sources of some Lumino packages (shipped in their npm package, src/) to one ES
// module per source file, so webpack can leave out the files the core bundle does not use. The published
// dist/ of each is one flat file (a rollup of the same per-file output), which webpack cannot tree-shake.
// The app bundles use the result through SplitPackagesPlugin (splitLuminoPlugin in ../webpack-plugins.js).
//
// The output has the form of dist/index.es6.js: ES5 classes (third-party ES5 code may call
// Widget.call(this)) and enumerable accessors. That is why it uses the TypeScript version these Lumino
// versions were built with (~3.6, see below): TypeScript 3.9 and later make
// accessors non-enumerable. Every check below is a hard error, so a version change cannot go unnoticed.
// TypeScript 3.6 is a dependency of this folder (package.json here), not of the widget manager packages,
// so their "tsc" stays TypeScript 5. The first run installs it (npm ci, from package-lock.json here).
//
// usage: node split-lumino.js [widget manager package dir, default: the current dir]
//   writes <dir>/node_modules/@lumino/<name>/split/*.js: inside the package, so the imports resolve
//   to the same dependency copies as the package's dist/ (e.g. its nested @lumino/coreutils 1.x)
// The widget manager packages run it before their build (prepare, prebuild and prewatch).
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

// the exact versions this was checked for; the core bundle uses some of their files, the lumino chunk the rest
const PACKAGES = {
    widgets: '1.37.2',
    algorithm: '1.9.2',
    collections: '1.9.3',
};
const TYPESCRIPT = /^3\.6\./;

function fail(message) {
    console.error(`split-lumino: ${message}`);
    process.exit(1);
}

function typescriptVersion() {
    try {
        return JSON.parse(fs.readFileSync(path.join(__dirname, 'node_modules', 'typescript', 'package.json'), 'utf8')).version;
    } catch (e) {
        return null;
    }
}

const pkgDir = path.resolve(process.argv[2] || '.');
if (!TYPESCRIPT.test(typescriptVersion() || '')) {
    const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    const result = childProcess.spawnSync(npm, ['ci', '--no-audit', '--no-fund', '--ignore-scripts'], {
        cwd: __dirname,
        stdio: 'inherit',
        shell: process.platform === 'win32',
    });
    if (result.status !== 0) {
        fail(`npm ci in ${__dirname} failed`);
    }
}
const ts = require(path.join(__dirname, 'node_modules', 'typescript'));
if (!TYPESCRIPT.test(ts.version)) {
    fail(`TypeScript is ${ts.version} in ${__dirname}, expected 3.6.x`);
}

for (const [name, expected] of Object.entries(PACKAGES)) {
    const packageDir = path.join(pkgDir, 'node_modules', '@lumino', name);
    const version = JSON.parse(fs.readFileSync(path.join(packageDir, 'package.json'), 'utf8')).version;
    if (version !== expected) {
        fail(`@lumino/${name} is ${version}, but the split was checked for ${expected}: check the split output and update PACKAGES`);
    }
    const srcDir = path.join(packageDir, 'src');
    const outDir = path.join(packageDir, 'split');
    const dist = fs.readFileSync(path.join(packageDir, 'dist', 'index.es6.js'), 'utf8');
    fs.rmSync(outDir, { recursive: true, force: true });
    fs.mkdirSync(outDir);
    let enumerable = 0;
    let hidden = 0;
    let modules = 0;
    for (const file of fs.readdirSync(srcDir).sort()) {
        if (!file.endsWith('.ts') || file.endsWith('.d.ts')) {
            continue;
        }
        const source = fs.readFileSync(path.join(srcDir, file), 'utf8');
        const result = ts.transpileModule(source, {
            fileName: file,
            reportDiagnostics: true,
            compilerOptions: {
                target: ts.ScriptTarget.ES5,
                module: ts.ModuleKind.ES2015,
                importHelpers: true,
                sourceMap: false,
            },
        });
        if (result.diagnostics && result.diagnostics.length) {
            fail(result.diagnostics.map(d => `${file}: ${ts.flattenDiagnosticMessageText(d.messageText, '\n')}`).join('\n'));
        }
        enumerable += (result.outputText.match(/enumerable: true,/g) || []).length;
        hidden += (result.outputText.match(/enumerable: false,/g) || []).length;
        const header = `// generated from @lumino/${name}@${version} src/${file} by split-lumino.js (TypeScript ${ts.version})\n`;
        fs.writeFileSync(path.join(outDir, file.replace(/\.ts$/, '.js')), header + result.outputText);
        modules += 1;
    }
    // the accessors must be enumerable, as in dist (some code copies or lists the properties of a widget)
    const distEnumerable = (dist.match(/enumerable: true,/g) || []).length;
    const distHidden = (dist.match(/enumerable: false,/g) || []).length;
    if (hidden !== distHidden || enumerable !== distEnumerable) {
        fail(`@lumino/${name}: ${enumerable} enumerable and ${hidden} non-enumerable accessors, dist has ${distEnumerable} and ${distHidden}`);
    }
    // "version" lets the app build check that the split belongs to the installed package
    const description = { name: `lumino-${name}-split`, version, private: true, sideEffects: false, module: 'index.js', main: 'index.js' };
    fs.writeFileSync(path.join(outDir, 'package.json'), JSON.stringify(description, null, 2) + '\n');
    console.log(`split-lumino: @lumino/${name}@${version}: ${modules} modules, ${enumerable}/${distEnumerable} accessors enumerable`);
}
