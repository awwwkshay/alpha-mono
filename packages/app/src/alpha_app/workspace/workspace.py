from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from litellm.types.llms.openai import (
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
)
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from alpha_app.constants.otel_constants import (
    ERROR_MESSAGE,
    ERROR_TYPE,
    SPAN_WORKSPACE_TOOL,
    WORKSPACE_NAME,
    WORKSPACE_TOOL_CATEGORY,
    WORKSPACE_TOOL_ERROR,
    WORKSPACE_TOOL_SUCCESS,
)

from alpha_app.log import logger

from alpha_core.contracts.workspace.file_system_contract import FileSystemContract
from alpha_core.contracts.workspace.sandbox_contract import SandboxContract
from alpha_app.workspace.file_systems.local_file_system import LocalFileSystem
from alpha_app.workspace.file_systems.s3_file_system import S3FileSystem
from alpha_app.workspace.sandboxes.e2b_sandbox import E2BSandbox
from alpha_app.workspace.sandboxes.local_sandbox import LocalSandbox
from alpha_core.schemas.filesystem_config import (
    LocalFilesystemConfig,
    S3FilesystemConfig,
)
from alpha_core.schemas.sandbox_config import E2BSandboxConfig, LocalSandboxConfig

if TYPE_CHECKING:
    from alpha_core.schemas.workspace_config import WorkspaceConfig


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

_SKILL_INSTRUCTIONS_FILE = "skill.md"


@dataclass
class Skill:
    name: str
    instructions: str
    files: dict[str, Path] = field(default_factory=dict)


def _load_skills(paths: list[Path]) -> list[Skill]:
    skills: list[Skill] = []
    for base in paths:
        if not base.is_dir():
            continue
        for skill_dir in sorted(base.iterdir()):
            if not skill_dir.is_dir():
                continue
            instructions_file = skill_dir / _SKILL_INSTRUCTIONS_FILE
            if not instructions_file.exists():
                continue
            instructions = instructions_file.read_text(encoding="utf-8")
            files = {
                f.name: f
                for f in skill_dir.iterdir()
                if f.is_file() and f.name != _SKILL_INSTRUCTIONS_FILE
            }
            skills.append(
                Skill(name=skill_dir.name, instructions=instructions, files=files)
            )
    return skills


# ---------------------------------------------------------------------------
# Filesystem tool dispatcher (operates on FileSystemContract interface)
# ---------------------------------------------------------------------------

_UNHANDLED = object()


def _dispatch_fs_read_tool(name: str, args: dict, fs: FileSystemContract) -> object:
    if name == "read_file":
        return {"content": fs.read_file(args["path"])}
    if name == "list_directory":
        return {
            "entries": fs.list_directory(
                args.get("path", "."), args.get("pattern", "*")
            )
        }
    if name == "grep":
        return {"matches": fs.grep(args["pattern"], args.get("path", "."))}
    if name == "stat":
        return fs.stat(args["path"])
    return _UNHANDLED


def _dispatch_fs_write_tool(name: str, args: dict, fs: FileSystemContract) -> object:
    if name == "write_file":
        fs.write_file(args["path"], args["content"])
    elif name == "edit_file":
        fs.edit_file(args["path"], args["old_string"], args["new_string"])
    elif name == "delete_file":
        fs.delete_file(args["path"])
    elif name == "delete_directory":
        fs.delete_directory(args["path"])
    elif name == "copy_file":
        fs.copy_file(args["src"], args["dst"])
    elif name == "move_file":
        fs.move_file(args["src"], args["dst"])
    elif name == "mkdir":
        fs.mkdir(args["path"])
    else:
        return _UNHANDLED
    return {"ok": True}


def _dispatch_fs_tool(name: str, args: dict, fs: FileSystemContract) -> object:
    result = _dispatch_fs_read_tool(name, args, fs)
    if result is not _UNHANDLED:
        return result
    return _dispatch_fs_write_tool(name, args, fs)


# ---------------------------------------------------------------------------
# Tool schema helpers
# ---------------------------------------------------------------------------


def _tool(
    name: str, description: str, properties: dict, required: list[str]
) -> ChatCompletionToolParam:
    return ChatCompletionToolParam(
        type="function",
        function=ChatCompletionToolParamFunctionChunk(
            name=name,
            description=description,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
            },
        ),
    )


_FS_TOOLS: list[ChatCompletionToolParam] = [
    _tool(
        "read_file",
        "Read the full text content of a file inside the workspace.",
        {"path": {"type": "string", "description": "Relative path to the file"}},
        ["path"],
    ),
    _tool(
        "write_file",
        "Create or overwrite a file inside the workspace.",
        {
            "path": {"type": "string", "description": "Relative path to the file"},
            "content": {"type": "string", "description": "Text content to write"},
        },
        ["path", "content"],
    ),
    _tool(
        "edit_file",
        "Replace the first occurrence of old_string with new_string in a file.",
        {
            "path": {"type": "string"},
            "old_string": {"type": "string", "description": "Exact text to replace"},
            "new_string": {"type": "string", "description": "Replacement text"},
        },
        ["path", "old_string", "new_string"],
    ),
    _tool(
        "list_directory",
        "List entries in a workspace directory.",
        {
            "path": {
                "type": "string",
                "description": "Relative path; defaults to root",
                "default": ".",
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern to filter names",
                "default": "*",
            },
        },
        [],
    ),
    _tool(
        "delete_file",
        "Delete a file from the workspace.",
        {"path": {"type": "string"}},
        ["path"],
    ),
    _tool(
        "delete_directory",
        "Recursively delete a directory and all its contents.",
        {"path": {"type": "string"}},
        ["path"],
    ),
    _tool(
        "copy_file",
        "Copy a file to a new location inside the workspace.",
        {
            "src": {"type": "string", "description": "Source path"},
            "dst": {"type": "string", "description": "Destination path"},
        },
        ["src", "dst"],
    ),
    _tool(
        "move_file",
        "Move or rename a file inside the workspace.",
        {
            "src": {"type": "string", "description": "Source path"},
            "dst": {"type": "string", "description": "Destination path"},
        },
        ["src", "dst"],
    ),
    _tool(
        "mkdir",
        "Create a directory (and any missing parents) inside the workspace.",
        {"path": {"type": "string"}},
        ["path"],
    ),
    _tool(
        "grep",
        "Search for a regex pattern across files in the workspace.",
        {
            "pattern": {"type": "string", "description": "Python regex pattern"},
            "path": {
                "type": "string",
                "description": "File or directory to search; defaults to root",
                "default": ".",
            },
        },
        ["pattern"],
    ),
    _tool(
        "stat",
        "Return metadata (size, mtime, type) for a workspace path.",
        {"path": {"type": "string"}},
        ["path"],
    ),
]

_SANDBOX_TOOLS: list[ChatCompletionToolParam] = [
    _tool(
        "execute_command",
        (
            "Run a shell command. "
            "Set background=true to spawn a long-running process and get its PID "
            "immediately; omit or set false to wait for completion."
        ),
        {
            "command": {"type": "string", "description": "Shell command to execute"},
            "background": {
                "type": "boolean",
                "description": "Spawn without waiting and return the PID",
                "default": False,
            },
        },
        ["command"],
    ),
    _tool(
        "get_process_output",
        "Retrieve accumulated stdout/stderr from a background process.",
        {
            "pid": {"type": "integer", "description": "PID from execute_command"},
            "tail": {
                "type": "integer",
                "description": "Return only the last N lines (omit for all output)",
            },
            "wait": {
                "type": "boolean",
                "description": "Block until the process exits before returning",
                "default": False,
            },
        },
        ["pid"],
    ),
    _tool(
        "kill_process",
        "Kill a foreground or background process by its PID.",
        {"pid": {"type": "integer", "description": "Process ID to kill"}},
        ["pid"],
    ),
]

_SKILL_TOOLS: list[ChatCompletionToolParam] = [
    _tool(
        "read_skill_file",
        "Read a non-instructions file that belongs to a named skill.",
        {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill directory",
            },
            "filename": {
                "type": "string",
                "description": "Name of the file inside the skill directory",
            },
        },
        ["skill_name", "filename"],
    ),
]


# ---------------------------------------------------------------------------
# Provider factories — build runtime instances from Pydantic config models
# ---------------------------------------------------------------------------


def _build_filesystem(
    config: LocalFilesystemConfig | S3FilesystemConfig,
) -> FileSystemContract:
    if isinstance(config, LocalFilesystemConfig):
        return LocalFileSystem(
            base_path=config.base_path,
            contained=config.contained,
            read_only=config.read_only,
            allowed_paths=config.allowed_paths or None,
        )
    return S3FileSystem(
        bucket=config.bucket,
        prefix=config.prefix,
        region=config.region,
        read_only=config.read_only,
    )


def _build_sandbox(config: LocalSandboxConfig | E2BSandboxConfig) -> SandboxContract:
    if isinstance(config, LocalSandboxConfig):
        return LocalSandbox(
            working_directory=config.working_directory,
            env=config.env or None,
            timeout=config.timeout,
            isolation=config.isolation,
        )
    return E2BSandbox(
        template=config.template,
        api_key=config.api_key,
        timeout=config.timeout,
    )


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


_tracer = trace.get_tracer(__name__)

_TOOL_CATEGORIES: dict[str, str] = {
    "read_file": "filesystem",
    "write_file": "filesystem",
    "edit_file": "filesystem",
    "list_directory": "filesystem",
    "delete_file": "filesystem",
    "delete_directory": "filesystem",
    "copy_file": "filesystem",
    "move_file": "filesystem",
    "mkdir": "filesystem",
    "grep": "filesystem",
    "stat": "filesystem",
    "execute_command": "sandbox",
    "get_process_output": "sandbox",
    "kill_process": "sandbox",
    "read_skill_file": "skill",
}


class Workspace:
    def __init__(self, config: WorkspaceConfig) -> None:
        self.config = config
        self._fs: FileSystemContract | None = None
        self._sandbox: SandboxContract | None = None
        self._skills: list[Skill] = []
        self._fs_lock = asyncio.Lock()

    async def setup(self) -> None:
        if self.config.filesystem is not None:
            self._fs = _build_filesystem(self.config.filesystem)
            await self._fs.setup()
        if self.config.sandbox is not None:
            self._sandbox = _build_sandbox(self.config.sandbox)
            await self._sandbox.setup()
        if self.config.skills is not None:
            self._skills = _load_skills(self.config.skills.paths)

    async def teardown(self) -> None:
        if self._sandbox is not None:
            await self._sandbox.teardown()

    def get_tools(self) -> list[ChatCompletionToolParam]:
        tools: list[ChatCompletionToolParam] = []
        if self._fs is not None:
            tools.extend(_FS_TOOLS)
        if self._sandbox is not None:
            tools.extend(_SANDBOX_TOOLS)
        if self._skills:
            tools.extend(_SKILL_TOOLS)
        return tools

    async def execute_tool(self, name: str, arguments: dict) -> str:
        logger.debug(f"Workspace executing tool '{name}'")
        category = _TOOL_CATEGORIES.get(name, "unknown")
        with _tracer.start_as_current_span(
            f"{SPAN_WORKSPACE_TOOL}/{name}",
            attributes={
                WORKSPACE_NAME: self.config.name,
                WORKSPACE_TOOL_CATEGORY: category,
                "tool.name": name,
            },
        ) as span:
            try:
                result: Any = await self._dispatch(name, arguments)
                if isinstance(result, BaseModel):
                    result = result.model_dump()
                span.set_attribute(WORKSPACE_TOOL_SUCCESS, True)
            except PermissionError:
                raise
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.set_attribute(WORKSPACE_TOOL_SUCCESS, False)
                span.set_attribute(WORKSPACE_TOOL_ERROR, str(exc))
                span.set_attribute(ERROR_TYPE, type(exc).__name__)
                span.set_attribute(ERROR_MESSAGE, str(exc))
                result = {"error": str(exc)}
            return json.dumps(result)

    async def _dispatch(self, name: str, args: dict) -> object:
        if self._fs is not None:
            async with self._fs_lock:
                result = await asyncio.to_thread(_dispatch_fs_tool, name, args, self._fs)
            if result is not _UNHANDLED:
                return result
        if self._sandbox is not None:
            if name == "execute_command":
                return await self._sandbox.execute_command(
                    args["command"],
                    background=bool(args.get("background", False)),
                )
            if name == "get_process_output":
                return await self._sandbox.get_process_output(
                    int(args["pid"]),
                    tail=args.get("tail"),
                    wait=bool(args.get("wait", False)),
                )
            if name == "kill_process":
                await self._sandbox.kill_process(int(args["pid"]))
                return {"ok": True}
        if name == "read_skill_file":
            return {
                "content": self._read_skill_file(args["skill_name"], args["filename"])
            }
        raise ValueError(f"Unknown or unavailable tool: {name!r}")

    def _read_skill_file(self, skill_name: str, filename: str) -> str:
        for skill in self._skills:
            if skill.name == skill_name:
                if filename not in skill.files:
                    raise FileNotFoundError(
                        f"File '{filename}' not found in skill '{skill_name}'"
                    )
                return skill.files[filename].read_text(encoding="utf-8")
        raise FileNotFoundError(f"Skill '{skill_name}' not found")

    def get_system_prompt_additions(self) -> str:
        parts: list[str] = []
        if self.config.description:
            parts.append(f"Workspace: {self.config.description}")
        for skill in self._skills:
            parts.append(f"## Skill: {skill.name}\n{skill.instructions}")
        return "\n\n".join(parts)


__all__ = [
    "Skill",
    "Workspace",
]
