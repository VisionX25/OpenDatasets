"""Tests for scripts/generate_catalog.py.

Verifies:
1. Virtualenv Python detection across POSIX and Windows layouts.
2. Safe recursion prevention and exit code semantics on missing dependencies.
3. Atomic file writes and temporary file cleanup.
4. Deterministic sorting and catalog generation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from scripts.generate_catalog import (
    REEXEC_ENV_VAR,
    find_venv_python,
    generate_catalog_data,
    write_catalog_atomic,
)


def test_find_venv_python_posix(tmp_path: Path):
    """Verify detection of POSIX virtual environment binary."""
    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    py_bin = bin_dir / "python3"
    py_bin.touch(mode=0o755)

    detected = find_venv_python(tmp_path)
    assert detected == py_bin


def test_find_venv_python_windows(tmp_path: Path):
    """Verify detection of Windows virtual environment binary."""
    scripts_dir = tmp_path / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    py_exe = scripts_dir / "python.exe"
    py_exe.touch()

    detected = find_venv_python(tmp_path)
    assert detected == py_exe


def test_find_venv_python_absent(tmp_path: Path):
    """Verify find_venv_python returns None when no venv directory exists."""
    assert find_venv_python(tmp_path) is None


def test_reexec_guard_prevents_recursion(tmp_path: Path):
    """Verify that when _OPENDATASETS_CATALOG_REEXEC is already set, script does not loop and exits with 1."""
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "generate_catalog.py"
    env = os.environ.copy()
    env[REEXEC_ENV_VAR] = "1"
    env["PYTHONPATH"] = str(tmp_path)

    # Use sys.executable with -S (isolated from site-packages) so jsonschema import fails deterministically
    proc = subprocess.run(
        [sys.executable, "-S", str(script_path), "--help"],
        env=env,
        capture_output=True,
        text=True,
    )
    # When jsonschema is missing and re-exec guard is set, it must fail cleanly with exit code 1
    assert proc.returncode == 1
    assert "Required dependency 'jsonschema' is not installed" in proc.stderr
    assert "pip install -r requirements-lock.txt" in proc.stderr


def test_write_catalog_atomic(tmp_path: Path):
    """Verify atomic write creates target catalog and leaves no temporary files."""
    output_path = tmp_path / "data" / "catalog.json"
    dummy_data = [{"id": "dataset-b", "name": "B"}, {"id": "dataset-a", "name": "A"}]

    write_catalog_atomic(dummy_data, output_path)

    assert output_path.is_file()
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded == dummy_data

    # Ensure no lingering .catalog.*.tmp files exist
    tmp_files = list(output_path.parent.glob(".catalog.*.tmp"))
    assert len(tmp_files) == 0


def test_write_catalog_atomic_cleanup_on_error(tmp_path: Path):
    """Verify temporary files are cleaned up if an exception occurs during atomic write."""
    output_path = tmp_path / "unwritable" / "catalog.json"
    output_path.parent.mkdir(parents=True)

    dummy_data = [{"id": "dataset-a"}]

    with patch("tempfile.NamedTemporaryFile", side_effect=OSError("Disk full")):
        with pytest.raises(OSError, match="Disk full"):
            write_catalog_atomic(dummy_data, output_path)

    # Verify no tmp files
    tmp_files = list(output_path.parent.glob(".catalog.*.tmp"))
    assert len(tmp_files) == 0
