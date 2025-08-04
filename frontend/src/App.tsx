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

  // Define functions first to avoid hoisting issues
  const loadFileContent = useCallback(async (filePath: string) => {
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
  }, []);

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
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: any) => {
    console.log('📨 Received WebSocket message:', message);
    
    if (message.type === 'file_changed') {
      // External file system change detected
      console.log('📁 File system change:', message.path);
      
      if (rootPath && message.path && message.path.startsWith(rootPath)) {
        // Refresh file tree if change is in our current directory
        console.log('🔄 Refreshing file tree due to external change');
        loadDirectory(rootPath);
      }
      
      // If the changed file is currently open, ask user if they want to reload
      if (selectedFile && message.path === selectedFile) {
        const shouldReload = window.confirm(
          `File "${selectedFile}" was modified externally. Do you want to reload it? (This will discard unsaved changes)`
        );
        if (shouldReload) {
          loadFileContent(selectedFile);
        }
      }
    } else if (message.type === 'file_updated') {
      // File was updated by another client/tab
      console.log('🔄 File updated by another client:', message.path);
      
      // Only reload if it's our currently selected file and not sent by us
      if (selectedFile && message.path === selectedFile && message.sender !== 'this-tab') {
        console.log('↻ Reloading file content from another tab update');
        loadFileContent(selectedFile);
      }
    }
  }, [selectedFile, rootPath, loadDirectory, loadFileContent]);

  // WebSocket connection for live updates
  const { sendMessage } = useWebSocket({
    url: 'ws://localhost:8001/ws',
    onMessage: handleWebSocketMessage,
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    enabled: true
  });

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

  const handleFileSelect = useCallback((filePath: string) => {
    setSelectedFile(filePath);
    loadFileContent(filePath);
  }, [loadFileContent]);

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

      // Notify other tabs/clients about file update
      sendMessage({
        type: 'file_updated',
        path: selectedFile,
        content: newContent,
        sender: 'this-tab'
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