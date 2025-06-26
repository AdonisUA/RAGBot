import React from 'react';
import { Message } from '../../types/chat';
import { User, Bot, Copy, Check } from 'lucide-react';
import { useState } from 'react';

interface MessageBubbleProps {
  message: Message;
  onFeedback?: (messageId: string, score: 'good' | 'bad') => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, onFeedback }) => {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'good' | 'bad' | null>(null);

  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="bg-gray-100 text-gray-600 text-sm px-3 py-1 rounded-full">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}>
      <div className={`flex max-w-xs lg:max-w-md ${isUser ? 'flex-row-reverse' : 'flex-row'} items-end space-x-2`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-600 ml-2' : 'bg-gray-200 mr-2'
        }`}>
          {isUser ? (
            <User className="w-4 h-4 text-white" />
          ) : (
            <Bot className="w-4 h-4 text-gray-600" />
          )}
        </div>

        {/* Message Content */}
        <div className={`relative px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-white text-gray-900 border border-gray-200 shadow-sm'
        }`}>
          {/* Message Text */}
          <div className="break-words whitespace-pre-wrap">
            {message.content}
          </div>

          {/* Timestamp */}
          <div className={`text-xs mt-1 ${
            isUser ? 'text-blue-100' : 'text-gray-500'
          }`}>
            {formatTime(message.timestamp)}
          </div>

          {/* Copy Button */}
          <button
            onClick={copyToClipboard}
            className={`absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded ${
              isUser
                ? 'hover:bg-blue-700 text-blue-100'
                : 'hover:bg-gray-100 text-gray-500'
            }`}
            title="Копировать"
          >
            {copied ? (
              <Check className="w-3 h-3" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
          </button>

          {/* Feedback Buttons (only for assistant) */}
          {!isUser && !isSystem && (
            <div className="flex space-x-2 mt-2">
              <button
                className={`p-1 rounded hover:bg-green-100 ${feedback === 'good' ? 'bg-green-200' : ''}`}
                title="Полезно"
                onClick={() => {
                  setFeedback('good');
                  onFeedback && onFeedback(message.id, 'good');
                }}
                disabled={!!feedback}
              >
                <span role="img" aria-label="like">👍</span>
              </button>
              <button
                className={`p-1 rounded hover:bg-red-100 ${feedback === 'bad' ? 'bg-red-200' : ''}`}
                title="Не полезно"
                onClick={() => {
                  setFeedback('bad');
                  onFeedback && onFeedback(message.id, 'bad');
                }}
                disabled={!!feedback}
              >
                <span role="img" aria-label="dislike">👎</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
