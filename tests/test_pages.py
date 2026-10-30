"""Protect direct-entry and legacy dataset links on static hosting."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "prepare_pages", Path(__file__).resolve().parents[1] / "scripts" / "prepare_pages.py"
)
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)


def test_static_host_gets_canonical_legacy_and_category_entries(tmp_path):
    shell = b'<html><script src="/OpenDatasets/assets/app.js"></script></html>'
    (tmp_path / "index.html").write_bytes(shell)
    pages.prepare_pages(tmp_path, ["mnist", "cifar-10"])
    for route in ("explore", "about", "datasets", "submit", "dataset/mnist", "datasets/mnist",
                  "dataset/cifar-10", "datasets/computer-vision"):
        assert (tmp_path / route / "index.html").read_bytes() == shell
    assert (tmp_path / "404.html").read_bytes() == shell
    assert (tmp_path / ".nojekyll").exists()


def test_missing_build_is_not_silently_published(tmp_path):
    with pytest.raises(ValueError, match="missing"):
        pages.prepare_pages(tmp_path, ["mnist"])


@pytest.mark.parametrize("slug", ["../outside", "nested/path", "", "a?b"])
def test_output_cannot_escape_static_directory(tmp_path, slug):
    (tmp_path / "index.html").write_text("app shell")
    with pytest.raises(ValueError, match="Unsafe"):
        pages.prepare_pages(tmp_path, [slug])
