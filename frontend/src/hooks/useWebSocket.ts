import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketMessage {
  type: string;
  path?: string;
  content?: string;
  sender?: string;
  timestamp?: number;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  enabled?: boolean;
}

// Global WebSocket instance to ensure only one connection per app
let globalWebSocket: WebSocket | null = null;
let globalListeners: Set<(message: WebSocketMessage) => void> = new Set();
let connectionPromise: Promise<WebSocket> | null = null;

const createConnection = async (url: string): Promise<WebSocket> => {
  return new Promise((resolve, reject) => {
    if (globalWebSocket && globalWebSocket.readyState === WebSocket.OPEN) {
      resolve(globalWebSocket);
      return;
    }

    console.log('🔌 Creating new WebSocket connection...');
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('✅ WebSocket connected successfully');
      globalWebSocket = ws;
      resolve(ws);
    };

    ws.onmessage = (event) => {
      try {
        console.log('🎯 Raw WebSocket message received:', event.data);
        const message = JSON.parse(event.data);
        console.log('🎯 Parsed WebSocket message:', message);
        console.log('🎯 Number of listeners:', globalListeners.size);
        // Broadcast to all listeners
        globalListeners.forEach((listener, index) => {
          console.log(`🎯 Calling listener ${index}`);
          listener(message);
        });
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = (event) => {
      console.log('❌ WebSocket disconnected, code:', event.code, 'reason:', event.reason);
      globalWebSocket = null;
      connectionPromise = null;
      
      // If server rejected with too many connections, don't retry immediately
      if (event.code === 1008) {
        console.log('🚫 Server rejected connection - too many connections');
        return;
      }

      // Auto-reconnect after a delay if there are active listeners
      if (globalListeners.size > 0) {
        console.log('🔄 Will auto-reconnect WebSocket in 2 seconds...');
        setTimeout(() => {
          console.log('🔄 Auto-reconnecting WebSocket...');
          connectionPromise = createConnection(url);
        }, 2000);
      }
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      reject(error);
    };
  });
};

export const useWebSocket = ({
  url,
  onMessage,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
  enabled = true
}: UseWebSocketOptions) => {
  console.log('🔌 useWebSocket called with:', { url, enabled, onMessage: !!onMessage });
  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const onMessageRef = useRef(onMessage);
  
  // Keep the callback ref updated
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  // Create a stable listener function
  const listener = useCallback((message: WebSocketMessage) => {
    onMessageRef.current?.(message);
  }, []);

  useEffect(() => {
    console.log('🔌 useWebSocket useEffect, enabled:', enabled);
    if (!enabled) {
      console.log('🔌 useWebSocket disabled, returning');
      return;
    }

    // Add this component's listener to global set
    console.log('🔌 Adding listener to global set, current size:', globalListeners.size);
    globalListeners.add(listener);
    
    // Create connection if it doesn't exist
    if (!connectionPromise) {
      console.log('🔌 Creating new connection promise');
      connectionPromise = createConnection(url);
    } else {
      console.log('🔌 Connection promise already exists');
    }

    // Wait for connection and update state
    connectionPromise
      .then((ws) => {
        if (ws.readyState === WebSocket.OPEN) {
          setIsConnected(true);
          setReconnectAttempts(0);
        }
      })
      .catch((error) => {
        console.error('Failed to connect WebSocket:', error);
        setIsConnected(false);
      });

    // Monitor connection state
    const checkConnection = () => {
      const isOpen = globalWebSocket?.readyState === WebSocket.OPEN;
      setIsConnected(isOpen);
    };

    const interval = setInterval(checkConnection, 1000);

    return () => {
      // Remove listener when component unmounts
      globalListeners.delete(listener);
      clearInterval(interval);
      
      // Close connection if no listeners left
      if (globalListeners.size === 0 && globalWebSocket) {
        console.log('🔌 Closing WebSocket - no more listeners');
        globalWebSocket.close();
        globalWebSocket = null;
        connectionPromise = null;
      }
    };
  }, [url, listener, enabled]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (globalWebSocket && globalWebSocket.readyState === WebSocket.OPEN) {
      const messageWithTimestamp = {
        ...message,
        timestamp: Date.now()
      };
      globalWebSocket.send(JSON.stringify(messageWithTimestamp));
      console.log('📤 Sent WebSocket message:', messageWithTimestamp);
    } else {
      console.warn('⚠️ WebSocket not connected (state:', globalWebSocket?.readyState, '), message not sent:', message);
      
      // Try to reconnect if not connected
      if (!connectionPromise) {
        console.log('🔄 Attempting to reconnect WebSocket...');
        connectionPromise = createConnection(url);
      }
    }
  }, [url]);

  return {
    isConnected,
    sendMessage,
    reconnectAttempts
  };
};