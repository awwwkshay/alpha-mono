from __future__ import annotations

import fnmatch
import os
import re
import shutil
from pathlib import Path

from alpha_core.contracts.workspace.file_system_contract import FileSystemContract


class LocalFileSystem(FileSystemContract):
    """
    Disk-backed filesystem.

    Args:
        base_path:     Root directory for all relative-path operations.
        contained:     When True (default), operations are restricted to
                       `base_path` and any `allowed_paths`.  Absolute and
                       tilde paths are accepted but must still resolve inside
                       an allowed location.  Set to False to disable all
                       path-containment checks.
        allowed_paths: Additional directories outside `base_path` that agents
                       are permitted to access (only meaningful when
                       `contained=True`).
        read_only:     Block all write operations when True.
    """

    def __init__(
        self,
        base_path: Path,
        *,
        contained: bool = True,
        allowed_paths: list[Path] | None = None,
        read_only: bool = False,
    ) -> None:
        self._base = base_path.resolve()
        self._contained = contained
        self._allowed_paths: list[Path] = [p.resolve() for p in (allowed_paths or [])]
        self._read_only = read_only

    async def setup(self) -> None:
        self._base.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path resolution & access control
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        p = Path(path)

        if not self._contained:
            return (self._base / p).resolve() if not p.is_absolute() else p.resolve()

        # Expand tilde
        if path.startswith("~"):
            resolved = Path(os.path.expanduser(path)).resolve()
        elif p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self._base / p).resolve()

        allowed = [self._base, *self._allowed_paths]
        if not any(str(resolved).startswith(str(a)) for a in allowed):
            raise PermissionError(
                f"Path '{path}' is outside allowed locations. "
                f"Allowed: {[str(a) for a in allowed]}"
            )
        return resolved

    def _check_writable(self) -> None:
        if self._read_only:
            raise PermissionError("Workspace filesystem is read-only")

    def set_allowed_paths(self, paths: list[Path]) -> None:
        """Replace the extra allowed paths at runtime."""
        self._allowed_paths = [p.resolve() for p in paths]

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def read_file(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8")

    def list_directory(self, path: str = ".", pattern: str = "*") -> list[str]:
        target = self._resolve(path)
        return [
            str(p.relative_to(self._base)) if p.is_relative_to(self._base) else str(p)
            for p in target.iterdir()
            if fnmatch.fnmatch(p.name, pattern)
        ]

    def grep(self, pattern: str, path: str = ".") -> list[str]:
        target = self._resolve(path)
        results: list[str] = []
        rx = re.compile(pattern)
        files = [target] if target.is_file() else target.rglob("*")
        for file in files:
            if not file.is_file():
                continue
            try:
                for i, line in enumerate(
                    file.read_text(encoding="utf-8", errors="replace").splitlines(),
                    start=1,
                ):
                    if rx.search(line):
                        label = (
                            str(file.relative_to(self._base))
                            if file.is_relative_to(self._base)
                            else str(file)
                        )
                        results.append(f"{label}:{i}: {line}")
            except OSError:
                pass
        return results

    def stat(self, path: str) -> dict:
        target = self._resolve(path)
        s = target.stat()
        display = (
            str(target.relative_to(self._base))
            if target.is_relative_to(self._base)
            else str(target)
        )
        return {
            "path": display,
            "size": s.st_size,
            "mtime": s.st_mtime,
            "is_file": target.is_file(),
            "is_dir": target.is_dir(),
        }

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def write_file(self, path: str, content: str) -> None:
        self._check_writable()
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def edit_file(self, path: str, old_string: str, new_string: str) -> None:
        self._check_writable()
        target = self._resolve(path)
        text = target.read_text(encoding="utf-8")
        if old_string not in text:
            raise ValueError(f"String not found in '{path}': {old_string!r}")
        target.write_text(text.replace(old_string, new_string, 1), encoding="utf-8")

    def delete_file(self, path: str) -> None:
        self._check_writable()
        self._resolve(path).unlink()

    def delete_directory(self, path: str) -> None:
        self._check_writable()
        shutil.rmtree(self._resolve(path))

    def copy_file(self, src: str, dst: str) -> None:
        self._check_writable()
        dst_path = self._resolve(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._resolve(src), dst_path)

    def move_file(self, src: str, dst: str) -> None:
        self._check_writable()
        dst_path = self._resolve(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self._resolve(src)), dst_path)

    def mkdir(self, path: str) -> None:
        self._check_writable()
        self._resolve(path).mkdir(parents=True, exist_ok=True)


__all__ = ["LocalFileSystem"]
