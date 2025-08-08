import React, { useState } from 'react';
import { FaFolder, FaFolderOpen, FaFile, FaChevronRight, FaChevronDown } from 'react-icons/fa';
import { FileTreeItem } from '../types';
import './FileTree.css';

interface FileTreeProps {
  items: FileTreeItem[];
  onFileSelect: (filePath: string) => void;
  selectedFile: string | null;
  level?: number;
}

interface TreeNodeProps {
  item: FileTreeItem;
  onFileSelect: (filePath: string) => void;
  selectedFile: string | null;
  level: number;
}

const TreeNode: React.FC<TreeNodeProps> = ({ item, onFileSelect, selectedFile, level }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const isSelected = selectedFile === item.path;
  const hasChildren = item.is_directory && item.children && item.children.length > 0;

  const handleClick = () => {
    if (item.is_directory) {
      setIsExpanded(!isExpanded);
    } else {
      onFileSelect(item.path);
    }
  };

  const handleDragStart = (e: React.DragEvent) => {
    if (item.is_directory) return;
    // Put absolute path as plain text to be consumed by drop targets
    e.dataTransfer.setData('text/plain', item.path);
    // Custom type for potential future extensions
    e.dataTransfer.setData('application/x-ide-filepath', item.path);
    e.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <div className="tree-node">
      <div
        className={`tree-node-content ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft: `${level * 20}px` }}
        onClick={handleClick}
        draggable={!item.is_directory}
        onDragStart={handleDragStart}
        title={item.is_directory ? undefined : 'Drag to prompt input'}
      >
        <div className="tree-node-icon">
          {item.is_directory ? (
            <>
              {hasChildren && (
                <span className="tree-node-chevron">
                  {isExpanded ? <FaChevronDown /> : <FaChevronRight />}
                </span>
              )}
              {isExpanded ? <FaFolderOpen /> : <FaFolder />}
            </>
          ) : (
            <FaFile />
          )}
        </div>
        <span className="tree-node-name">{item.name}</span>
      </div>
      
      {item.is_directory && isExpanded && item.children && (
        <div className="tree-node-children">
          {item.children.map((child, index) => (
            <TreeNode
              key={`${child.path}-${index}`}
              item={child}
              onFileSelect={onFileSelect}
              selectedFile={selectedFile}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const FileTree: React.FC<FileTreeProps> = ({ items, onFileSelect, selectedFile, level = 0 }) => {
  if (!items || items.length === 0) {
    return (
      <div className="file-tree empty">
        <p>No files to display. Open a directory to get started.</p>
      </div>
    );
  }

  return (
    <div className="file-tree">
      {items.map((item, index) => (
        <TreeNode
          key={`${item.path}-${index}`}
          item={item}
          onFileSelect={onFileSelect}
          selectedFile={selectedFile}
          level={level}
        />
      ))}
    </div>
  );
};

export default FileTree;