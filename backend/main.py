"""
FastAPI backend for text IDE
Provides file system operations, WebSocket support, and AI analysis capabilities
"""
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import aiofiles

# AI Agent import
from ai_agent import get_ai_agent
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

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connected WebSocket clients
websocket_connections: List[WebSocket] = []

class FileTreeItem(BaseModel):
    name: str
    path: str
    is_directory: bool
    children: Optional[List['FileTreeItem']] = None

class FileContent(BaseModel):
    path: str
    content: str
    is_binary: bool

class WriteFileRequest(BaseModel):
    path: str
    content: str

class AIAnalysisRequest(BaseModel):
    query: str
    file_paths: Optional[List[str]] = None
    project_path: Optional[str] = None

class FileWatcher(FileSystemEventHandler):
    """File system watcher for detecting changes on disk"""
    
    def __init__(self):
        self.watched_paths = set()
    
    async def on_modified(self, event):
        if event.is_directory:
            return
        
        # Notify all connected clients about file change
        message = {
            "type": "file_changed",
            "path": event.src_path
        }
        await broadcast_to_websockets(message)
    
    def on_created(self, event):
        asyncio.create_task(self.on_modified(event))
    
    def on_deleted(self, event):
        asyncio.create_task(self.on_modified(event))
    
    def on_moved(self, event):
        asyncio.create_task(self.on_modified(event))

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

async def broadcast_to_websockets(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    if not websocket_connections:
        return
    
    message_str = json.dumps(message)
    disconnected = []
    
    for websocket in websocket_connections:
        try:
            await websocket.send_text(message_str)
        except:
            disconnected.append(websocket)
    
    # Remove disconnected clients
    for ws in disconnected:
        websocket_connections.remove(ws)

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
    """Get file content (text or binary indicator)"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path is a directory")
    
    try:
        if is_text_file(path):
            async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
                content = await f.read()
            return FileContent(path=path, content=content, is_binary=False)
        else:
            return FileContent(path=path, content="[Binary file]", is_binary=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@app.post("/api/write-file")
async def write_file(request: WriteFileRequest):
    """Write content to file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(request.path), exist_ok=True)
        
        async with aiofiles.open(request.path, mode='w', encoding='utf-8') as f:
            await f.write(request.content)
        
        # Notify WebSocket clients about file change
        await broadcast_to_websockets({
            "type": "file_updated",
            "path": request.path,
            "content": request.content
        })
        
        return {"success": True, "message": "File saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

@app.post("/api/pick-directory")
async def pick_directory():
    """Open system folder picker dialog"""
    try:
        if platform.system() == "Darwin":  # macOS
            print("Using macOS folder picker")
            # Use AppleScript for native macOS folder picker
            applescript = '''
            tell application "System Events"
                activate
            end tell
            set selectedFolder to choose folder with prompt "Select Folder"
            return POSIX path of selectedFolder
            '''
            
            print("Running AppleScript...")
            result = subprocess.run([
                'osascript', '-e', applescript
            ], capture_output=True, text=True, timeout=60)
            print("AppleScript result:", result.returncode, result.stdout, result.stderr)
            
            if result.returncode == 0:
                folder_path = result.stdout.strip()
                if folder_path:
                    # Unescape AppleScript path and convert to absolute path
                    folder_path = folder_path.replace('\\ ', ' ')
                    folder_path = os.path.abspath(folder_path)
                    print(f"Selected folder path: {folder_path}")
                    print(f"Path exists: {os.path.exists(folder_path)}")
                    print(f"Is directory: {os.path.isdir(folder_path)}")
                    return {"path": folder_path, "success": True}
                else:
                    return {"path": None, "success": False, "message": "User cancelled"}
            elif result.returncode == 1:
                # User cancelled
                return {"path": None, "success": False, "message": "User cancelled"}
            else:
                raise Exception(f"AppleScript error: {result.stderr}")
                
        elif HAS_TKINTER:
            # Use tkinter for other platforms
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.attributes('-topmost', True)  # Make dialog appear on top
            
            # Open folder picker dialog
            folder_path = filedialog.askdirectory(
                title="Select Folder",
                initialdir=os.getcwd()
            )
            
            # Clean up
            root.destroy()
            
            if folder_path:
                return {"path": folder_path, "success": True}
            else:
                # User cancelled
                return {"path": None, "success": False, "message": "User cancelled"}
        else:
            raise HTTPException(status_code=501, detail="System folder picker not available")
            
    except subprocess.TimeoutExpired:
        return {"path": None, "success": False, "message": "Dialog timeout"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error opening folder picker: {str(e)}")

@app.post("/api/ai/analyze")
async def analyze_with_ai(request: AIAnalysisRequest):
    """
    Analyze user query with AI agent and stream thoughts
    Returns streaming response with real-time AI thinking process
    """
    try:
        agent = get_ai_agent()
        
        async def generate_stream():
            """Generate streaming response"""
            async for thought in agent.analyze(request.query, request.project_path):
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
        agent = get_ai_agent()
        return {"status": "ok", "message": "AI agent initialized successfully"}
    except Exception as e:
        return {"status": "error", "message": f"AI agent error: {str(e)}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time file synchronization"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "file_update":
                # Client updated a file
                file_path = message.get("path")
                content = message.get("content")
                
                if file_path and content is not None:
                    # Save to disk
                    async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
                        await f.write(content)
                    
                    # Broadcast to other clients
                    await broadcast_to_websockets({
                        "type": "file_updated",
                        "path": file_path,
                        "content": content,
                        "sender": id(websocket)  # Don't send back to sender
                    })
    
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    
    print("Starting Text IDE Backend...")
    print("Starting file watcher...")
    
    # Start file watcher
    observer.start()
    
    print("Starting uvicorn server on port 8001...")
    
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
    except KeyboardInterrupt:
        print("Stopping server...")
        observer.stop()
    observer.join()
    print("Server stopped.")