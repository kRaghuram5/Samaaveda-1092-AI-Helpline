/**
 * Citizen UI Logic
 */
class CitizenUI {
    constructor() {
        this.selectedLanguage = 'auto';
        this.init();
    }

    init() {
        // Language buttons
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.selectedLanguage = btn.dataset.lang;
                console.log('[Citizen] Language selected:', this.selectedLanguage);
                
                // Update Badge
                document.getElementById('citizen-lang').innerText = btn.innerText.toUpperCase();
            });
        });

        // Mic button
        const micBtn = document.getElementById('mic-btn');
        micBtn.addEventListener('click', async () => {
            if (micBtn.classList.contains('recording')) {
                await this.stopRecording();
            } else {
                await this.startRecording();
            }
        });

        // Correction button
        document.getElementById('btn-submit-correction').addEventListener('click', () => {
            const correction = document.getElementById('citizen-correction-input').value;
            if (correction) {
                console.log('[Citizen] Submitting correction:', correction);
                window.wsClient.sendJSON({ 
                    type: 'verification_response', 
                    response: 'partial', // Assume partial if they are correcting
                    correction: correction 
                });
                // Clear and hide
                document.getElementById('citizen-correction-input').value = '';
                document.getElementById('correction-area').style.display = 'none';
            }
        });
    }

    async startRecording() {
        // Clear previous state if it exists
        if (window.app) {
            window.app.resetUIForNewCase();
        }
        
        try {
            const ok = await window.audioCapture.start(this.selectedLanguage);
            if (ok) {
                document.getElementById('mic-btn').classList.add('recording');
                document.getElementById('status-text').innerText = 'Listening...';
                document.getElementById('live-transcript-preview').innerText = 'Listening to your voice...';
            }
        } catch (err) {
            console.error('Mic start error:', err);
        }
    }

    async stopRecording() {
        await window.audioCapture.stop();
        document.getElementById('mic-btn').classList.remove('recording');
        document.getElementById('status-text').innerText = 'Processing...';
        
        // Tell backend to stop and process
        window.wsClient.sendJSON({ type: 'stop_recording' });
    }
}

window.citizenUI = new CitizenUI();
