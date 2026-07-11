"""
Sandbox path traversal tests.
These run without a database or Redis - pure path resolution logic.
"""
import os
from pathlib import Path

import pytest

from app.services.file_service import resolve_in_workspace


@pytest.fixture(autouse=True)
def _patch_workspace(tmp_path, monkeypatch):
    root = tmp_path / "ODIN"
    root.mkdir()
    (root / "Inbox").mkdir()
    (root / "Projects").mkdir()
    monkeypatch.setattr("app.config.settings.WORKSPACE_ROOT", str(root))
    return root


def test_parent_traversal_rejected():
    """../../etc/passwd must raise ValueError."""
    with pytest.raises(ValueError):
        resolve_in_workspace("../../etc/passwd")


def test_absolute_path_rejected():
    with pytest.raises(ValueError):
        resolve_in_workspace("/etc/passwd")


def test_null_byte_rejected():
    with pytest.raises(ValueError):
        resolve_in_workspace("Inbox/file\x00.txt")


def test_sibling_prefix_rejected(tmp_path, monkeypatch):
    """WORKSPACE_ROOT + '2' must not satisfy a prefix check."""
    # Create ODIN2 as a sibling
    sibling = tmp_path / "ODIN2"
    sibling.mkdir()
    root = tmp_path / "ODIN"
    monkeypatch.setattr("app.config.settings.WORKSPACE_ROOT", str(root))
    with pytest.raises(ValueError):
        resolve_in_workspace(str(sibling / "secret.txt"))


def test_dotdot_inside_allowed():
    """Projects/../Inbox/x.txt resolves inside and is allowed."""
    path = resolve_in_workspace("Projects/../Inbox/x.txt")
    assert path.name == "x.txt"
    from app.services.file_service import workspace_root
    path.relative_to(workspace_root())  # must not raise


def test_valid_nested_path_allowed():
    path = resolve_in_workspace("Inbox/subfolder/file.pdf")
    from app.services.file_service import workspace_root
    path.relative_to(workspace_root())  # must not raise


def test_empty_path_returns_root():
    from app.services.file_service import workspace_root
    path = resolve_in_workspace("")
    assert path == workspace_root()
