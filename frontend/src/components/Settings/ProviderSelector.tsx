import React, { useState, useEffect } from 'react';
import { Bot, Check, ChevronDown, Zap } from 'lucide-react';
import { chatAPI } from '../../services/api';

interface Provider {
  name: string;
  model: string;
}

interface ProviderInfo {
  current_provider: string;
  available_providers: string[];
  provider_configs: Record<string, Provider>;
}

interface ProviderSelectorProps {
  onProviderChange?: (provider: string) => void;
}

const ProviderSelector: React.FC<ProviderSelectorProps> = ({ onProviderChange }) => {
  const [providerInfo, setProviderInfo] = useState<ProviderInfo | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProviderInfo();
  }, []);

  const loadProviderInfo = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const info = await chatAPI.getProviders();
      setProviderInfo(info);

    } catch (err) {
      console.error('Failed to load provider info:', err);
      setError('Не удалось загрузить информацию о провайдерах');
    } finally {
      setIsLoading(false);
    }
  };

  const switchProvider = async (provider: string) => {
    try {
      setIsLoading(true);
      setError(null);

      await chatAPI.switchProvider(provider);

      // Update local state
      if (providerInfo) {
        setProviderInfo({
          ...providerInfo,
          current_provider: provider
        });
      }

      // Notify parent component
      onProviderChange?.(provider);

      setIsOpen(false);

    } catch (err) {
      console.error('Failed to switch provider:', err);
      setError('Не удалось переключить провайдера');
    } finally {
      setIsLoading(false);
    }
  };

  const getProviderDisplayName = (provider: string) => {
    const displayNames: Record<string, string> = {
      'openai': 'OpenAI GPT',
      'gemini': 'Google Gemini',
      'anthropic': 'Anthropic Claude'
    };
    return displayNames[provider] || provider;
  };

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case 'openai':
        return '🤖';
      case 'gemini':
        return '✨';
      case 'anthropic':
        return '🧠';
      default:
        return '🔮';
    }
  };

  if (isLoading && !providerInfo) {
    return (
      <div className="flex items-center space-x-2 text-gray-500">
        <div className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm">Загрузка...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        {error}
      </div>
    );
  }

  if (!providerInfo || providerInfo.available_providers.length === 0) {
    return (
      <div className="text-gray-500 text-sm">
        Нет доступных провайдеров
      </div>
    );
  }

  const currentProvider = providerInfo.current_provider;
  const currentConfig = providerInfo.provider_configs[currentProvider];

  return (
    <div className="relative">
      {/* Current Provider Display */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="flex items-center space-x-2 px-3 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors w-full min-w-48"
      >
        <span className="text-lg">{getProviderIcon(currentProvider)}</span>
        <div className="flex-1 text-left">
          <div className="font-medium text-gray-900">
            {getProviderDisplayName(currentProvider)}
          </div>
          {currentConfig && (
            <div className="text-xs text-gray-500">
              {currentConfig.model}
            </div>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          <div className="py-1">
            {providerInfo.available_providers.map((provider) => {
              const config = providerInfo.provider_configs[provider];
              const isCurrent = provider === currentProvider;

              return (
                <button
                  key={provider}
                  onClick={() => switchProvider(provider)}
                  disabled={isLoading || isCurrent}
                  className={`w-full flex items-center space-x-3 px-3 py-2 text-left hover:bg-gray-50 transition-colors ${
                    isCurrent ? 'bg-blue-50' : ''
                  }`}
                >
                  <span className="text-lg">{getProviderIcon(provider)}</span>
                  <div className="flex-1">
                    <div className={`font-medium ${isCurrent ? 'text-blue-700' : 'text-gray-900'}`}>
                      {getProviderDisplayName(provider)}
                    </div>
                    {config && (
                      <div className={`text-xs ${isCurrent ? 'text-blue-600' : 'text-gray-500'}`}>
                        {config.model}
                      </div>
                    )}
                  </div>
                  {isCurrent && (
                    <Check className="w-4 h-4 text-blue-600" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Footer */}
          <div className="border-t border-gray-100 px-3 py-2">
            <div className="flex items-center space-x-1 text-xs text-gray-500">
              <Zap className="w-3 h-3" />
              <span>Провайдеры AI</span>
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        </div>
      )}
    </div>
  );
};

export default ProviderSelector;
