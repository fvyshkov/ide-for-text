import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import FileTree from './components/FileTree';
import FileEditor from './components/FileEditor';
import { FileTreeItem, FileContent } from './types';

const API_BASE_URL = 'http://localhost:8001';

function App() {
  const [fileTree, setFileTree] = useState<FileTreeItem[]>([]);
  const [rootPath, setRootPath] = useState<string>('');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<FileContent | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setWebsocket(ws);
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'file_updated' && message.path === selectedFile) {
        // File was updated externally, refresh content
        if (message.sender !== 'frontend') {
          loadFileContent(message.path);
        }
      } else if (message.type === 'file_changed') {
        // File system change detected, might need to refresh tree
        if (message.path.startsWith(rootPath)) {
          // File in current directory changed
          console.log('File changed:', message.path);
        }
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWebsocket(null);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return () => {
      ws.close();
    };
  }, [selectedFile, rootPath]);

  const openDirectory = async () => {
    // For now, we'll use a file input to select directory
    // In production, you might want to use Electron or a different approach
    const directoryPath = prompt('Enter directory path:');
    if (!directoryPath) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/open-directory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: directoryPath }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setFileTree(data.tree);
      setRootPath(data.root_path);
    } catch (error) {
      console.error('Error opening directory:', error);
      alert('Error opening directory. Please check the path and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const refreshFileTree = async () => {
    if (!rootPath) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/open-directory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: rootPath }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setFileTree(data.tree);
    } catch (error) {
      console.error('Error refreshing file tree:', error);
      alert('Error refreshing file tree.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadFileContent = async (filePath: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/file-content?path=${encodeURIComponent(filePath)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const content: FileContent = await response.json();
      setFileContent(content);
    } catch (error) {
      console.error('Error loading file content:', error);
      alert('Error loading file content.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = useCallback((filePath: string) => {
    setSelectedFile(filePath);
    loadFileContent(filePath);
  }, []);

  const handleFileContentChange = async (newContent: string) => {
    if (!selectedFile) return;

    try {
      // Save to backend
      const response = await fetch(`${API_BASE_URL}/api/write-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          path: selectedFile,
          content: newContent,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Update local state
      setFileContent(prev => prev ? { ...prev, content: newContent } : null);

      // Notify WebSocket
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({
          type: 'file_update',
          path: selectedFile,
          content: newContent,
          sender: 'frontend'
        }));
      }
    } catch (error) {
      console.error('Error saving file:', error);
      alert('Error saving file.');
    }
  };

  return (
    <div className="App">
      <div className="app-header">
        <h1>Text IDE</h1>
        <div className="header-info">
          {rootPath && <span>Root: {rootPath}</span>}
          {selectedFile && <span>Selected: {selectedFile}</span>}
        </div>
      </div>
      
      <div className="app-content">
        <div className="left-panel">
          <div className="file-tree-header">
            <button onClick={openDirectory} disabled={isLoading}>
              Open Directory
            </button>
            <button onClick={refreshFileTree} disabled={isLoading || !rootPath}>
              Refresh
            </button>
          </div>
          
          <FileTree
            items={fileTree}
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
          />
        </div>
        
        <div className="right-panel">
          <FileEditor
            fileContent={fileContent}
            onContentChange={handleFileContentChange}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

export default App;