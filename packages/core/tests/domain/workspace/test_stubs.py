from __future__ import annotations

import pytest

from alpha_app.workspace.file_systems.s3_file_system import S3FileSystem
from alpha_app.workspace.sandboxes.e2b_sandbox import E2BSandbox


# ---------------------------------------------------------------------------
# S3FileSystem — all methods raise NotImplementedError
# ---------------------------------------------------------------------------


@pytest.fixture
def s3():
    return S3FileSystem(bucket="test-bucket")


async def test_s3_setup_raises(s3):
    with pytest.raises(NotImplementedError):
        await s3.setup()


def test_s3_read_file_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.read_file("key.txt")


def test_s3_write_file_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.write_file("key.txt", "content")


def test_s3_edit_file_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.edit_file("key.txt", "old", "new")


def test_s3_list_directory_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.list_directory()


def test_s3_delete_file_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.delete_file("key.txt")


def test_s3_delete_directory_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.delete_directory("prefix/")


def test_s3_copy_file_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.copy_file("src", "dst")


def test_s3_move_file_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.move_file("src", "dst")


def test_s3_mkdir_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.mkdir("prefix/")


def test_s3_grep_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.grep("pattern")


def test_s3_stat_raises(s3):
    with pytest.raises(NotImplementedError):
        s3.stat("key.txt")


# ---------------------------------------------------------------------------
# E2BSandbox — all methods raise NotImplementedError
# ---------------------------------------------------------------------------


@pytest.fixture
def e2b():
    return E2BSandbox(template="base")


async def test_e2b_setup_raises(e2b):
    with pytest.raises(NotImplementedError):
        await e2b.setup()


async def test_e2b_teardown_raises(e2b):
    with pytest.raises(NotImplementedError):
        await e2b.teardown()


async def test_e2b_execute_command_raises(e2b):
    with pytest.raises(NotImplementedError):
        await e2b.execute_command("echo hi")


async def test_e2b_get_process_output_raises(e2b):
    with pytest.raises(NotImplementedError):
        await e2b.get_process_output(1)


async def test_e2b_kill_process_raises(e2b):
    with pytest.raises(NotImplementedError):
        await e2b.kill_process(1)
