import React, { useState, useRef, useEffect, ReactNode } from 'react';
import './ResizableSplitter.css';

interface ResizableSplitterProps {
  leftPanel: ReactNode;
  rightPanel: ReactNode;
  defaultLeftWidth?: number;
  minLeftWidth?: number;
  maxLeftWidth?: number;
}

const ResizableSplitter: React.FC<ResizableSplitterProps> = ({
  leftPanel,
  rightPanel,
  defaultLeftWidth = 300,
  minLeftWidth = 200,
  maxLeftWidth = 600
}) => {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load saved width from localStorage
    const savedWidth = localStorage.getItem('text-ide-left-panel-width');
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width >= minLeftWidth && width <= maxLeftWidth) {
        setLeftWidth(width);
      }
    }
  }, [minLeftWidth, maxLeftWidth]);

  useEffect(() => {
    // Save width to localStorage
    localStorage.setItem('text-ide-left-panel-width', leftWidth.toString());
  }, [leftWidth]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      const containerRect = containerRef.current.getBoundingClientRect();
      const newWidth = e.clientX - containerRect.left;
      
      // Constrain width to min/max values
      const constrainedWidth = Math.max(
        minLeftWidth,
        Math.min(maxLeftWidth, newWidth)
      );
      
      setLeftWidth(constrainedWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
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
  }, [isDragging, minLeftWidth, maxLeftWidth]);

  return (
    <div className="resizable-splitter" ref={containerRef}>
      <div 
        className="resizable-panel left-panel" 
        style={{ width: `${leftWidth}px` }}
      >
        {leftPanel}
      </div>
      
      <div 
        className={`splitter-handle ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
      >
        <div className="splitter-line" />
      </div>
      
      <div 
        className="resizable-panel right-panel"
        style={{ width: `calc(100% - ${leftWidth + 4}px)` }}
      >
        {rightPanel}
      </div>
    </div>
  );
};

export default ResizableSplitter;