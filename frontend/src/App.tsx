import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import FileTree from './components/FileTree';
import FileEditor from './components/FileEditor';
import ResizableSplitter from './components/ResizableSplitter';
import { FileTreeItem, FileContent } from './types';
import { useTheme } from './contexts/ThemeContext';
import { pickDirectorySimple } from './utils/fileSystemAccess';
import { FaSun, FaMoon, FaFolder } from 'react-icons/fa';

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
    let directoryPath = '';
    try {
      const directoryName = await pickDirectorySimple();
      if (!directoryName) return; // User cancelled

      setIsLoading(true);
      
      // Try relative path first
      directoryPath = `./${directoryName}`;
      
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
      alert(`Error opening directory "${directoryPath}". Make sure the folder exists in the current directory or try again.`);
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

  const leftPanel = (
    <div className="left-panel">
      <div className="file-tree-header">
        <button 
          className="open-directory-btn"
          onClick={openDirectory} 
          disabled={isLoading}
          title="Open Directory"
        >
          <FaFolder />
          <span>Open Directory</span>
        </button>
        <button 
          className="refresh-btn icon-only"
          onClick={refreshFileTree} 
          disabled={isLoading || !rootPath}
          title="Refresh"
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z" />
          </svg>
        </button>
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