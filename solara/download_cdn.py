from solara.server.cdn_helper import default_cache_dir, npm_pack

packages = [
    ["@widgetti/solara-vuetify-app", "0.0.1-alpha.1"],
    ["requirejs", "2.3.6"],
    ["mermaid", "8.6.4"],
    ["codemirror", "5.65.3"],
    ["vega", "5.21.0"],
    ["vega-lite", "5.2.0"],
    ["vega-embed", "6.20.2"],
    ["@widgetti/vue-grid-layout", "2.3.13-alpha.2"],
]

for package, version in packages:
    npm_pack(default_cache_dir, package, version)
