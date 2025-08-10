"""Minimal in-process MCP client that calls MCPServer methods directly (MVP).
Later can be replaced by stdio/WebSocket transport.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from .mcp_server import MCPServer, MCPResponse, get_default_server


class MCPClient:
    def __init__(self, server: Optional[MCPServer] = None, project_root: Optional[str] = None):
        self.server = server or get_default_server(project_root)

    # Generic request
    def request(self, tool_name: str, args: Dict[str, Any]) -> MCPResponse:
        if not hasattr(self.server, tool_name):
            return MCPResponse(False, error=f"Tool not found: {tool_name}")
        fn = getattr(self.server, tool_name)
        return fn(**args)

    # Helpers
    def fs_list_directory(self, path: Optional[str] = None) -> MCPResponse:
        return self.server.fs_list_directory(path)

    def fs_read_file(self, path: str, max_bytes: Optional[int] = None) -> MCPResponse:
        return self.server.fs_read_file(path, max_bytes)

    def fs_write_file(self, path: str, text: Optional[str] = None, content_base64: Optional[str] = None) -> MCPResponse:
        return self.server.fs_write_file(path, text, content_base64)

    def fs_search_files(self, query: str, root: Optional[str] = None) -> MCPResponse:
        return self.server.fs_search_files(query, root)

    def exec_run_python(self, code: str, workdir: Optional[str] = None, timeout_sec: int = 15) -> MCPResponse:
        return self.server.exec_run_python(code, workdir, timeout_sec)


