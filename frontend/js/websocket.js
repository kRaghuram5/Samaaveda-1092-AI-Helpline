/**
 * WebSocket Client for Samaaveda
 */
class WebSocketClient {
    constructor() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.url = `${protocol}//${window.location.host}/ws`;
        this.socket = null;
        this.handlers = {};
        this.reconnectAttempts = 0;
        this.connect();
    }

    connect() {
        console.log(`[WS] Connecting to ${this.url}...`);
        this.socket = new WebSocket(this.url);

        this.socket.onopen = () => {
            console.log('[WS] Connected successfully.');
            this.reconnectAttempts = 0;
            this.emit('connection_open', {});
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('[WS] Received:', data.type);
                if (this.handlers[data.type]) {
                    this.handlers[data.type](data);
                }
            } catch (err) {
                // If not JSON, it's likely binary or a raw status
                console.debug('[WS] Non-JSON message received');
            }
        };

        this.socket.onclose = () => {
            console.warn('[WS] Connection closed.');
            if (this.reconnectAttempts < 5) {
                this.reconnectAttempts++;
                setTimeout(() => this.connect(), 2000);
            }
        };

        this.socket.onerror = (err) => {
            console.error('[WS] Socket error:', err);
        };
    }

    on(type, handler) {
        this.handlers[type] = handler;
    }

    emit(type, data) {
        if (this.handlers[type]) this.handlers[type](data);
    }

    sendJSON(data) {
        if (this.isConnected()) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.error('[WS] Cannot send: Not connected');
        }
    }

    isConnected() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }
}

window.wsClient = new WebSocketClient();
