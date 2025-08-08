import React, { useState, useRef, useEffect } from 'react';
import { FaPaperPlane, FaRobot, FaUser, FaTrash, FaBrain, FaTools, FaCheckCircle, FaCopy, FaCheck } from 'react-icons/fa';
import './AIChat.css';
// Импортируем API для работы с файлами
import { openFile } from '../utils/fileUtils';

interface Message {
  id: string;
  type: 'user' | 'assistant' | 'thinking' | 'tool_use' | 'tool_result' | 'file_generated';
  content: string;
  timestamp: Date;
  metadata?: {
    tool_name?: string;
    tool_input?: any;
    thinking_type?: string;
    generatedFile?: {
      path: string;
      type: 'image' | 'text' | 'other';
    };
  };
}

interface AIChatProps {
  // Future: add props for current file context, project context, etc.
  currentFile?: string;
  projectPath?: string;
}

const AIChat = React.forwardRef<{ askQuestion: (question: string) => void }, AIChatProps>((props, ref) => {
  const { currentFile, projectPath } = props;
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'Hello! I\'m your AI coding assistant. I can help you with your code, answer questions about your project, and assist with development tasks.',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Reset height to calculate new height
      textarea.style.height = 'auto';
      
      // Calculate line height (approximate)
      const lineHeight = 20;
      const maxLines = 10;
      const maxHeight = lineHeight * maxLines;
      
      // Set new height based on scroll height, but cap at max
      const newHeight = Math.min(textarea.scrollHeight, maxHeight);
      textarea.style.height = `${newHeight}px`;
    }
  };

  const removeAttachment = (path: string) => {
    setAttachedFiles(prev => prev.filter(p => p !== path));
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const text = e.dataTransfer.getData('text/plain');
    if (text) {
      setAttachedFiles(prev => Array.from(new Set([...prev, text])));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea when input changes
  useEffect(() => {
    adjustTextareaHeight();
  }, [inputValue]);

  // Expose askQuestion method through ref
  React.useImperativeHandle(ref, () => ({
    askQuestion: (question: string) => {
      setInputValue(question);
      setTimeout(() => handleSendMessage(question), 0);
    }
  }));

  const handleSendMessage = async (manualInput?: string) => {
    const messageText = manualInput || inputValue;
    if (!messageText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: messageText.trim() + (attachedFiles.length ? `\n\nFiles: ${attachedFiles.map(p => `@${p}`).join(' ')}` : ''),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const originalInput = messageText.trim();
    setInputValue('');
    setIsLoading(true);
    
    // Reset textarea height after sending
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }, 0);

    try {
      // Call our real AI API with streaming
      const response = await fetch('http://localhost:8001/api/ai/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: originalInput,
          file_paths: attachedFiles.length ? attachedFiles : (currentFile ? [currentFile] : undefined),
          project_path: projectPath
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          // Add chunk to buffer
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer
          
          for (const line of lines) {
            if (line.trim()) {
              try {
                // Handle Server-Sent Events format (data: {...})
                let jsonData = line.trim();
                if (jsonData.startsWith('data: ')) {
                  jsonData = jsonData.substring(6); // Remove 'data: ' prefix
                }
                
                if (jsonData) {
                  const event = JSON.parse(jsonData);
                  
                  // Create message based on event type
                  // Ensure content is always a string and format JSON-like content
                  let content = event.content;
                  if (typeof content !== 'string') {
                    content = JSON.stringify(content, null, 2);
                  } else if (content.includes('{') && content.includes('}')) {
                    // Try to format JSON-like strings more readably
                    try {
                      const parsed = JSON.parse(content);
                      content = JSON.stringify(parsed, null, 2);
                    } catch {
                      // If parsing fails, keep original string
                    }
                  }

                  const aiMessage: Message = {
                    id: `ai-${Date.now()}-${Math.random()}`,
                    type: event.type === 'final_result' ? 'assistant' : 
                          event.type === 'tool_use' ? 'tool_use' :
                          event.type === 'tool_result' ? 'tool_result' : 'thinking',
                    content: content,
                    timestamp: new Date(),
                    metadata: {
                      tool_name: event.tool_name,
                      tool_input: event.tool_input,
                      thinking_type: event.type
                    }
                  };

                  setMessages(prev => {
                    // Prevent duplicate messages
                    const isDuplicate = prev.some(msg => 
                      msg.content === aiMessage.content && 
                      msg.type === aiMessage.type &&
                      Math.abs(msg.timestamp.getTime() - aiMessage.timestamp.getTime()) < 1000
                    );
                    
                    if (isDuplicate) {
                      return prev;
                    }
                    
                    return [...prev, aiMessage];
                  });

                  if (event.type === 'file_changed') {
                    const fileMessage: Message = {
                      id: `file-${Date.now()}`,
                      type: 'file_generated',
                      content: `Создан файл: ${event.path.split('/').pop()}`,
                      timestamp: new Date(),
                      metadata: {
                        generatedFile: {
                          path: event.path,
                          type: event.path.toLowerCase().endsWith('.png') ? 'image' : 
                                 event.path.toLowerCase().endsWith('.txt') ? 'text' : 'other'
                        }
                      }
                    };

                    setMessages(prev => [...prev, fileMessage]);
                  }
                }
              } catch (e) {
                console.error('Failed to parse AI event:', e, 'Line:', line);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('AI API Error:', error);
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        type: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      // Keep chips after sending per UX request
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearChat = () => {
    setMessages([{
      id: Date.now().toString(),
      type: 'assistant',
      content: 'Chat cleared. How can I help you?',
      timestamp: new Date()
    }]);
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user': return <FaUser />;
      case 'thinking': return <FaBrain />;
      case 'tool_use': return <FaTools />;
      case 'tool_result': return <FaCheckCircle />;
      default: return <FaRobot />;
    }
  };

  const getMessageClass = (type: string) => {
    switch (type) {
      case 'thinking': return 'message thinking';
      case 'tool_use': return 'message tool-use';
      case 'tool_result': return 'message tool-result';
      default: return `message ${type}`;
    }
  };

  const copyToClipboard = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      
      // Reset the copied state after 2 seconds
      setTimeout(() => {
        setCopiedMessageId(null);
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = content;
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        setCopiedMessageId(messageId);
        setTimeout(() => {
          setCopiedMessageId(null);
        }, 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy failed: ', fallbackErr);
      }
      
      document.body.removeChild(textArea);
    }
  };

  const handleMessageClick = (message: Message) => {
    if (message.type === 'file_generated' && message.metadata?.generatedFile) {
      openFile(message.metadata.generatedFile.path);
    }
  };

  return (
      <div className="ai-chat" onDrop={handleDrop} onDragOver={handleDragOver}>
      <div className="ai-chat-header">
        <div className="chat-title">
          <FaRobot className="chat-icon" />
          <span>AI Assistant</span>
        </div>
        <button 
          className="clear-chat-btn"
          onClick={clearChat}
          title="Clear chat"
        >
          <FaTrash />
        </button>
      </div>

      <div className="ai-chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={getMessageClass(message.type)} onClick={() => handleMessageClick(message)}>
            <div className="message-header">
              <div className="message-avatar">
                {getMessageIcon(message.type)}
              </div>
              <span className="message-time">
                {formatTimestamp(message.timestamp)}
              </span>
              {message.metadata?.thinking_type && (
                <span className="thinking-type">
                  {message.metadata.thinking_type}
                </span>
              )}
              <button
                className={`copy-button ${copiedMessageId === message.id ? 'copied' : ''}`}
                onClick={() => copyToClipboard(message.id, message.content)}
                title="Copy message"
              >
                {copiedMessageId === message.id ? <FaCheck /> : <FaCopy />}
              </button>
            </div>
            <div className="message-content">
              {message.content}
              {message.metadata?.tool_input && (
                <div className="tool-input">
                  <small>Input: {JSON.stringify(message.metadata.tool_input)}</small>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant loading">
            <div className="message-header">
              <div className="message-avatar">
                <FaRobot />
              </div>
              <span className="message-time">...</span>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="ai-chat-input">
        <div className="input-container">
          {/* Attachments (chips) */}
          {attachedFiles.length > 0 && (
            <div className="attached-files">
              <button className="file-chips-clear" onClick={() => setAttachedFiles([])} title="Clear all">×</button>
              {attachedFiles.map((p) => (
                <span key={p} className="file-chip" title={p}>
                  <span className="file-chip-name">{p.split('/').pop()}</span>
                  <button className="file-chip-remove" onClick={() => removeAttachment(p)} aria-label="Remove file">×</button>
                </span>
              ))}
            </div>
          )}

          <div className="prompt-row">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                // Trigger resize on next tick to ensure state is updated
                setTimeout(adjustTextareaHeight, 0);
              }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onKeyDown={handleKeyDown}
              placeholder="Ask me about your code, project, or anything else..."
              className="chat-textarea"
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isLoading}
              className="send-button"
              title="Send message (Enter)"
            >
              <FaPaperPlane />
            </button>
          </div>
        </div>
        <div className="input-hint">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
});

export default AIChat;