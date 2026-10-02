import pytest

pytest.importorskip("pixelmatch")

from PIL import Image  # noqa: E402

from solara.test.pytest_plugin import compare_default  # noqa: E402


def test_compare_default_reports_the_difference():
    reference = Image.new("RGB", (8, 8), (255, 0, 0))
    result = Image.new("RGB", (8, 8), (0, 0, 255))
    diff, difference = compare_default(reference, result)
    assert diff == 64
    assert difference.size == reference.size
    assert difference.mode == "RGB"
