"CDN assets for Solara"

# Versioned on its own, not with solara: we only publish a new version when the
# assets change, to stay under the PyPI storage cap (that cap is why
# solara-assets was replaced by solara-assets2).
__version__ = "1.0.0"

# For each published version, the hash of the packages and prune rules in
# hatch_build.py that it ships. Only append, never edit an entry.
# tests/unit/solara_assets_test.py checks that the last entry matches
# hatch_build.py and __version__, and that each version has a new hash.
content_hashes = {
    "1.0.0": "b73aac8aec8a0db8",
}
