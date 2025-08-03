import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import './App.css';
import FileTree from './components/FileTree';
import FileEditor from './components/FileEditor';
import TripleSplitter from './components/TripleSplitter';
import AIChat from './components/AIChat';
import { FileTreeItem, FileContent } from './types';
import { useTheme } from './contexts/ThemeContext';
import { useWebSocket } from './hooks/useWebSocket';
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
  const aiChatRef = useRef<any>(null);

  // Function to ask AI a question
  const askAI = useCallback((question: string) => {
    aiChatRef.current?.askQuestion(question);
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: any) => {
    if (message.type === 'file_updated' && message.path === selectedFile) {
      // File was updated externally, refresh content
      console.log('🔄 WebSocket file update:', {
        path: message.path,
        sender: message.sender,
        senderType: typeof message.sender,
        type: message.type,
        willReload: message.sender !== 'frontend',
        selectedFile: selectedFile
      });
      
      // Only reload if external change (not from our frontend)
      // Skip reload for now to avoid infinite loops
      console.log('⚠️ Skipping WebSocket file reload to avoid loops');
    } else if (message.type === 'file_changed') {
      // File system change detected, might need to refresh tree
      if (message.path.startsWith(rootPath)) {
        // File in current directory changed
        console.log('File changed:', message.path);
      }
    }
  }, [selectedFile, rootPath]);

  // WebSocket connection with auto-reconnect
  const { sendMessage } = useWebSocket({
    url: 'ws://localhost:8001/ws',
    onMessage: handleWebSocketMessage,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5
  });

  const loadDirectory = useCallback(async (directoryPath: string) => {
    console.log('Loading directory:', directoryPath);
    setIsLoading(true);
    
    try {
      console.log('Sending request to open directory:', directoryPath);
      const response = await fetch(`${API_BASE_URL}/api/open-directory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: directoryPath }),
      });
      console.log('Response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setFileTree(data.tree);
      setRootPath(data.root_path);
      
      // Save successfully loaded directory to localStorage
      localStorage.setItem('ide-last-directory', data.root_path);
    } catch (error) {
      console.error('Error opening directory:', error);
      alert(`Error opening directory "${directoryPath}". Make sure the directory exists.`);
    } finally {
      setIsLoading(false);
    }
  }, [setIsLoading, setFileTree, setRootPath]);

  const openDirectory = useCallback(async () => {
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
  }, [loadDirectory]);

  const refreshFileTree = useCallback(async () => {
    if (!rootPath) return;
    await loadDirectory(rootPath);
  }, [rootPath, loadDirectory]);

  // Auto-load directory on startup
  useEffect(() => {
    // Clear any previously saved directory
    localStorage.removeItem('ide-last-directory');

    const initializeDirectory = async () => {
      // Start with test directory
      const directoryToLoad = 'test-directory';
      console.log('Initializing with directory:', directoryToLoad);
      
      try {
        await loadDirectory(directoryToLoad);
      } catch (error) {
        console.warn('Failed to load directory:', directoryToLoad, error);
        try {
          await loadDirectory('.');
        } catch (fallbackError) {
          console.error('Failed to load current directory as fallback:', fallbackError);
        }
      } finally {
        // Make sure isLoading is false even if all attempts fail
        setIsLoading(false);
      }
    };

    initializeDirectory();
  }, [loadDirectory]); // Include loadDirectory in dependencies

  const loadFileContent = async (filePath: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/file-content?path=${encodeURIComponent(filePath)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const content: FileContent = await response.json();
      // File loaded successfully
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

  const handleFileContentChange = useCallback(async (newContent: string) => {
    if (!selectedFile) return;

    // Saving to backend
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

      // Don't update local state - let Monaco manage its own content

      // Notify WebSocket
      // Send update via WebSocket
      sendMessage({
        type: 'file_update',
        path: selectedFile,
        content: newContent,
        sender: 'frontend'
      });
    } catch (error) {
      console.error('Error saving file:', error);
      alert('Error saving file.');
    }
  }, [selectedFile, sendMessage]);



  // Center panel: File editor
  const centerPanel = useMemo(() => (
    <div className="center-panel">
      <FileEditor
        fileContent={fileContent}
        onContentChange={handleFileContentChange}
        isLoading={isLoading}
        onAskAI={askAI}
      />
    </div>
  ), [fileContent, handleFileContentChange, isLoading, askAI]);

  // Left panel: File tree
  const leftPanel = useMemo(() => {
    // Bring openDirectory into scope
    const handleOpenDirectory = openDirectory;
    return (<div className="left-panel">
      <div className="file-tree-header">
        <div className="toolbar-buttons">
          <button 
            className="toolbar-btn"
            onClick={handleOpenDirectory} 
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
  }, [fileTree, handleFileSelect, selectedFile, isLoading, rootPath, refreshFileTree, openDirectory]);

  // Right panel: AI Chat
  const rightPanel = useMemo(() => (
    <div className="right-panel">
      <AIChat 
        ref={aiChatRef}
        currentFile={selectedFile || undefined}
        projectPath={rootPath || undefined}
      />
    </div>
  ), [selectedFile, rootPath]);

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
                {selectedFile}
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
        <TripleSplitter
          leftPanel={leftPanel}
          centerPanel={centerPanel}
          rightPanel={rightPanel}
          defaultLeftWidth={300}
          defaultRightWidth={400}
          minLeftWidth={200}
          maxLeftWidth={600}
          minRightWidth={300}
          maxRightWidth={800}
        />
      </div>
    </div>
  );
}

export default App;