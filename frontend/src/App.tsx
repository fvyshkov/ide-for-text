import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import FileTree from './components/FileTree';
import FileEditor from './components/FileEditor';
import ResizableSplitter from './components/ResizableSplitter';
import { FileTreeItem, FileContent } from './types';
import { useTheme } from './contexts/ThemeContext';
// Native directory picker functionality
import { FaSun, FaMoon, FaFolder, FaSync } from 'react-icons/fa';

const API_BASE_URL = 'http://localhost:8001';

function App() {
  const { theme, toggleTheme } = useTheme();
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
    try {
      // Use backend system folder picker for reliable full path
      const response = await fetch(`${API_BASE_URL}/api/pick-directory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.path) {
          await loadDirectory(data.path);
        }
        // If user cancelled, data.success will be false - do nothing
      } else {
        alert('Directory picker not available');
      }
    } catch (error) {
      console.error('Directory picker error:', error);
      alert('Error opening directory picker');
    }
  };

  const loadDirectory = async (directoryPath: string) => {
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
      alert(`Error opening directory "${directoryPath}". Make sure the directory exists.`);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshFileTree = async () => {
    if (!rootPath) return;
    await loadDirectory(rootPath);
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

  const leftPanel = (
    <div className="left-panel">
      <div className="file-tree-header">
        <div className="toolbar-buttons">
          <button 
            className="toolbar-btn"
            onClick={openDirectory} 
            disabled={isLoading}
            title="Open folder"
          >
            <FaFolder />
          </button>
          <button 
            className="toolbar-btn"
            onClick={refreshFileTree} 
            disabled={isLoading || !rootPath}
            title="Refresh"
          >
            <FaSync />
          </button>
        </div>
      </div>
      
      <FileTree
        items={fileTree}
        onFileSelect={handleFileSelect}
        selectedFile={selectedFile}
      />
    </div>
  );

  const rightPanel = (
    <div className="right-panel">
      <FileEditor
        fileContent={fileContent}
        onContentChange={handleFileContentChange}
        isLoading={isLoading}
      />
    </div>
  );

  return (
    <div className="App">
      <div className="app-header">
        <div className="header-left">
          <h1>Text IDE</h1>
          {rootPath && (
            <div className="current-directory">
              <span className="directory-label">Directory:</span>
              <span className="directory-path" title={rootPath}>{rootPath}</span>
            </div>
          )}
        </div>
        
        <div className="header-right">
          {selectedFile && (
            <div className="selected-file">
              <span className="file-label">File:</span>
              <span className="file-path" title={selectedFile}>
                {selectedFile.split('/').pop()}
              </span>
            </div>
          )}
          
          <button 
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          >
            {theme === 'light' ? <FaMoon /> : <FaSun />}
          </button>
        </div>
      </div>
      
      <div className="app-content">
        <ResizableSplitter
          leftPanel={leftPanel}
          rightPanel={rightPanel}
          defaultLeftWidth={300}
          minLeftWidth={200}
          maxLeftWidth={600}
        />
      </div>
    </div>
  );
}

export default App;