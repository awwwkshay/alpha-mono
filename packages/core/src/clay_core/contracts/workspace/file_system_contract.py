from __future__ import annotations

from abc import ABC, abstractmethod


from clay_core.schemas.filesystem import FileStat


class FileSystemContract(ABC):
    """
    Abstract filesystem backend.  Implement this to plug in any storage layer
    (local disk, S3, GCS, in-memory, etc.) and pass an instance to WorkspaceConfig.
    """

    async def setup(self) -> None:
        """Called once by Workspace.setup(). Create directories, open connections, etc."""

    @abstractmethod
    def read_file(self, path: str) -> str: ...

    @abstractmethod
    def write_file(self, path: str, content: str) -> None: ...

    @abstractmethod
    def edit_file(self, path: str, old_string: str, new_string: str) -> None: ...

    @abstractmethod
    def list_directory(self, path: str = ".", pattern: str = "*") -> list[str]: ...

    @abstractmethod
    def delete_file(self, path: str) -> None: ...

    @abstractmethod
    def delete_directory(self, path: str) -> None: ...

    @abstractmethod
    def copy_file(self, src: str, dst: str) -> None: ...

    @abstractmethod
    def move_file(self, src: str, dst: str) -> None: ...

    @abstractmethod
    def mkdir(self, path: str) -> None: ...

    @abstractmethod
    def grep(self, pattern: str, path: str = ".") -> list[str]: ...

    @abstractmethod
    def stat(self, path: str) -> FileStat: ...


__all__ = ["FileSystemContract"]
