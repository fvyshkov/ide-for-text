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
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const connect = useCallback(() => {
    try {
      const websocket = new WebSocket(url);

      websocket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setReconnectAttempts(0);
      };

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setWs(null);

        // Try to reconnect if we haven't exceeded max attempts
        if (reconnectAttempts < maxReconnectAttempts) {
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, reconnectInterval);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      setWs(websocket);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }, [url, onMessage, reconnectAttempts, reconnectInterval, maxReconnectAttempts]);

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