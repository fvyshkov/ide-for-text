"""
File operation tools for AI agent
"""
import os
import time
import asyncio
import aiofiles
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool


@tool
def read_file_content(file_path: str) -> str:
    """
    Read the content of a text file.
    
    Args:
        file_path: Path to the file to read (relative to project directory)
    
    Returns:
        The content of the file as a string
    """
    try:
        # Ensure path is relative and safe
        if os.path.isabs(file_path):
            return f"Error: Absolute paths not allowed. Use relative path from project directory."
        
        # Get the project root (parent of backend)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        full_path = os.path.join(project_root, file_path)
        
        # Security check - ensure file is within project
        if not os.path.commonpath([project_root, full_path]) == project_root:
            return f"Error: File path outside project directory not allowed."
        
        if not os.path.exists(full_path):
            return f"Error: File '{file_path}' does not exist."
        
        if not os.path.isfile(full_path):
            return f"Error: '{file_path}' is not a file."
        
        # Read file content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"Content of '{file_path}':\n\n{content}"
        
    except Exception as e:
        return f"Error reading file '{file_path}': {str(e)}"


@tool
def write_file_content(file_path: str, content: str) -> str:
    """
    Write content to a text file, creating directories if needed.
    
    Args:
        file_path: Path to the file to write (relative to project directory)
        content: Content to write to the file
    
    Returns:
        Success or error message
    """
    try:
        # Ensure path is relative and safe
        if os.path.isabs(file_path):
            return f"Error: Absolute paths not allowed. Use relative path from project directory."
        
        # Get the project root (parent of backend)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        full_path = os.path.join(project_root, file_path)
        
        # Security check - ensure file is within project
        if not os.path.commonpath([project_root, full_path]) == project_root:
            return f"Error: File path outside project directory not allowed."
        
        # Create directories if they don't exist
        dir_path = os.path.dirname(full_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        # Write file content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully wrote content to '{file_path}'"
        
    except Exception as e:
        return f"Error writing file '{file_path}': {str(e)}"


@tool
def list_files_in_directory(directory_path: str = "") -> str:
    """
    List files and directories in the specified directory.
    
    Args:
        directory_path: Path to directory (relative to project directory, empty for root)
    
    Returns:
        List of files and directories
    """
    try:
        # Get the project root (parent of backend)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        
        if directory_path:
            if os.path.isabs(directory_path):
                return f"Error: Absolute paths not allowed. Use relative path from project directory."
            full_path = os.path.join(project_root, directory_path)
        else:
            full_path = project_root
        
        # Security check - ensure directory is within project
        if not os.path.commonpath([project_root, full_path]) == project_root:
            return f"Error: Directory path outside project directory not allowed."
        
        if not os.path.exists(full_path):
            return f"Error: Directory '{directory_path}' does not exist."
        
        if not os.path.isdir(full_path):
            return f"Error: '{directory_path}' is not a directory."
        
        # List contents
        items = []
        for item in sorted(os.listdir(full_path)):
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                items.append(f"[DIR]  {item}/")
            else:
                file_size = os.path.getsize(item_path)
                items.append(f"[FILE] {item} ({file_size} bytes)")
        
        if not items:
            return f"Directory '{directory_path or 'project root'}' is empty."
        
        return f"Contents of '{directory_path or 'project root'}':\n" + "\n".join(items)
        
    except Exception as e:
        return f"Error listing directory '{directory_path}': {str(e)}"


@tool
def get_file_info(file_path: str) -> str:
    """
    Get information about a file (size, type, exists, etc.).
    
    Args:
        file_path: Path to the file (relative to project directory)
    
    Returns:
        Information about the file
    """
    try:
        # Ensure path is relative and safe
        if os.path.isabs(file_path):
            return f"Error: Absolute paths not allowed. Use relative path from project directory."
        
        # Get the project root (parent of backend)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        full_path = os.path.join(project_root, file_path)
        
        # Security check - ensure file is within project
        if not os.path.commonpath([project_root, full_path]) == project_root:
            return f"Error: File path outside project directory not allowed."
        
        if not os.path.exists(full_path):
            return f"File '{file_path}' does not exist."
        
        # Get file info
        stat = os.stat(full_path)
        info = []
        info.append(f"Path: {file_path}")
        info.append(f"Exists: Yes")
        info.append(f"Type: {'Directory' if os.path.isdir(full_path) else 'File'}")
        info.append(f"Size: {stat.st_size} bytes")
        info.append(f"Modified: {time.ctime(stat.st_mtime)}")
        
        return "\n".join(info)
        
    except Exception as e:
        return f"Error getting file info for '{file_path}': {str(e)}"