import { useState, useEffect, useCallback } from 'react';

interface WebSocketMessage {
  type: string;
  path?: string;
  content?: string;
  sender?: string;
}

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export const useWebSocket = ({
  url,
  onMessage,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5
}: UseWebSocketOptions) => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isRejected, setIsRejected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const connect = useCallback(() => {
    // Don't try to connect if we're rejected or already connected
    if (isRejected || (ws && ws.readyState === WebSocket.OPEN)) {
      return;
    }

    try {
      console.log('Connecting to WebSocket...');
      const websocket = new WebSocket(url);

      websocket.onopen = () => {
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setReconnectAttempts(0);
        setIsRejected(false);
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      websocket.onclose = (event) => {
        console.log('WebSocket closed with code:', event.code);
        setIsConnected(false);
        setWs(null);

        if (event.code === 1008) {
          console.log('Server rejected connection - too many connections');
          setIsRejected(true);
          return;
        }

        // Only try to reconnect if we're not rejected and haven't exceeded max attempts
        if (!isRejected && reconnectAttempts < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), reconnectInterval);
          console.log(`Will try to reconnect in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, delay);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      setWs(websocket);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }, [url, onMessage, reconnectAttempts, reconnectInterval, maxReconnectAttempts, ws, isRejected]);

  useEffect(() => {
    connect();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [connect, ws]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected, message not sent:', message);
    }
  }, [ws]);

  return {
    isConnected,
    sendMessage,
    reconnectAttempts
  };
};