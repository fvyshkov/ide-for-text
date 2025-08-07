import React, { useRef, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { FileContent } from '../types';
import { useTheme } from '../contexts/ThemeContext';
import ExcelViewer from './ExcelViewer';
import { API_BASE_URL } from '../utils/config';
import './FileEditor.css';
import { FaImage, FaFile } from 'react-icons/fa';

interface FileEditorProps {
  fileContent: FileContent | null;
  onContentChange: (content: string) => void;
  isLoading: boolean;
  onAskAI?: (question: string) => void;
  onUpdateContentRef?: (updateFn: (content: string) => void) => void;
}

const FileEditor: React.FC<FileEditorProps> = ({ fileContent, onContentChange, isLoading, onAskAI, onUpdateContentRef }) => {
  const { theme } = useTheme();
  const editorRef = useRef<any>(null);
  const currentFilePathRef = useRef<string | null>(null);

  // Simple file tracking for reference
  useEffect(() => {
    if (fileContent) {
      currentFilePathRef.current = fileContent.path;
    }
  }, [fileContent]);

  // Get file language based on extension
  const getLanguageFromFileName = (fileName: string): string => {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    switch (ext) {
      case 'js':
      case 'jsx':
        return 'javascript';
      case 'ts':
      case 'tsx':
        return 'typescript';
      case 'py':
        return 'python';
      case 'json':
        return 'json';
      case 'md':
        return 'markdown';
      case 'html':
        return 'html';
      case 'css':
        return 'css';
      case 'xml':
        return 'xml';
      case 'yaml':
      case 'yml':
        return 'yaml';
      default:
        return 'plaintext';
    }
  };

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
    // Monaco is created with correct defaultLanguage and defaultValue
    // No need for manual setup
  };

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      onContentChange(value);
    }
  };

  // Function to update content without losing cursor position
  const updateContentWithoutFocus = (newContent: string) => {
    if (editorRef.current) {
      const editor = editorRef.current;
      const currentPosition = editor.getPosition();
      const currentSelection = editor.getSelection();
      
      // Update the content
      editor.setValue(newContent);
      
      // Restore cursor position and selection if they're still valid
      if (currentPosition) {
        const model = editor.getModel();
        if (model) {
          const lineCount = model.getLineCount();
          const validPosition = {
            lineNumber: Math.min(currentPosition.lineNumber, lineCount),
            column: Math.min(currentPosition.column, model.getLineMaxColumn(Math.min(currentPosition.lineNumber, lineCount)))
          };
          editor.setPosition(validPosition);
          
          if (currentSelection) {
            const validSelection = {
              startLineNumber: Math.min(currentSelection.startLineNumber, lineCount),
              startColumn: Math.min(currentSelection.startColumn, model.getLineMaxColumn(Math.min(currentSelection.startLineNumber, lineCount))),
              endLineNumber: Math.min(currentSelection.endLineNumber, lineCount),
              endColumn: Math.min(currentSelection.endColumn, model.getLineMaxColumn(Math.min(currentSelection.endLineNumber, lineCount)))
            };
            editor.setSelection(validSelection);
          }
        }
      }
    }
  };

  // Provide the update function to parent component
  useEffect(() => {
    if (onUpdateContentRef) {
      onUpdateContentRef(updateContentWithoutFocus);
    }
  }, [onUpdateContentRef]);

  const isImageFile = (fileName: string) => {
    const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'];
    return imageExtensions.some(ext => fileName.toLowerCase().endsWith(ext));
  };

  if (isLoading) {
    return (
      <div className="file-editor loading">
        <div className="loading-spinner">Loading...</div>
      </div>
    );
  }

  if (!fileContent) {
    return (
      <div className="file-editor empty">
        <div className="empty-state">
          <h3>No file selected</h3>
          <p>Select a file from the tree to view and edit its contents.</p>
        </div>
      </div>
    );
  }

  // Get file extension and language
  const fileName = fileContent.path.split('/').pop() || '';
  const language = getLanguageFromFileName(fileName);
  const editorTheme = theme === 'light' ? 'light' : 'vs-dark';

  // Monaco Editor creation

  return (
    <div className="file-editor">
      <div className="file-editor-header">
        <span className="file-name">{fileName}</span>
        <span className="file-path">{fileContent.path}</span>
      </div>
      
      {fileContent && !isLoading && (
        fileContent.file_type === 'excel' || fileContent.file_type === 'csv' ? (
          // Excel/CSV Viewer
          <ExcelViewer
            content={fileContent.content || ''}
            path={fileContent.path}
            onContentChange={onContentChange}
            readOnly={false}
          />
        ) : fileContent.file_type === 'image' || isImageFile(fileContent.path) ? (
          // Image Viewer
          <div className="image-viewer">
            <img 
              src={`${API_BASE_URL}/api/file-content?path=${encodeURIComponent(fileContent.path)}`} 
              alt={fileContent.path.split('/').pop()} 
              className="file-image"
            />
            <div className="image-info">
              <FaImage /> {fileContent.path.split('/').pop()}
            </div>
          </div>
        ) : fileContent.is_binary ? (
          // Binary File Viewer
          <div className="binary-file-viewer">
            <div className="binary-file-icon">
              <FaFile />
            </div>
            <div className="binary-file-info">
              <p>Binary File</p>
              <p>{fileContent.path.split('/').pop()}</p>
            </div>
          </div>
        ) : (
          // Text Editor
          <Editor
            key={`monaco-${fileContent.path}`}
            height="100%"
            defaultLanguage={getLanguageFromFileName(fileContent.path)}
            defaultValue={fileContent.content}
            onMount={handleEditorDidMount}
            onChange={handleEditorChange}
            theme={editorTheme}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              renderWhitespace: 'selection',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              wordWrap: 'on',
              wrappingIndent: 'indent',
              tabSize: 2,
              insertSpaces: true,
              detectIndentation: true,
              trimAutoWhitespace: true,
              renderLineHighlight: 'line',
              selectionHighlight: true,
              occurrencesHighlight: 'singleFile',
              codeLens: false,
              folding: true,
              foldingHighlight: true,
              showFoldingControls: 'mouseover',
              matchBrackets: 'always',
              autoIndent: 'full',
              formatOnPaste: true,
              formatOnType: true
            }}
            className="editor-container editor-tall"
          />
        )
      )}
    </div>
  );
};

export default FileEditor;