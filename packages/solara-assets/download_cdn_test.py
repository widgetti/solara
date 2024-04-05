from packages.assets.hatch_build import npm_pack


def test_npm_pack(tmp_path_factory):
    base_cache_dir = tmp_path_factory.mktemp("cdn")

    package = "@widgetti/solara-vuetify-app"
    version = "0.0.1-alpha.1"
    npm_pack(base_cache_dir, package, version)

    some_file = base_cache_dir / f"{package}@{version}" / "dist" / "037d830416495def72b7881024c14b7b.woff2"
    assert some_file.is_file()
    assert len(some_file.read_bytes()) == 15436
