export interface VoiceRequest {
  audio_id?: string;
  session_id?: string;
  language?: string;
  task?: 'transcribe' | 'translate';
  temperature?: number;
  auto_send?: boolean;
  metadata?: Record<string, any>;
}

export interface TranscriptionResult {
  id: string;
  text: string;
  confidence?: number;
  language?: string;
  duration?: number;
  segments?: any[];
  processing_time?: number;
  timestamp: string;
}

export interface VoiceResponse {
  transcription: TranscriptionResult;
  audio_id: string;
  session_id?: string;
  auto_sent_to_chat: boolean;
  chat_message_id?: string;
  metadata?: Record<string, any>;
}

export interface AudioProcessingStatus {
  audio_id: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  progress: number;
  message?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
  processing_time?: number;
}
