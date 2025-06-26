import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, Mic, Send, Settings } from 'lucide-react';
import ChatContainer from './components/Chat/ChatContainer';
import VoiceRecorder from './components/Voice/VoiceRecorder';
import ProviderSelector from './components/Settings/ProviderSelector';
import { Message } from './types/chat';
import { chatAPI } from './services/api';
import { WebSocketClient } from './services/websocket';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [inputMessage, setInputMessage] = useState('');
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const [currentProvider, setCurrentProvider] = useState<string>('');
  const [showSettings, setShowSettings] = useState(false);
  const [wsStatus, setWsStatus] = useState<string>('disconnected'); // New state for WebSocket status
  const [isTyping, setIsTyping] = useState(false);

  const websocketClientRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    // Generate session ID on app start
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);

    // Initialize WebSocket client
    const wsUrl = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') +
                  '//' + window.location.host + '/ws' +
                  `?session_id=${newSessionId}`;
    const wsClient = new WebSocketClient(wsUrl);
    wsClient.connect();

    wsClient.onMessage((data) => {
      if (data.type === 'new_message') {
        // Add new AI message to the chat
        const newMessage: Message = {
          id: data.data.message_id,
          content: data.data.content,
          role: data.data.role,
          timestamp: new Date().toISOString(),
          session_id: data.data.session_id
        };
        setMessages(prev => [...prev, newMessage]);
      } else if (data.type === 'stream_chunk') {
        // Append chunk to the last assistant message
        setMessages(prev => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            const updatedMessage = { ...lastMessage, content: lastMessage.content + data.data.chunk };
            return [...prev.slice(0, -1), updatedMessage];
          }
          return prev;
        });
      } else if (data.type === 'stream_end') {
        // Finalize the streaming response
        setMessages(prev => {
          const lastMessage = prev[prev.length - 1];
          if (lastMessage && lastMessage.role === 'assistant') {
            const updatedMessage = { ...lastMessage, content: data.data.final_content };
            return [...prev.slice(0, -1), updatedMessage];
          }
          return prev;
        });
        setIsLoading(false);
        setIsTyping(false);
      } else if (data.type === 'typing_indicator') {
        // Handle typing indicator
        setIsTyping(data.data.typing);
      } else if (data.type === 'error') {
        // Handle error messages
        console.error('WebSocket error:', data.data.message);
        const errorMessage: Message = {
          id: `error_${Date.now()}`,
          content: `Ошибка: ${data.data.message}`,
          role: 'assistant',
          timestamp: new Date().toISOString(),
          session_id: sessionId
        };
        setMessages(prev => [...prev, errorMessage]);
        setIsLoading(false);
        setIsTyping(false);
      }
    });

    wsClient.onStatusChange((status) => {
      setWsStatus(status); // Update WebSocket status in UI
    });

    websocketClientRef.current = wsClient;

    // Add welcome message
    const welcomeMessage: Message = {
      id: 'welcome',
      content: 'Привет! Я ваш AI-ассистент. Как дела? Чем могу помочь?',
      role: 'assistant',
      timestamp: new Date().toISOString(),
      session_id: newSessionId
    };
    setMessages([welcomeMessage]);

    return () => {
      wsClient.disconnect();
    };
  }, []);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: `user_${Date.now()}`,
      content: content.trim(),
      role: 'user',
      timestamp: new Date().toISOString(),
      session_id: sessionId
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      if (websocketClientRef.current) {
        websocketClientRef.current.sendMessage('chat_message', { message: content.trim(), sessionId });
        // Don't set isLoading to false here - wait for stream_end event
      } else {
        // Fallback to HTTP API if WebSocket not connected
        const response = await chatAPI.sendMessage({
          message: content.trim(),
          session_id: sessionId,
          context_length: 10
        }, currentProvider || undefined);

        // Add AI response
        const aiMessage: Message = {
          id: response.message_id,
          content: response.response,
          role: 'assistant',
          timestamp: response.timestamp,
          session_id: response.session_id
        };

        setMessages(prev => [...prev, aiMessage]);
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Error sending message:', error);

      // Add error message
      const errorMessage: Message = {
        id: `error_${Date.now()}`,
        content: 'Извините, произошла ошибка. Попробуйте еще раз.',
        role: 'assistant',
        timestamp: new Date().toISOString(),
        session_id: sessionId
      };

      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const handleVoiceTranscription = (text: string) => {
    if (text.trim()) {
      sendMessage(text);
    }
  };

  const handleProviderChange = (provider: string) => {
    setCurrentProvider(provider);
    console.log('Switched to provider:', provider);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputMessage);
    }
  };

  const handleFeedback = (messageId: string, score: 'good' | 'bad') => {
    if (websocketClientRef.current) {
      websocketClientRef.current.sendMessage('feedback', {
        message_id: messageId,
        score,
        session_id: sessionId
      });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <MessageCircle className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">AI ChatBot</h1>
                <p className="text-sm text-gray-500">Универсальный AI-ассистент</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {/* Provider Selector */}
              <ProviderSelector onProviderChange={handleProviderChange} />

              <button
                onClick={() => setIsVoiceMode(!isVoiceMode)}
                className={`btn btn-sm ${isVoiceMode ? 'btn-primary' : 'btn-secondary'}`}
              >
                <Mic className="w-4 h-4 mr-2" />
                Голос
              </button>

              <button
                onClick={() => setShowSettings(!showSettings)}
                className="btn btn-secondary btn-sm"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto flex flex-col h-[calc(100vh-64px)]">
        <div className="flex-1 overflow-y-auto">
          <ChatContainer
            messages={messages}
            isLoading={isLoading}
            onFeedback={handleFeedback}
          />
          {/* Typing indicator */}
          {isTyping && (
            <div className="text-gray-600 italic p-2 text-center">
              AI печатает...
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t bg-gray-50 p-4">
          {isVoiceMode ? (
            <VoiceRecorder
              onTranscription={handleVoiceTranscription}
              isLoading={isLoading}
            />
          ) : (
            <div className="flex space-x-3">
              <div className="flex-1">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Введите сообщение..."
                  className="input resize-none"
                  rows={1}
                  disabled={isLoading}
                />
              </div>

              <button
                onClick={() => sendMessage(inputMessage)}
                disabled={!inputMessage.trim() || isLoading}
                className="btn btn-primary btn-md"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Status */}
        <div className="mt-4 text-center">
          <p className="text-sm text-gray-500">
            Сессия: {sessionId} • Сообщений: {messages.length}
            {currentProvider && ` • AI: ${currentProvider}`}
            {isLoading && ' • Обработка...'}
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
