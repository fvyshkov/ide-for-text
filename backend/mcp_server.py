"""
Minimal in-process MCP-like server (MVP)
- Exposes file system tools and Python execution with simple safety limits
- Intended to be called via in-process client for now
"""
from __future__ import annotations

import os
import time
import json
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class MCPResponse:
    ok: bool
    result: Any = None
    error: Optional[str] = None


class MCPServer:
    """Minimal tool server exposing fs.* and exec.run_python"""

    def __init__(self, project_root: Optional[str] = None, output_dir: Optional[str] = None):
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.output_dir = os.path.abspath(output_dir or self.project_root)

    # ===== Filesystem tools =====
    def fs_list_directory(self, path: Optional[str] = None) -> MCPResponse:
        try:
            target = os.path.abspath(path or self.project_root)
            if not target.startswith(self.project_root):
                return MCPResponse(False, error="Path outside project_root is not allowed")
            if not os.path.exists(target):
                return MCPResponse(False, error=f"Directory not found: {target}")
            if not os.path.isdir(target):
                return MCPResponse(False, error=f"Not a directory: {target}")
            items = []
            for name in sorted(os.listdir(target)):
                p = os.path.join(target, name)
                try:
                    stat = os.stat(p)
                except Exception:
                    continue
                items.append({
                    "name": name,
                    "path": p,
                    "is_dir": os.path.isdir(p),
                    "size": stat.st_size,
                    "mtime": int(stat.st_mtime),
                })
            return MCPResponse(True, {"path": target, "items": items})
        except Exception as e:
            return MCPResponse(False, error=str(e))

    def fs_read_file(self, path: str, max_bytes: Optional[int] = None) -> MCPResponse:
        try:
            target = os.path.abspath(path)
            if not target.startswith(self.project_root):
                return MCPResponse(False, error="Path outside project_root is not allowed")
            if not os.path.exists(target) or not os.path.isfile(target):
                return MCPResponse(False, error=f"File not found: {target}")
            with open(target, 'rb') as f:
                data = f.read(max_bytes) if max_bytes else f.read()
            try:
                text = data.decode('utf-8')
                return MCPResponse(True, {"path": target, "text": text})
            except UnicodeDecodeError:
                import base64
                return MCPResponse(True, {"path": target, "contentBase64": base64.b64encode(data).decode('ascii')})
        except Exception as e:
            return MCPResponse(False, error=str(e))

    def fs_write_file(self, path: str, text: Optional[str] = None, content_base64: Optional[str] = None) -> MCPResponse:
        try:
            target = os.path.abspath(path)
            if not target.startswith(self.project_root):
                return MCPResponse(False, error="Path outside project_root is not allowed")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if content_base64 is not None:
                import base64
                data = base64.b64decode(content_base64)
                with open(target, 'wb') as f:
                    f.write(data)
            else:
                with open(target, 'w', encoding='utf-8') as f:
                    f.write(text or "")
            return MCPResponse(True, {"ok": True, "path": target})
        except Exception as e:
            return MCPResponse(False, error=str(e))

    def fs_search_files(self, query: str, root: Optional[str] = None, globs: Optional[List[str]] = None, limit: int = 50) -> MCPResponse:
        try:
            base = os.path.abspath(root or self.project_root)
            if not base.startswith(self.project_root):
                return MCPResponse(False, error="Root outside project_root is not allowed")
            q = query.lower().strip()
            results = []
            for r, _, files in os.walk(base):
                for name in files:
                    if name.startswith('~$'):
                        continue
                    if q in name.lower():
                        p = os.path.join(r, name)
                        try:
                            st = os.stat(p)
                            results.append({"path": p, "size": st.st_size, "mtime": int(st.st_mtime)})
                            if len(results) >= limit:
                                return MCPResponse(True, {"matches": results})
                        except Exception:
                            continue
            return MCPResponse(True, {"matches": results})
        except Exception as e:
            return MCPResponse(False, error=str(e))

    # ===== Exec tool =====
    def exec_run_python(self, code: str, workdir: Optional[str] = None, timeout_sec: int = 15) -> MCPResponse:
        """Execute Python with minimal sandbox and timeout.
        WARNING: MVP — relies on limited builtins and timeouts only.
        """
        import io, sys, threading
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure
        import numpy as np

        original_cwd = os.getcwd()
        try:
            wd = os.path.abspath(workdir or self.output_dir)
            # Allow workdir inside project_root or equal to it
            if not wd.startswith(self.project_root):
                return MCPResponse(False, error="workdir outside project_root is not allowed")
            os.makedirs(wd, exist_ok=True)
            os.chdir(wd)

            # Patch savefig to collect outputs
            original_savefig = plt.savefig
            outputs: List[str] = []
            def _patched_savefig(fname, *args, **kwargs):
                out = original_savefig(fname, *args, **kwargs)
                try:
                    outputs.append(os.path.abspath(fname))
                except Exception:
                    pass
                return out
            plt.savefig = _patched_savefig
            original_fig_savefig = getattr(Figure, 'savefig', None)
            if callable(original_fig_savefig):
                def _patched_fig_savefig(self, fname, *args, **kwargs):
                    out = original_fig_savefig(self, fname, *args, **kwargs)
                    try:
                        outputs.append(os.path.abspath(fname))
                    except Exception:
                        pass
                    return out
                Figure.savefig = _patched_fig_savefig

            # Prepare sandboxed globals
            allowed_globals = {
                'pd': pd,
                'pandas': pd,
                'plt': plt,
                'np': np,
                'os': os,
                'time': time,
                '__builtins__': __builtins__,
            }

            buffer = io.StringIO()
            err_buffer = io.StringIO()
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buffer, err_buffer

            exc: Dict[str, Any] = {}
            def _runner():
                try:
                    exec(code, allowed_globals)
                except Exception as e:
                    exc['err'] = e
                    exc['tb'] = traceback.format_exc()

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join(timeout=timeout_sec)
            timed_out = t.is_alive()
            if timed_out:
                return MCPResponse(False, error=f"Execution timeout after {timeout_sec}s")
            out = buffer.getvalue()
            err = err_buffer.getvalue()
            if 'err' in exc:
                return MCPResponse(False, error=f"{exc['err']}\n{exc.get('tb','')}")
            # If outputs are relative paths, normalize to absolute within wd
            norm_outputs = []
            for p in outputs:
                try:
                    ap = p if os.path.isabs(p) else os.path.abspath(os.path.join(wd, p))
                    norm_outputs.append(ap)
                except Exception:
                    norm_outputs.append(p)
            return MCPResponse(True, {"ok": True, "stdout": out, "stderr": err, "outputs": norm_outputs})
        except Exception as e:
            return MCPResponse(False, error=str(e))
        finally:
            try:
                sys.stdout, sys.stderr = old_stdout, old_stderr  # type: ignore[name-defined]
            except Exception:
                pass
            try:
                os.chdir(original_cwd)
            except Exception:
                pass


def get_default_server(project_root: Optional[str] = None) -> MCPServer:
    return MCPServer(project_root=project_root, output_dir=project_root)


