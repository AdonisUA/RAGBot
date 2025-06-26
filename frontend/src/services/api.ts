import axios from 'axios';
import { ChatRequest, ChatResponse, ConversationSummary } from '../types/chat';
import { VoiceResponse } from '../types/voice';

// API Base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Chat API
export const chatAPI = {
  async sendMessage(request: ChatRequest, provider?: string): Promise<ChatResponse> {
    const params = provider ? { provider } : {};
    const response = await apiClient.post('/api/chat/message', request, { params });
    return response.data;
  },

  async getHistory(sessionId: string, page = 1, pageSize = 50) {
    const response = await apiClient.get(`/api/chat/history/${sessionId}`, {
      params: { page, page_size: pageSize }
    });
    return response.data;
  },

  async getConversations(page = 1, pageSize = 20): Promise<ConversationSummary[]> {
    const response = await apiClient.get('/api/chat/conversations', {
      params: { page, page_size: pageSize }
    });
    return response.data;
  },

  async deleteConversation(sessionId: string) {
    const response = await apiClient.delete(`/api/chat/conversation/${sessionId}`);
    return response.data;
  },

  async exportConversation(sessionId: string, format = 'json') {
    const response = await apiClient.get(`/api/chat/conversation/${sessionId}/export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  },

  async cleanup(maxAgeDays = 30) {
    const response = await apiClient.post('/api/chat/cleanup', {
      max_age_days: maxAgeDays
    });
    return response.data;
  },

  async getProviders() {
    const response = await apiClient.get('/api/chat/providers');
    return response.data;
  },

  async switchProvider(provider: string) {
    const response = await apiClient.post('/api/chat/providers/switch', null, {
      params: { provider }
    });
    return response.data;
  },

  async getAvailableModels(provider?: string) {
    const params = provider ? { provider } : {};
    const response = await apiClient.get('/api/chat/models', { params });
    return response.data;
  }
};

// Voice API
export const voiceAPI = {
  async transcribeAudio(
    audioFile: File,
    options: {
      sessionId?: string;
      language?: string;
      task?: string;
      autoSend?: boolean;
    } = {}
  ): Promise<VoiceResponse> {
    const formData = new FormData();
    formData.append('audio', audioFile);

    if (options.sessionId) {
      formData.append('session_id', options.sessionId);
    }
    if (options.language) {
      formData.append('language', options.language);
    }
    if (options.task) {
      formData.append('task', options.task);
    }
    if (options.autoSend !== undefined) {
      formData.append('auto_send', options.autoSend.toString());
    }

    const response = await apiClient.post('/api/voice/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  async getProcessingStatus(audioId: string) {
    const response = await apiClient.get(`/api/voice/status/${audioId}`);
    return response.data;
  },

  async validateAudio(audioFile: File) {
    const formData = new FormData();
    formData.append('audio', audioFile);

    const response = await apiClient.post('/api/voice/validate', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  async getSettings() {
    const response = await apiClient.get('/api/voice/settings');
    return response.data;
  },

  async updateSettings(settings: any) {
    const response = await apiClient.post('/api/voice/settings', settings);
    return response.data;
  },

  async getAvailableModels() {
    const response = await apiClient.get('/api/voice/models');
    return response.data;
  }
};

// Health API
export const healthAPI = {
  async check() {
    const response = await apiClient.get('/health/');
    return response.data;
  },

  async detailed() {
    const response = await apiClient.get('/health/detailed');
    return response.data;
  },

  async system() {
    const response = await apiClient.get('/health/system');
    return response.data;
  },

  async metrics() {
    const response = await apiClient.get('/health/metrics');
    return response.data;
  }
};

// Config API
export const configAPI = {
  async getConfiguration() {
    const response = await apiClient.get('/api/config/');
    return response.data;
  },

  async getChatSettings() {
    const response = await apiClient.get('/api/config/chat');
    return response.data;
  },

  async updateChatSettings(settings: any) {
    const response = await apiClient.post('/api/config/chat', settings);
    return response.data;
  },

  async getVoiceSettings() {
    const response = await apiClient.get('/api/config/voice');
    return response.data;
  },

  async updateVoiceSettings(settings: any) {
    const response = await apiClient.post('/api/config/voice', settings);
    return response.data;
  },

  async getFlows() {
    const response = await apiClient.get('/api/config/flows');
    return response.data;
  },

  async updateFlows(flows: any) {
    const response = await apiClient.post('/api/config/flows', flows);
    return response.data;
  },

  async getPrompts() {
    const response = await apiClient.get('/api/config/prompts');
    return response.data;
  },

  async updatePrompts(prompts: any) {
    const response = await apiClient.post('/api/config/prompts', prompts);
    return response.data;
  }
};

export default apiClient;
