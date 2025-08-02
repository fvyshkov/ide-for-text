import React, { useState, useRef, useEffect, ReactNode } from 'react';
import './TripleSplitter.css';

interface TripleSplitterProps {
  leftPanel: ReactNode;
  centerPanel: ReactNode;
  rightPanel: ReactNode;
  defaultLeftWidth?: number;
  defaultRightWidth?: number;
  minLeftWidth?: number;
  maxLeftWidth?: number;
  minRightWidth?: number;
  maxRightWidth?: number;
}

const TripleSplitter: React.FC<TripleSplitterProps> = ({
  leftPanel,
  centerPanel,
  rightPanel,
  defaultLeftWidth = 300,
  defaultRightWidth = 400,
  minLeftWidth = 200,
  maxLeftWidth = 600,
  minRightWidth = 300,
  maxRightWidth = 800
}) => {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [rightWidth, setRightWidth] = useState(defaultRightWidth);
  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load saved widths from localStorage
  useEffect(() => {
    const savedLeftWidth = localStorage.getItem('text-ide-left-panel-width');
    const savedRightWidth = localStorage.getItem('text-ide-right-panel-width');
    
    if (savedLeftWidth) {
      const width = parseInt(savedLeftWidth, 10);
      if (width >= minLeftWidth && width <= maxLeftWidth) {
        setLeftWidth(width);
      }
    }
    
    if (savedRightWidth) {
      const width = parseInt(savedRightWidth, 10);
      if (width >= minRightWidth && width <= maxRightWidth) {
        setRightWidth(width);
      }
    }
  }, [minLeftWidth, maxLeftWidth, minRightWidth, maxRightWidth]);

  // Save widths to localStorage
  useEffect(() => {
    localStorage.setItem('text-ide-left-panel-width', leftWidth.toString());
  }, [leftWidth]);

  useEffect(() => {
    localStorage.setItem('text-ide-right-panel-width', rightWidth.toString());
  }, [rightWidth]);

  const handleLeftMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingLeft(true);
  };

  const handleRightMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingRight(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      
      const containerRect = containerRef.current.getBoundingClientRect();
      const containerWidth = containerRect.width;

      if (isDraggingLeft) {
        const newLeftWidth = e.clientX - containerRect.left;
        const constrainedWidth = Math.max(
          minLeftWidth,
          Math.min(maxLeftWidth, newLeftWidth)
        );
        setLeftWidth(constrainedWidth);
      }

      if (isDraggingRight) {
        const newRightWidth = containerRect.right - e.clientX;
        const constrainedWidth = Math.max(
          minRightWidth,
          Math.min(maxRightWidth, newRightWidth)
        );
        setRightWidth(constrainedWidth);
      }
    };

    const handleMouseUp = () => {
      setIsDraggingLeft(false);
      setIsDraggingRight(false);
    };

    if (isDraggingLeft || isDraggingRight) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDraggingLeft, isDraggingRight, minLeftWidth, maxLeftWidth, minRightWidth, maxRightWidth]);

  const centerWidth = `calc(100% - ${leftWidth + rightWidth + 8}px)`;

  return (
    <div className="triple-splitter" ref={containerRef}>
      {/* Left Panel */}
      <div 
        className="triple-panel left-panel" 
        style={{ width: `${leftWidth}px` }}
      >
        {leftPanel}
      </div>
      
      {/* Left Splitter */}
      <div 
        className={`splitter-handle left-splitter ${isDraggingLeft ? 'dragging' : ''}`}
        onMouseDown={handleLeftMouseDown}
      >
        <div className="splitter-line" />
      </div>
      
      {/* Center Panel */}
      <div 
        className="triple-panel center-panel"
        style={{ width: centerWidth }}
      >
        {centerPanel}
      </div>
      
      {/* Right Splitter */}
      <div 
        className={`splitter-handle right-splitter ${isDraggingRight ? 'dragging' : ''}`}
        onMouseDown={handleRightMouseDown}
      >
        <div className="splitter-line" />
      </div>
      
      {/* Right Panel */}
      <div 
        className="triple-panel right-panel"
        style={{ width: `${rightWidth}px` }}
      >
        {rightPanel}
      </div>
    </div>
  );
};

export default TripleSplitter;