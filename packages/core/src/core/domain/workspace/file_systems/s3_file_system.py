from __future__ import annotations

from core.contracts.workspace.file_system_contract import FileSystemContract


class S3FileSystem(FileSystemContract):
    """
    S3-backed filesystem (stub — not yet implemented).

    Expected constructor args:
        bucket:    S3 bucket name
        prefix:    Key prefix used as the root of all paths (default "")
        region:    AWS region (default: from environment / boto3 default chain)
        read_only: Block all write operations when True
    """

    def __init__(
        self,
        bucket: str,
        *,
        prefix: str = "",
        region: str | None = None,
        read_only: bool = False,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/")
        self._region = region
        self._read_only = read_only

    async def setup(self) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def read_file(self, path: str) -> str:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def write_file(self, path: str, content: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def edit_file(self, path: str, old_string: str, new_string: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def list_directory(self, path: str = ".", pattern: str = "*") -> list[str]:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def delete_file(self, path: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def delete_directory(self, path: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def copy_file(self, src: str, dst: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def move_file(self, src: str, dst: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def mkdir(self, path: str) -> None:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def grep(self, pattern: str, path: str = ".") -> list[str]:
        raise NotImplementedError("S3FileSystem is not yet implemented")

    def stat(self, path: str) -> dict:
        raise NotImplementedError("S3FileSystem is not yet implemented")


__all__ = ["S3FileSystem"]
