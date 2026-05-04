/**
 * Audio Capture and Streaming
 */
class AudioCapture {
    constructor() {
        this.mediaRecorder = null;
        this.stream = null;
    }

    async start(language) {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Start Visualizer
            if (window.visualizer) {
                window.visualizer.start(this.stream);
            }

            // Tell backend we're starting
            window.wsClient.sendJSON({ type: 'start_session', language: language || 'auto' });

            // Create MediaRecorder
            // Use a standard format (webm/opus)
            const options = { mimeType: 'audio/webm;codecs=opus' };
            this.mediaRecorder = new MediaRecorder(this.stream, options);

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && window.wsClient.isConnected()) {
                    window.wsClient.socket.send(event.data);
                }
            };

            this.mediaRecorder.start(300); // Send chunks every 300ms
            return true;
        } catch (err) {
            console.error('[Audio] Error starting capture:', err);
            return false;
        }
    }

    async stop() {
        if (this.mediaRecorder) {
            this.mediaRecorder.stop();
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        if (window.visualizer) {
            window.visualizer.stop();
        }
    }
}

window.audioCapture = new AudioCapture();
