"""
FastAPI backend for text IDE
Provides file system operations, WebSocket support, and AI analysis capabilities
"""
import os
import json
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field, ConfigDict
import aiofiles
import shutil
import pandas as pd
import openpyxl

# AI Agent import - using manager for version switching
from backend.ai_agent_manager import get_ai_agent, clear_session, get_agent_info
# import magic  # Temporarily disabled due to libmagic dependency issues
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# For system folder picker
import subprocess
import platform

try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

app = FastAPI(title="Text IDE Backend", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """Set up event loop for FileWatcher and start watching"""
    global global_event_loop
    global_event_loop = asyncio.get_running_loop()
    file_watcher.loop = global_event_loop
    print(f"Global event loop set for FileWatcher: {global_event_loop}")
    
    # Start file watcher after event loop is set
    print("Starting file watcher...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    test_dir = os.path.join(parent_dir, "test-directory")
    
    if os.path.exists(test_dir):
        print(f"Adding {test_dir} to file watcher")
        observer.schedule(file_watcher, test_dir, recursive=True)
        file_watcher.watched_paths.add(test_dir)
        observer.start()
        print("File watcher started!")
    else:
        print(f"Test directory not found: {test_dir}")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients with timestamps
class WebSocketConnection:
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.last_ping = time.time()

    async def send_ping(self) -> bool:
        try:
            await self.websocket.send_text('{"type": "ping"}')
            self.last_ping = time.time()
            return True
        except:
            return False

    async def close(self):
        try:
            await self.websocket.close()
        except:
            pass

websocket_connections: Dict[str, WebSocketConnection] = {}
MAX_WEBSOCKET_CONNECTIONS = 10  # Increased for multiple tabs

async def broadcast_to_websockets(message: dict, exclude_client: str = None):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        print("No WebSocket connections to broadcast to")
        return
        
    # Don't send file content in broadcast (too much data)
    broadcast_message = {
        "type": message.get("type"),
        "path": message.get("path"),
        "timestamp": message.get("timestamp", time.time()),
        "sender": message.get("sender")
    }
    
    # Count clients excluding the sender
    target_clients = {cid: conn for cid, conn in websocket_connections.items() if cid != exclude_client}
    
    if not target_clients:
        print("No other clients to broadcast to (excluding sender)")
        return
        
    print(f"Broadcasting to {len(target_clients)} clients (excluding {exclude_client}): {broadcast_message}")
    
    # Send to all connections except excluded
    dead_connections = []
    print(f"Iterating over {len(target_clients)} target connections")
    
    # Create a copy to avoid modification during iteration
    connections_copy = list(target_clients.items())
    
    for client_id, conn in connections_copy:
        try:
            print(f"Processing connection {client_id}, type: {type(conn)}")
            if not hasattr(conn, 'websocket'):
                print(f"Connection {client_id} has no websocket attribute")
                dead_connections.append(client_id)
                continue
                
            await conn.websocket.send_text(json.dumps(broadcast_message))
            print(f"Sent to {client_id}")
        except Exception as e:
            print(f"Failed to send to {client_id}: {e}")
            import traceback
            traceback.print_exc()
            dead_connections.append(client_id)
    
    # Clean up dead connections
    for client_id in dead_connections:
        websocket_connections.pop(client_id, None)
        print(f"Removed dead connection: {client_id}")

async def cleanup_old_connections():
    """Remove disconnected connections"""
    global websocket_connections
    current_time = time.time()
    to_remove = []
    
    # Create a copy of items to avoid modification during iteration
    connections_copy = list(websocket_connections.items())
    
    for client_id, conn in connections_copy:
        try:
            # Check if connection still exists and is valid
            if not hasattr(conn, 'websocket') or not hasattr(conn, 'last_ping'):
                print(f"Invalid connection object for {client_id}")
                to_remove.append(client_id)
                continue
                
            # Remove connections that haven't received a ping in 30 seconds
            if current_time - (conn.last_ping or 0) > 30:
                print(f"Connection {client_id} timed out")
                to_remove.append(client_id)
                await conn.close()
            elif not await conn.send_ping():
                print(f"Connection {client_id} is dead")
                to_remove.append(client_id)
        except Exception as e:
            print(f"Error checking connection {client_id}: {e}")
            to_remove.append(client_id)
    
    # Remove dead connections
    for client_id in to_remove:
        websocket_connections.pop(client_id, None)
    
    print(f"Active connections: {len(websocket_connections)}")

class FileTreeItem(BaseModel):
    name: str
    path: str
    is_directory: bool
    children: Optional[List['FileTreeItem']] = None

class FileContent(BaseModel):
    path: str
    content: str
    is_binary: bool

class AIAnalysisRequest(BaseModel):
    query: str
    project_path: Optional[str] = None
    reset_context: bool = False
    file_paths: Optional[List[str]] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "query": "Analyze the contents of this file",
                "project_path": "/path/to/project",
                "reset_context": False
            }
        }
    )

class FileWriteRequest(BaseModel):
    path: str
    content: str

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "path": "/path/to/file.txt",
                "content": "New file content"
            }
        }
    )

class FileReadRequest(BaseModel):
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "path": "/path/to/file.txt",
                "start_line": 1,
                "end_line": 10
            }
        }
    )

class FileWatcher(FileSystemEventHandler):
    """File system watcher for detecting changes on disk"""
    
    def __init__(self):
        self.watched_paths = set()
        self.last_event_time = {}  # To prevent duplicate events  
        self.recently_saved_by_web = {}  # Track files saved by web app
        self.loop = None  # Will be set when event loop is available
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Ignore if this file was recently saved by web app
        if self.is_recently_web_saved(file_path):
            print(f"Ignoring FileWatcher event for web-saved file: {file_path}")
            return
            
        # Prevent duplicate events (filesystem can fire multiple events for one change)
        current_time = time.time()
        if file_path in self.last_event_time:
            if current_time - self.last_event_time[file_path] < 0.5:  # 500ms debounce
                return
        
        self.last_event_time[file_path] = current_time
        
        print(f"External file change detected: {file_path}")
        
        # Notify all connected clients about external file change
        message = {
            "type": "file_changed",
            "path": file_path,
            "timestamp": current_time,
            "source": "external"  # Mark as external change
        }
        
        # Schedule the coroutine in the main event loop
        # FileWatcher runs in a separate thread, so we need to use the global event loop
        if global_event_loop and not global_event_loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(broadcast_to_websockets(message), global_event_loop)
                print("File change broadcasted successfully via global event loop")
            except Exception as e:
                print(f"Error broadcasting file change: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"No event loop available for broadcasting (global_event_loop: {global_event_loop})")
    
    def on_created(self, event):
        if not event.is_directory:
            self.on_modified(event)
    
    def on_deleted(self, event):
        if not event.is_directory:
            # For deleted files, always notify (no web app involvement in deletion)
            print(f"File deleted externally: {event.src_path}")
            message = {
                "type": "file_deleted", 
                "path": event.src_path,
                "timestamp": time.time(),
                "source": "external"
            }
            # Schedule the coroutine in the main event loop
            # FileWatcher runs in a separate thread, so we need to use the global event loop
            if global_event_loop and not global_event_loop.is_closed():
                try:
                    asyncio.run_coroutine_threadsafe(broadcast_to_websockets(message), global_event_loop)
                    print("File deletion broadcasted via global event loop")
                except Exception as e:
                    print(f"Error broadcasting file deletion: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"No event loop available for broadcasting deletion (global_event_loop: {global_event_loop})")
    
    def on_moved(self, event):
        if not event.is_directory:
            self.on_modified(event)
    
    def mark_as_web_saved(self, file_path: str):
        """Mark file as recently saved by web app to ignore next FileWatcher event"""
        current_time = time.time()
        self.recently_saved_by_web[file_path] = current_time
        print(f"Marked as web-saved: {file_path}")
    
    def is_recently_web_saved(self, file_path: str) -> bool:
        """Check if file was recently saved by web app (within 2 seconds)"""
        if file_path not in self.recently_saved_by_web:
            return False
        
        current_time = time.time()
        save_time = self.recently_saved_by_web[file_path]
        
        # Clean up old entries (older than 5 seconds)
        if current_time - save_time > 5.0:
            del self.recently_saved_by_web[file_path]
            return False
        
        # Check if within 2 second window
        return current_time - save_time < 2.0


class BootstrapSampleRequest(BaseModel):
    base_path: str
    sample_name: Optional[str] = "sample-project"
    force: bool = True


@app.post("/api/bootstrap-sample")
async def bootstrap_sample(req: BootstrapSampleRequest):
    """Create a local sample project under base_path/sample_name by copying the repo's test-directory.
    Returns the new root path and its file tree.
    """
    try:
        base_path = os.path.abspath(req.base_path)
        if not os.path.exists(base_path) or not os.path.isdir(base_path):
            raise HTTPException(status_code=400, detail=f"Base path is not a directory: {base_path}")

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        source_sample = os.path.join(project_root, "test-directory")
        if not os.path.exists(source_sample) or not os.path.isdir(source_sample):
            raise HTTPException(status_code=500, detail="Source sample directory not found")

        target_dir = os.path.join(base_path, req.sample_name)

        # Remove target if exists and force requested
        if os.path.exists(target_dir):
            if req.force:
                shutil.rmtree(target_dir, ignore_errors=True)
            else:
                raise HTTPException(status_code=409, detail=f"Target already exists: {target_dir}")

        # Copy with ignore patterns
        shutil.copytree(
            source_sample,
            target_dir,
            ignore=shutil.ignore_patterns("~$*", ".DS_Store", "__pycache__", "*.pyc"),
            dirs_exist_ok=False,
        )

        # Start watching this new directory
        if target_dir not in file_watcher.watched_paths:
            observer.schedule(file_watcher, target_dir, recursive=True)
            file_watcher.watched_paths.add(target_dir)

        tree = build_file_tree(target_dir)
        return {"success": True, "root_path": target_dir, "tree": tree}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bootstrap error: {str(e)}")

# Global event loop for FileWatcher
import threading
import multiprocessing
global_event_loop = None
global_event_loop_lock = threading.Lock()

# Global file watcher
file_watcher = FileWatcher()
observer = Observer()

def is_text_file(file_path: str) -> bool:
    """Check if file is text or binary"""
    # Get file extension
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # Common text file extensions
    text_extensions = {
        '.txt', '.md', '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.htm',
        '.css', '.scss', '.sass', '.json', '.xml', '.yaml', '.yml', '.toml',
        '.ini', '.cfg', '.conf', '.log', '.sql', '.sh', '.bash', '.zsh',
        '.php', '.rb', '.go', '.rs', '.java', '.c', '.cpp', '.h', '.hpp',
        '.cs', '.kt', '.swift', '.m', '.mm', '.vue', '.svelte', '.r', '.R',
        '.dockerfile', '.gitignore', '.gitattributes', '.env', '.editorconfig',
        '.prettierrc', '.eslintrc', '.babelrc', '.npmrc', '.yarnrc'
    }
    
    # Check by extension first
    if file_extension in text_extensions:
        return True
    
    # For files without extension or unknown extensions, try to read as text
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read first 8KB to detect binary content
            chunk = f.read(8192)
            # Check for null bytes which typically indicate binary files
            if '\0' in chunk:
                return False
            return True
    except (UnicodeDecodeError, PermissionError):
        return False

def is_excel_file(file_path: str) -> bool:
    """Check if file is an Excel file"""
    file_extension = os.path.splitext(file_path)[1].lower()
    return file_extension in ['.xlsx', '.xls', '.xlsm', '.xlsb']

def is_csv_file(file_path: str) -> bool:
    """Check if file is a CSV file"""
    file_extension = os.path.splitext(file_path)[1].lower()
    return file_extension == '.csv'

def read_excel_file(file_path: str) -> dict:
    """Read Excel file and convert to JSON format"""
    try:
        # Read Excel file
        excel_file = pd.ExcelFile(file_path)
        sheets_data = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            # Replace NaN with None for JSON serialization
            df = df.where(pd.notnull(df), None)
            # Convert to dict format
            sheets_data[sheet_name] = {
                'columns': df.columns.tolist(),
                'data': df.values.tolist()
            }
        
        return {
            'type': 'excel',
            'sheets': sheets_data,
            'sheet_names': excel_file.sheet_names
        }
    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")

def read_csv_file(file_path: str) -> dict:
    """Read CSV file and convert to JSON format"""
    try:
        # Try to read with different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("Could not decode CSV file with any common encoding")
        
        # Replace NaN with None for JSON serialization
        df = df.where(pd.notnull(df), None)
        
        return {
            'type': 'csv',
            'columns': df.columns.tolist(),
            'data': df.values.tolist()
        }
    except Exception as e:
        raise Exception(f"Error reading CSV file: {str(e)}")

def build_file_tree(directory: str, max_depth: int = 10, current_depth: int = 0) -> List[FileTreeItem]:
    """Build file tree structure from directory"""
    if current_depth >= max_depth:
        return []
    
    items = []
    try:
        for item in sorted(os.listdir(directory)):
            if item.startswith('.'):  # Skip hidden files
                continue
            
            item_path = os.path.join(directory, item)
            is_dir = os.path.isdir(item_path)
            
            tree_item = FileTreeItem(
                name=item,
                path=item_path,
                is_directory=is_dir,
                children=build_file_tree(item_path, max_depth, current_depth + 1) if is_dir else None
            )
            items.append(tree_item)
    except PermissionError:
        pass
    
    return items

from backend.tools.data_analysis import intelligent_data_visualization

@app.post("/api/visualize-data")
async def visualize_data(file_path: str):
    """
    Endpoint for intelligent data visualization
    
    Args:
        file_path (str): Path to the data file
    
    Returns:
        Visualization details or error message
    """
    try:
        result = intelligent_data_visualization(file_path)
        
        if result:
            return {
                "status": "success",
                "chart_path": result['chart_path'],
                "strategy": result.get('strategy', 'Default visualization')
            }
        else:
            return {
                "status": "error",
                "message": "Unable to generate visualization"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Text IDE Backend API"}

class OpenDirectoryRequest(BaseModel):
    path: str

@app.post("/api/open-directory")
async def open_directory(request: OpenDirectoryRequest):
    """Open directory and return file tree"""
    directory_path = request.path
    
    print(f"Opening directory: {directory_path}")
    if not directory_path:
        print("Error: Directory path is empty")
        raise HTTPException(status_code=400, detail="Directory path is empty")
    
    # Handle paths
    if directory_path.startswith('/'):
        # Absolute path
        directory_path = directory_path
    elif directory_path.startswith('./') or directory_path.startswith('../'):
        # Relative path from current directory
        directory_path = os.path.abspath(os.path.join(os.getcwd(), directory_path))
    else:
        # Just path - treat as relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        directory_path = os.path.abspath(os.path.join(project_root, directory_path))
    
    print(f"Absolute path: {directory_path}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Directory exists: {os.path.exists(directory_path)}")
    print(f"Is directory: {os.path.isdir(directory_path)}")
    print(f"Directory contents: {os.listdir(directory_path) if os.path.exists(directory_path) and os.path.isdir(directory_path) else 'N/A'}")
    
    if not os.path.exists(directory_path):
        print(f"Error: Directory does not exist: {directory_path}")
        raise HTTPException(status_code=400, detail=f"Directory does not exist: {directory_path}")
    
    if not os.path.isdir(directory_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")
    
    try:
        # Start watching this directory
        if directory_path not in file_watcher.watched_paths:
            observer.schedule(file_watcher, directory_path, recursive=True)
            file_watcher.watched_paths.add(directory_path)
        
        file_tree = build_file_tree(directory_path)
        return {"tree": file_tree, "root_path": directory_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")

@app.get("/api/file-content")
async def get_file_content(path: str):
    """Get file content (text, Excel, CSV or binary indicator)"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path is a directory")
    
    try:
        # Check if it's an image
        import mimetypes
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type and mime_type.startswith('image/'):
            # Images are returned directly as files
            return FileResponse(path, media_type=mime_type)
            
        # Check if it's an Excel file
        if is_excel_file(path):
            excel_data = read_excel_file(path)
            return {
                "path": path,
                "content": json.dumps(excel_data),
                "is_binary": False,
                "file_type": "excel"
            }
        # Check if it's a CSV file
        elif is_csv_file(path):
            csv_data = read_csv_file(path)
            return {
                "path": path,
                "content": json.dumps(csv_data),
                "is_binary": False,
                "file_type": "csv"
            }
        # Check if it's a text file
        elif is_text_file(path):
            async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
                content = await f.read()
            return FileContent(path=path, content=content, is_binary=False)
        else:
            # Binary file that's not an image
            return {
                "path": path,
                "content": "[Binary file]",
                "is_binary": True
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@app.post("/api/write-file")
async def write_file(request: FileWriteRequest):
    """Write content to file"""
    try:
        print(f"Saving file: {request.path}")
        print(f"Content length: {len(request.content)} characters")
        
        # Get directory path
        dir_path = os.path.dirname(request.path)
        print(f"Directory: {dir_path}")
        
        # Create directory if it doesn't exist (but only if dir_path is not empty)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            print(f"Directory created/exists: {dir_path}")
        
        # Check if this is Excel/CSV data
        try:
            data = json.loads(request.content)
            if isinstance(data, dict) and 'type' in data:
                if data['type'] == 'excel' and 'sheets' in data:
                    # Save as Excel file
                    with pd.ExcelWriter(request.path, engine='openpyxl') as writer:
                        for sheet_name, sheet_data in data['sheets'].items():
                            df = pd.DataFrame(sheet_data['data'], columns=sheet_data['columns'])
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"Excel file saved successfully: {request.path}")
                    file_watcher.mark_as_web_saved(request.path)
                    return {"success": True, "message": "Excel file saved successfully"}
                elif data['type'] == 'csv':
                    # Save as CSV file
                    df = pd.DataFrame(data['data'], columns=data['columns'])
                    df.to_csv(request.path, index=False)
                    print(f"CSV file saved successfully: {request.path}")
                    file_watcher.mark_as_web_saved(request.path)
                    return {"success": True, "message": "CSV file saved successfully"}
        except (json.JSONDecodeError, KeyError):
            # Not JSON or not Excel/CSV data, save as regular text file
            pass
        
        # Write as regular text file
        async with aiofiles.open(request.path, mode='w', encoding='utf-8') as f:
            await f.write(request.content)
        
        print(f"File saved successfully: {request.path}")
        
        # Mark file as saved by web app to prevent FileWatcher false positives
        print(f"Calling mark_as_web_saved for: {request.path}")
        file_watcher.mark_as_web_saved(request.path)
        print(f"mark_as_web_saved completed")
        
        return {"success": True, "message": "File saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

@app.post("/api/pick-directory")
async def pick_directory_api(test_mode: bool = False):
    """Open system folder picker dialog (native), returns selected absolute path.
    test_mode=True will return repository test-directory for convenience.
    """
    print(f"/api/pick-directory called, test_mode={test_mode}")
    if test_mode:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        test_dir = os.path.join(project_root, "test-directory")
        print(f"Returning test directory: {test_dir}")
        return {"path": test_dir, "success": True}
    try:
        # On macOS prefer AppleScript (proved working earlier); otherwise use Tkinter
        if platform.system() == "Darwin":  # macOS AppleScript first
            applescript = '''
            tell application "System Events"
                activate
            end tell
            set selectedFolder to choose folder with prompt "Select Folder"
            return POSIX path of selectedFolder
            '''
            result = subprocess.run(['osascript', '-e', applescript], capture_output=True, text=True, timeout=60)
            print(f"AppleScript exit={result.returncode}, out='{result.stdout.strip()}', err='{result.stderr.strip()}'")
            if result.returncode == 0:
                folder_path = result.stdout.strip()
                if folder_path:
                    folder_path = os.path.abspath(folder_path.replace('\\ ', ' '))
                    print(f"Selected folder: {folder_path}")
                    return {"path": folder_path, "success": True}
                return {"path": None, "success": False, "message": "User cancelled"}
            if result.returncode == 1:
                print("User cancelled folder picker")
                return {"path": None, "success": False, "message": "User cancelled"}
            # If AppleScript fails, try Tkinter as fallback
            if HAS_TKINTER:
                try:
                    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                    folder_path = filedialog.askdirectory(title="Select Folder", initialdir=os.getcwd())
                    root.destroy()
                    if folder_path:
                        print(f"Selected folder (tk fallback): {folder_path}")
                        return {"path": os.path.abspath(folder_path), "success": True}
                    print("User cancelled folder picker (tk)")
                    return {"path": None, "success": False, "message": "User cancelled"}
                except Exception as te:
                    print(f"Tkinter fallback error: {te}")
            raise Exception(result.stderr)

        # Non-macOS platforms: use Tkinter if available
        if HAS_TKINTER:
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            folder_path = filedialog.askdirectory(title="Select Folder", initialdir=os.getcwd())
            root.destroy()
            if folder_path:
                print(f"Selected folder (tk): {folder_path}")
                return {"path": os.path.abspath(folder_path), "success": True}
            return {"path": None, "success": False, "message": "User cancelled"}

        # No picker available
        raise HTTPException(status_code=501, detail="System folder picker not available")
    except subprocess.TimeoutExpired:
        print("Folder picker timeout")
        return {"path": None, "success": False, "message": "Dialog timeout"}
    except Exception as e:
        print(f"Folder picker error: {e}")
        raise HTTPException(status_code=500, detail=f"Error opening folder picker: {str(e)}")

@app.post("/api/open-file")
async def open_file(request: FileReadRequest):
    """
    Open a file using the system's default application.
    
    Args:
        request (FileReadRequest): Request containing file path
    
    Returns:
        dict: Status of file opening operation
    """
    try:
        import subprocess
        import platform
        
        path = request.path
        
        # Normalize path to absolute
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        
        # Platform-specific file opening
        system = platform.system()
        if system == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        elif system == "Windows":
            os.startfile(path)
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", path], check=True)
        
        return {"status": "success", "path": path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/ai/analyze")
async def analyze_with_ai(request: AIAnalysisRequest):
    """
    Analyze user query with AI agent and stream thoughts
    Returns streaming response with real-time AI thinking process
    """
    try:
        # Get session ID from request or use default
        session_id = getattr(request, 'session_id', 'default')
        reset_context = getattr(request, 'reset_context', False)
        
        agent = get_ai_agent(session_id)
        
        async def generate_stream():
            """Generate streaming response"""
            async for thought in agent.analyze(
                request.query,
                request.project_path,
                reset_context,
                request.file_paths,
            ):
                # Format as Server-Sent Events
                data = json.dumps(thought)
                yield f"data: {data}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")

@app.get("/api/ai/test")
async def test_ai():
    """Test AI agent connectivity"""
    try:
        # Explicitly define tool names
        tool_names = ["data_tool", "code_executor"]
        
        return {
            "status": "ok", 
            "message": "AI agent initialized successfully",
            "tool_names": tool_names
        }
    except Exception as e:
        return {"status": "error", "message": f"AI agent error: {str(e)}"}

@app.get("/api/ai/info")
async def get_ai_info():
    """Get information about current AI agent configuration"""
    try:
        from ai_agent_manager import get_agent_info
        agent = get_ai_agent()
        info = get_agent_info()
        info["agent_class"] = type(agent).__name__
        
        # Add library versions for debugging
        try:
            import langchain_anthropic
            info["langchain_anthropic_version"] = getattr(langchain_anthropic, '__version__', 'unknown')
            info["langchain_anthropic_location"] = langchain_anthropic.__file__
        except:
            info["langchain_anthropic_version"] = "import_error"
            
        try:
            import anthropic
            info["anthropic_version"] = getattr(anthropic, '__version__', 'unknown')
        except:
            info["anthropic_version"] = "import_error"
            
        return info
    except Exception as e:
        return {"status": "error", "message": f"AI agent info error: {str(e)}"}

@app.post("/api/ai/clear-context")
async def clear_ai_context(session_id: str = "default"):
    """Clear AI conversation context for a session"""
    try:
        clear_session(session_id)
        return {"status": "ok", "message": f"Context cleared for session: {session_id}"}
    except Exception as e:
        return {"status": "error", "message": f"Error clearing context: {str(e)}"}

@app.post("/api/ai/reset-all")
async def reset_all_sessions():
    """Reset all AI agent sessions"""
    try:
        from ai_agent_manager import _agent_sessions
        session_ids = list(_agent_sessions.keys())
        for session_id in session_ids:
            clear_session(session_id)
        return {"status": "ok", "message": f"Reset {len(session_ids)} sessions", "sessions": session_ids}
    except Exception as e:
        return {"status": "error", "message": f"Error resetting sessions: {str(e)}"}

@app.get("/api/ai/info")
async def get_ai_agent_info():
    """Get information about current AI agent configuration"""
    return get_agent_info()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time file synchronization"""
    print("WebSocket connection attempt...")
    # Generate unique client ID based on remote address and a random component
    client_id = f"{websocket.client.host}:{websocket.client.port}:{id(websocket)}"
    print(f"Client ID: {client_id}")
    
    # Run cleanup before accepting new connection
    await cleanup_old_connections()
    
    # Check if we have room for new connection
    if len(websocket_connections) >= MAX_WEBSOCKET_CONNECTIONS:
        print(f"Rejecting connection from {client_id} - too many connections")
        await websocket.close(code=1008, reason="Too many connections")
        return
    
    # Accept the connection
    print("Accepting WebSocket connection...")
    await websocket.accept()
    print("WebSocket connection accepted!")
    
    # Set global event loop for FileWatcher
    global global_event_loop
    with global_event_loop_lock:
        print(f"Current global_event_loop: {global_event_loop}")
        if global_event_loop is None:
            try:
                global_event_loop = asyncio.get_event_loop()
                print(f"Global event loop set for FileWatcher via WebSocket: {global_event_loop}")
            except Exception as e:
                print(f"Error setting global event loop: {e}")
        else:
            print(f"Global event loop already set for FileWatcher: {global_event_loop}")
    
    # Create new connection object
    conn = WebSocketConnection(websocket, client_id)
    websocket_connections[client_id] = conn
    print(f"New WebSocket connection from {client_id}")
    
    try:
        # Send initial ping
        if not await conn.send_ping():
            print(f"Failed to send initial ping to {client_id}")
            return
            
        while True:
            try:
                # Wait for messages
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "pong":
                    conn.last_ping = time.time()
                    continue
                elif message.get("type") == "sync_tabs":
                    # Simple tab-to-tab synchronization (manual trigger)
                    file_path = message.get("path")
                    if file_path:
                        print(f"🔄 Tab sync request for: {file_path}")
                        await broadcast_to_websockets({
                            "type": "sync_tabs",
                            "path": file_path,
                            "timestamp": time.time()
                        }, exclude_client=client_id)  # Don't send back to sender
                
            except WebSocketDisconnect:
                print(f"WebSocket disconnected: {client_id}")
                break
            except Exception as e:
                print(f"Error processing message from {client_id}: {e}")
                import traceback
                traceback.print_exc()
                break
                
    finally:
        # Clean up on exit
        if client_id in websocket_connections:
            await websocket_connections[client_id].close()
            websocket_connections.pop(client_id, None)
        print(f"Connection closed: {client_id}")
    


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Text IDE Backend...")
    
    print("Starting uvicorn server on port 8001...")
    
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
    except KeyboardInterrupt:
        print("Stopping server...")
        observer.stop()
    observer.join()
    print("Server stopped.")