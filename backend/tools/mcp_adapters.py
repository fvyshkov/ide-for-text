from __future__ import annotations

import os
from typing import Optional
from langchain.tools import BaseTool
from pydantic import ConfigDict
from typing import Any
from ..mcp_client import MCPClient


class MCPListDirectoryTool(BaseTool):
    name: str = "fs_list_directory"
    description: str = "List files and directories under a path (absolute)."
    client: MCPClient
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, client: MCPClient):
        super().__init__(client=client)

    def _run(self, path: Optional[str] = None) -> str:
        resp = self.client.fs_list_directory(path)
        if not resp.ok:
            return f"Error: {resp.error}"
        items = resp.result["items"]
        lines = []
        for it in items:
            tag = "[DIR]" if it["is_dir"] else "[FILE]"
            lines.append(f"{tag} {it['name']} ({it['size']} bytes)")
        return f"Contents of '{resp.result['path']}':\n" + ("\n".join(lines) if lines else "Empty")


class MCPReadFileTool(BaseTool):
    name: str = "fs_read_file"
    description: str = "Read a file (absolute path). Returns text or base64 if binary."
    client: MCPClient
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, client: MCPClient):
        super().__init__(client=client)

    def _run(self, path: str) -> str:
        resp = self.client.fs_read_file(path)
        if not resp.ok:
            return f"Error: {resp.error}"
        if resp.result.get("text") is not None:
            return resp.result["text"]
        return f"[BASE64_CONTENT]\n{resp.result.get('contentBase64','')}"


class MCPWriteFileTool(BaseTool):
    name: str = "fs_write_file"
    description: str = "Write text content to a file (absolute path)."
    client: MCPClient
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, client: MCPClient):
        super().__init__(client=client)

    def _run(self, args: str) -> str:
        import json
        try:
            data = json.loads(args)
            path = data.get("path")
            text = data.get("text", "")
        except Exception:
            return "Error: expected JSON with {path, text}"
        resp = self.client.fs_write_file(path, text=text)
        return "OK" if resp.ok else f"Error: {resp.error}"


class MCPRunPythonTool(BaseTool):
    name: str = "exec_run_python"
    description: str = "Execute Python code in a sandboxed process with limited time. Returns stdout/stderr and output paths."
    client: MCPClient
    workdir_provider: Any
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, client: MCPClient, workdir_provider=lambda: os.getcwd()):
        super().__init__(client=client, workdir_provider=workdir_provider)

    def _run(self, code: str) -> str:
        resp = self.client.exec_run_python(code, workdir=self.workdir_provider())
        if not resp.ok:
            return f"Error: {resp.error}"
        r = resp.result
        out = r.get("stdout", "")
        err = r.get("stderr", "")
        outputs = r.get("outputs", [])
        return f"STDOUT:\n{out}\nSTDERR:\n{err}\nOUTPUTS:\n" + "\n".join(outputs)


class MCPDataToolShim(BaseTool):
    """Shim that provides 'data_tool' operations (list/read/analyze/write) via MCP client.
    Input format: 'operation arguments'
    - list <dir>
    - read <path>
    - analyze <path>
    - write {"path": "...", "content": "..."}
    """
    name: str = "data_tool"
    description: str = "Shim over MCP tools: supports 'list <dir>', 'read <path>', 'analyze <path>', 'write {json}'."
    client: MCPClient
    base_dir_provider: Any
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, input_str: str) -> str:
        import json as _json
        import os as _os
        import pandas as _pd
        parts = input_str.split(" ", 1)
        if len(parts) != 2:
            return "Error: Invalid input format. Expected 'operation arguments'"
        operation = parts[0].strip()
        arguments = (parts[1] or '').strip()
        base_dir = self.base_dir_provider()
        if operation == "list":
            path = arguments if arguments else base_dir
            resp = self.client.fs_list_directory(path)
            if not resp.ok:
                return f"Error: {resp.error}"
            items = resp.result.get("items", [])
            lines = []
            for it in items:
                tag = "[DIR]" if it.get("is_dir") else "[FILE]"
                size = it.get("size", 0)
                lines.append(f"{tag} {it.get('name')} ({size} bytes)")
            return f"Contents of '{resp.result.get('path', path)}':\n" + ("\n".join(lines) if lines else "No items found")
        if operation == "write":
            try:
                write_args = _json.loads(arguments)
                file_path = write_args.get('path')
                content = write_args.get('content', '')
            except Exception:
                return "Error: Write arguments must be JSON with 'path' and 'content'"
            if not file_path:
                return "Error: No file path provided"
            if not _os.path.isabs(file_path):
                file_path = _os.path.join(base_dir, file_path)
            resp = self.client.fs_write_file(file_path, text=content)
            return "OK" if resp.ok else f"Error: {resp.error}"
        if operation == "read":
            file_path = arguments
            if not _os.path.isabs(file_path):
                file_path = _os.path.join(base_dir, file_path)
            if not _os.path.exists(file_path):
                return f"Error: File '{file_path}' not found"
            if file_path.endswith(('.xlsx', '.xls')):
                df = _pd.read_excel(file_path)
                return f"Excel file with {len(df)} rows, columns: {list(df.columns)}\n\nFirst 5 rows:\n{df.head().to_string()}"
            elif file_path.endswith('.csv'):
                df = _pd.read_csv(file_path)
                return f"CSV file with {len(df)} rows, columns: {list(df.columns)}\n\nFirst 5 rows:\n{df.head().to_string()}"
            elif file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = _json.load(f)
                return f"JSON content:\n{_json.dumps(data, indent=2)[:1000]}"
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"File content:\n{content}"
        if operation == "analyze":
            file_path = arguments
            if not _os.path.isabs(file_path):
                file_path = _os.path.join(base_dir, file_path)
            if not _os.path.exists(file_path):
                return f"Error: File '{file_path}' not found"
            stat = os.stat(file_path)
            info = [
                f"Path: {file_path}",
                f"Size: {stat.st_size} bytes",
                f"Type: {'Directory' if os.path.isdir(file_path) else 'File'}",
                f"Modified: {time.ctime(stat.st_mtime)}"
            ]
            if file_path.endswith(('.xlsx', '.xls', '.csv')):
                try:
                    df = _pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else _pd.read_csv(file_path)
                    info.extend([
                        f"Rows: {len(df)}",
                        f"Columns: {list(df.columns)}",
                        f"Data types: {df.dtypes.to_dict()}",
                        f"Missing values: {df.isnull().sum().to_dict()}"
                    ])
                except Exception:
                    pass
            return "\n".join(info)
        return f"Unknown operation: {operation}"

