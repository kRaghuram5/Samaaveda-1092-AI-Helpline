/**
 * Audio Visualizer using Web Audio API
 */
class Visualizer {
    constructor() {
        this.canvas = document.getElementById('visualizer');
        this.ctx = this.canvas.getContext('2d');
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
    }

    start(stream) {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioCtx.createMediaStreamSource(stream);
        this.analyser = audioCtx.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);

        const bufferLength = this.analyser.frequencyBinCount;
        this.dataArray = new Uint8Array(bufferLength);

        this.draw();
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    draw() {
        this.animationId = requestAnimationFrame(() => this.draw());
        this.analyser.getByteFrequencyData(this.dataArray);

        this.ctx.fillStyle = '#161b22';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        const barWidth = (this.canvas.width / this.dataArray.length) * 2.5;
        let x = 0;

        for (let i = 0; i < this.dataArray.length; i++) {
            const barHeight = this.dataArray[i] / 2;
            // Use Samaaveda Blue
            this.ctx.fillStyle = `rgb(88, 166, 255)`;
            this.ctx.fillRect(x, this.canvas.height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }
    }
}

window.visualizer = new Visualizer();
