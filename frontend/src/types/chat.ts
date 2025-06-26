export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: string;
  session_id?: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  context_length?: number;
  stream?: boolean;
  metadata?: Record<string, any>;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  message_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
  usage?: Record<string, any>;
}

export interface Conversation {
  session_id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
  title?: string;
}

export interface ConversationSummary {
  session_id: string;
  title?: string;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_preview?: string;
}
