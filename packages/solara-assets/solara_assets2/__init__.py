"CDN assets for Solara"

# Versioned on its own, not with solara: we only publish a new version when the
# assets change, to stay under the PyPI storage cap (that cap is why
# solara-assets was replaced by solara-assets2).
__version__ = "1.0.0"

# Hash of the packages and prune rules in hatch_build.py that this version
# ships. tests/unit/solara_assets_test.py fails when they differ: bump
# __version__ (and the solara[assets] pin) and update this hash.
content_hash = "b73aac8aec8a0db8"
