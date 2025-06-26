import React, { useState, useRef, useCallback } from 'react';
import { Mic, MicOff, Square, Upload } from 'lucide-react';
import { voiceAPI } from '../../services/api';

interface VoiceRecorderProps {
  onTranscription: (text: string) => void;
  isLoading?: boolean;
  sessionId?: string;
}

const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  onTranscription,
  isLoading,
  sessionId
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const startRecording = useCallback(async () => {
    try {
      setError(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: 'audio/webm;codecs=opus'
        });

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());

        await processAudio(audioBlob);
      };

      mediaRecorder.start(1000); // Collect data every second
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (err) {
      console.error('Error starting recording:', err);
      setError('Не удалось получить доступ к микрофону');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, [isRecording]);

  const processAudio = async (audioBlob: Blob) => {
    try {
      setIsProcessing(true);
      setError(null);

      // Convert to WAV for better compatibility
      const audioFile = new File([audioBlob], 'recording.webm', {
        type: 'audio/webm'
      });

      const response = await voiceAPI.transcribeAudio(audioFile, {
        sessionId,
        language: 'auto',
        task: 'transcribe',
        autoSend: false // We'll handle sending manually
      });

      if (response.transcription.text) {
        onTranscription(response.transcription.text);
      } else {
        setError('Не удалось распознать речь');
      }

    } catch (err) {
      console.error('Error processing audio:', err);
      setError('Ошибка обработки аудио');
    } finally {
      setIsProcessing(false);
      setRecordingTime(0);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsProcessing(true);
      setError(null);

      // Validate file
      const validation = await voiceAPI.validateAudio(file);
      if (!validation.valid) {
        setError('Неподдерживаемый формат аудио');
        return;
      }

      const response = await voiceAPI.transcribeAudio(file, {
        sessionId,
        language: 'auto',
        task: 'transcribe',
        autoSend: false
      });

      if (response.transcription.text) {
        onTranscription(response.transcription.text);
      } else {
        setError('Не удалось распознать речь');
      }

    } catch (err) {
      console.error('Error uploading audio:', err);
      setError('Ошибка загрузки файла');
    } finally {
      setIsProcessing(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isDisabled = isLoading || isProcessing;

  return (
    <div className="space-y-4">
      {/* Recording Controls */}
      <div className="flex items-center justify-center space-x-4">
        {!isRecording ? (
          <>
            <button
              onClick={startRecording}
              disabled={isDisabled}
              className="btn btn-primary btn-lg"
              title="Начать запись"
            >
              <Mic className="w-5 h-5 mr-2" />
              Записать
            </button>

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isDisabled}
              className="btn btn-secondary btn-lg"
              title="Загрузить аудио файл"
            >
              <Upload className="w-5 h-5 mr-2" />
              Загрузить
            </button>
          </>
        ) : (
          <button
            onClick={stopRecording}
            className="btn bg-red-600 text-white hover:bg-red-700 btn-lg"
            title="Остановить запись"
          >
            <Square className="w-5 h-5 mr-2" />
            Остановить
          </button>
        )}
      </div>

      {/* Recording Status */}
      {isRecording && (
        <div className="text-center">
          <div className="flex items-center justify-center space-x-2 text-red-600">
            <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse"></div>
            <span className="font-mono text-lg">{formatTime(recordingTime)}</span>
          </div>
          <p className="text-sm text-gray-500 mt-1">Говорите четко в микрофон</p>
        </div>
      )}

      {/* Processing Status */}
      {isProcessing && (
        <div className="text-center">
          <div className="flex items-center justify-center space-x-2 text-blue-600">
            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <span>Обработка аудио...</span>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="audio/*"
        onChange={handleFileUpload}
        className="hidden"
      />

      {/* Instructions */}
      <div className="text-center text-sm text-gray-500">
        <p>Поддерживаемые форматы: WAV, MP3, M4A, OGG</p>
        <p>Максимальная длительность: 60 секунд</p>
      </div>
    </div>
  );
};

export default VoiceRecorder;
