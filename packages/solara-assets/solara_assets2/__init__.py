"CDN assets for Solara"

# Versioned on its own, not with solara: we only publish a new version when the
# assets change, to stay under the PyPI storage cap (that cap is why
# solara-assets was replaced by solara-assets2).
# check_version.py fails in CI when the wheel changes without a version bump.
__version__ = "1.0.0"
