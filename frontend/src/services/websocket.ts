import ReconnectingWebSocket from 'reconnecting-websocket';

type MessageCallback = (data: any) => void;

export class WebSocketClient {
  private socket: any = null;
  private messageCallback: MessageCallback | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private statusCallback: ((status: string) => void) | null = null;

  constructor(private url: string) {}

  connect() {
    if (this.socket) {
      return;
    }
    this.socket = new ReconnectingWebSocket(this.url);

    this.socket.addEventListener('open', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      if (this.statusCallback) {
        this.statusCallback('connected');
      }
    });

    this.socket.addEventListener('close', () => {
      console.log('WebSocket disconnected');
      if (this.statusCallback) {
        this.statusCallback('disconnected');
      }
      this._scheduleReconnect();
    });

    this.socket.addEventListener('error', (event: Event) => {
      console.error('WebSocket error', event);
      if (this.statusCallback) {
        this.statusCallback('error');
      }
      this._scheduleReconnect();
    });

    this.socket.addEventListener('message', (event: any) => {
      if (this.messageCallback) {
        try {
          const data = JSON.parse(event.data);
          this.messageCallback(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      }
    });
  }

  private _scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('Max reconnect attempts reached');
      return;
    }
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
    this.reconnectAttempts++;
    setTimeout(() => {
      console.log(`Reconnecting WebSocket, attempt ${this.reconnectAttempts}`);
      this.connect();
    }, delay);
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  sendMessage(type: string, payload: object) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected');
      return;
    }
    const message = JSON.stringify({ type, payload });
    this.socket.send(message);
  }

  onMessage(callback: MessageCallback) {
    this.messageCallback = callback;
  }

  onStatusChange(callback: (status: string) => void) {
    this.statusCallback = callback;
  }
}
