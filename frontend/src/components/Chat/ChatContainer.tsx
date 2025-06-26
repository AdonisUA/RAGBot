import React, { useEffect, useRef } from 'react';
import { Message } from '../../types/chat';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

interface ChatContainerProps {
  messages: Message[];
  isLoading?: boolean;
  onFeedback?: (messageId: string, score: 'good' | 'bad') => void;
}

const ChatContainer: React.FC<ChatContainerProps> = ({ messages, isLoading, onFeedback }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col space-y-4 p-4 h-full">
      {messages.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <p className="text-lg font-medium">Начните разговор</p>
            <p className="text-sm">Отправьте сообщение или используйте голосовой ввод</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 space-y-4">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} onFeedback={onFeedback} />
          ))}

          {isLoading && <TypingIndicator />}
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatContainer;
