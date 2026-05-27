from __future__ import annotations

from pathlib import Path

import pytest

from alpha_core.domain.workspace.file_systems.local_file_system import LocalFileSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fs(
    base: Path,
    *,
    contained: bool = True,
    read_only: bool = False,
    allowed: list[Path] | None = None,
) -> LocalFileSystem:
    return LocalFileSystem(
        base, contained=contained, read_only=read_only, allowed_paths=allowed
    )


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


async def test_setup_creates_base_directory(tmp_path):
    base = tmp_path / "new_dir"
    fs = _fs(base)
    assert not base.exists()
    await fs.setup()
    assert base.is_dir()


async def test_setup_idempotent(tmp_path):
    fs = _fs(tmp_path)
    await fs.setup()
    await fs.setup()  # should not raise


# ---------------------------------------------------------------------------
# write_file / read_file
# ---------------------------------------------------------------------------


async def test_write_and_read_file(tmp_path):
    await _fs(tmp_path).setup()
    fs = _fs(tmp_path)
    fs.write_file("hello.txt", "world")
    assert fs.read_file("hello.txt") == "world"


async def test_write_file_creates_parent_dirs(tmp_path):
    fs = _fs(tmp_path)
    await fs.setup()
    fs.write_file("a/b/c.txt", "deep")
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------


def test_list_directory_returns_entries(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.py").write_text("b")
    fs = _fs(tmp_path)
    entries = fs.list_directory()
    names = {Path(e).name for e in entries}
    assert {"a.txt", "b.py"}.issubset(names)


def test_list_directory_with_glob_pattern(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.py").write_text("b")
    fs = _fs(tmp_path)
    py_files = fs.list_directory(pattern="*.py")
    assert all(e.endswith(".py") for e in py_files)
    assert len(py_files) == 1


# ---------------------------------------------------------------------------
# grep
# ---------------------------------------------------------------------------


def test_grep_finds_matching_lines(tmp_path):
    (tmp_path / "code.py").write_text("def hello():\n    pass\n")
    fs = _fs(tmp_path)
    matches = fs.grep(r"def \w+")
    assert any("def hello" in m for m in matches)


def test_grep_no_matches_returns_empty(tmp_path):
    (tmp_path / "f.txt").write_text("nothing here")
    fs = _fs(tmp_path)
    assert fs.grep(r"zzz_no_match") == []


def test_grep_returns_file_and_line_number(tmp_path):
    (tmp_path / "x.txt").write_text("line1\ntarget line\nline3\n")
    fs = _fs(tmp_path)
    matches = fs.grep("target")
    assert len(matches) == 1
    assert ":2:" in matches[0]


# ---------------------------------------------------------------------------
# stat
# ---------------------------------------------------------------------------


def test_stat_on_file(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("content")
    fs = _fs(tmp_path)
    s = fs.stat("f.txt")
    assert s["is_file"] is True
    assert s["is_dir"] is False
    assert s["size"] > 0


def test_stat_on_directory(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    fs = _fs(tmp_path)
    s = fs.stat("subdir")
    assert s["is_dir"] is True
    assert s["is_file"] is False


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------


def test_edit_file_replaces_first_occurrence(tmp_path):
    (tmp_path / "f.txt").write_text("aaa bbb aaa")
    fs = _fs(tmp_path)
    fs.edit_file("f.txt", "aaa", "xxx")
    assert (tmp_path / "f.txt").read_text() == "xxx bbb aaa"


def test_edit_file_old_string_not_found_raises(tmp_path):
    (tmp_path / "f.txt").write_text("hello world")
    fs = _fs(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        fs.edit_file("f.txt", "missing", "replacement")


# ---------------------------------------------------------------------------
# delete_file / delete_directory
# ---------------------------------------------------------------------------


def test_delete_file(tmp_path):
    f = tmp_path / "del.txt"
    f.write_text("x")
    fs = _fs(tmp_path)
    fs.delete_file("del.txt")
    assert not f.exists()


def test_delete_directory(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    (d / "f.txt").write_text("x")
    fs = _fs(tmp_path)
    fs.delete_directory("subdir")
    assert not d.exists()


# ---------------------------------------------------------------------------
# copy_file / move_file
# ---------------------------------------------------------------------------


def test_copy_file(tmp_path):
    (tmp_path / "src.txt").write_text("content")
    fs = _fs(tmp_path)
    fs.copy_file("src.txt", "dst.txt")
    assert (tmp_path / "src.txt").read_text() == "content"
    assert (tmp_path / "dst.txt").read_text() == "content"


def test_move_file(tmp_path):
    (tmp_path / "src.txt").write_text("content")
    fs = _fs(tmp_path)
    fs.move_file("src.txt", "dst.txt")
    assert not (tmp_path / "src.txt").exists()
    assert (tmp_path / "dst.txt").read_text() == "content"


# ---------------------------------------------------------------------------
# mkdir
# ---------------------------------------------------------------------------


def test_mkdir_creates_nested_directory(tmp_path):
    fs = _fs(tmp_path)
    fs.mkdir("a/b/c")
    assert (tmp_path / "a" / "b" / "c").is_dir()


def test_mkdir_idempotent(tmp_path):
    fs = _fs(tmp_path)
    fs.mkdir("existing")
    fs.mkdir("existing")  # should not raise


# ---------------------------------------------------------------------------
# Path containment
# ---------------------------------------------------------------------------


def test_escape_via_dotdot_raises(tmp_path):
    fs = _fs(tmp_path)
    with pytest.raises(PermissionError):
        fs.read_file("../../etc/passwd")


def test_absolute_path_outside_base_raises(tmp_path):
    fs = _fs(tmp_path)
    with pytest.raises(PermissionError):
        fs.read_file("/etc/passwd")


def test_allowed_path_permits_access(tmp_path):
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "data.txt").write_text("allowed data")
    fs = _fs(tmp_path, allowed=[extra])
    content = fs.read_file(str(extra / "data.txt"))
    assert content == "allowed data"


def test_contained_false_allows_absolute(tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    (target / "f.txt").write_text("data")
    fs = _fs(tmp_path / "base", contained=False)
    content = fs.read_file(str(target / "f.txt"))
    assert content == "data"


# ---------------------------------------------------------------------------
# Read-only enforcement
# ---------------------------------------------------------------------------


def test_read_only_write_file_raises(tmp_path):
    fs = _fs(tmp_path, read_only=True)
    with pytest.raises(PermissionError):
        fs.write_file("f.txt", "x")


def test_read_only_edit_file_raises(tmp_path):
    (tmp_path / "f.txt").write_text("old")
    fs = _fs(tmp_path, read_only=True)
    with pytest.raises(PermissionError):
        fs.edit_file("f.txt", "old", "new")


def test_read_only_delete_file_raises(tmp_path):
    (tmp_path / "f.txt").write_text("x")
    fs = _fs(tmp_path, read_only=True)
    with pytest.raises(PermissionError):
        fs.delete_file("f.txt")


def test_read_only_allows_reads(tmp_path):
    (tmp_path / "f.txt").write_text("readable")
    fs = _fs(tmp_path, read_only=True)
    assert fs.read_file("f.txt") == "readable"


def test_set_allowed_paths_replaces_existing(tmp_path):
    extra1 = tmp_path / "e1"
    extra2 = tmp_path / "e2"
    extra1.mkdir()
    extra2.mkdir()
    (extra2 / "f.txt").write_text("ok")

    fs = _fs(tmp_path, allowed=[extra1])
    fs.set_allowed_paths([extra2])
    content = fs.read_file(str(extra2 / "f.txt"))
    assert content == "ok"
