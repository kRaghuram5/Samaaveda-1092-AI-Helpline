/**
 * Main Application Orchestrator
 */
class SamaavedaApp {
    constructor() {
        this.currentStep = 'listening';
        this.init();
    }

    init() {
        // Event Listeners for WebSocket events
        window.wsClient.on('status', (data) => this.handleStatus(data));
        window.wsClient.on('transcript_update', (data) => this.handleTranscript(data));
        window.wsClient.on('structured_summary', (data) => this.handleSummary(data));
        window.wsClient.on('emotion', (data) => this.handleEmotion(data));
        window.wsClient.on('confidence_update', (data) => this.handleConfidence(data));
        window.wsClient.on('verification_prompt', (data) => this.handleVerification(data));
        window.wsClient.on('escalation_alert', (data) => this.handleEscalation(data));
        window.wsClient.on('agent_action_result', (data) => this.handleActionResult(data));
        window.wsClient.on('verification_result', (data) => this.handleVerificationResult(data));
        
        console.log('[App] Initialized and connected to socket events.');
    }

    updatePipeline(step) {
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
        const el = document.getElementById(`step-${step}`);
        if (el) el.classList.add('active');
        this.currentStep = step;
    }

    addReasoning(key, value) {
        const log = document.getElementById('reasoning-log');
        const item = document.createElement('div');
        item.className = 'reason-item';
        item.innerHTML = `<span>${key}:</span> ${value}`;
        log.prepend(item);
        
        // Pulse the indicator
        const indicator = document.getElementById('thinking-indicator');
        indicator.style.display = 'inline-block';
        setTimeout(() => indicator.style.display = 'none', 1000);
    }

    handleStatus(data) {
        document.getElementById('status-text').innerText = data.message;
        
        if (data.state === 'recording') this.updatePipeline('listening');
        if (data.state === 'processing') {
            this.updatePipeline('transcribing');
            this.addReasoning('Action', 'Audio chunk received, processing STT...');
        }
        if (data.state === 'analyzing') {
            this.updatePipeline('thinking');
            this.addReasoning('LLM', 'Starting semantic analysis...');
        }
        if (data.state === 'awaiting_verification') {
            this.updatePipeline('verifying');
            this.addReasoning('Logic', 'Matching against Vector Memory...');
        }
    }

    handleTranscript(data) {
        if (data.is_final) {
            document.getElementById('full-transcript').innerText = data.text;
            document.getElementById('live-transcript-preview').innerText = data.text;
            document.getElementById('citizen-lang').innerText = data.language.toUpperCase();
            
            this.addReasoning('Transcription', `Detected ${data.language} with ${Math.round(data.confidence * 100)}% confidence`);
            this.updatePipeline('thinking');
        }
    }

    handleSummary(data) {
        const d = data.data;
        document.getElementById('field-intent').value = d.intent;
        document.getElementById('field-issue-type').value = d.issue_type;
        document.getElementById('field-location').value = d.location;
        document.getElementById('field-duration').value = d.duration;
        
        this.addReasoning('Extracted', `Intent: ${d.issue_type} | Location: ${d.location}`);
        if (d.dialect_notes) this.addReasoning('Dialect', d.dialect_notes);
    }

    handleEmotion(data) {
        const emotionEl = document.getElementById('emotion-val');
        const urgencyEl = document.getElementById('urgency-val');
        const urgencyCard = document.getElementById('urgency-card');

        emotionEl.innerText = data.primary.toUpperCase();
        urgencyEl.innerText = data.urgency_level.toUpperCase();
        
        // Remove classes
        urgencyEl.className = 'stat-val';
        urgencyCard.classList.remove('urgency-high');

        if (data.urgency_level === 'high' || data.urgency_level === 'critical') {
            urgencyEl.classList.add('val-high');
            urgencyCard.classList.add('urgency-high');
            this.addReasoning('Alert', 'High Urgency detected in voice sentiment');
        } else {
            urgencyEl.classList.add('val-low');
        }
    }

    handleConfidence(data) {
        const confEl = document.getElementById('confidence-val');
        const confStatus = document.getElementById('confidence-status');
        const suggestEl = document.getElementById('suggest-action');
        
        const score = Math.round(data.score * 100);
        confEl.innerText = `${score}%`;
        
        if (score > 80) {
            confEl.className = 'stat-val val-success';
            confStatus.innerText = 'HIGH CONFIDENCE';
            document.getElementById('suggested-action').innerText = 'PROCEED TO CONFIRM';
        } else if (score > 60) {
            confEl.className = 'stat-val val-medium';
            confStatus.innerText = 'NEEDS VERIFICATION';
            document.getElementById('suggested-action').innerText = 'USE VERIFICATION LOOP';
        } else {
            confEl.className = 'stat-val val-high';
            confStatus.innerText = 'LOW CONFIDENCE';
            document.getElementById('suggested-action').innerText = 'RECOMMEND ESCALATION';
            this.addReasoning('Warning', 'Confidence below threshold. Guardrails triggered.');
        }
    }

    handleVerification(data) {
        document.getElementById('verification-loop').style.display = 'block';
        document.getElementById('confirmation-sentence').innerText = data.message;
        this.updatePipeline('verifying');
    }

    handleVerificationResult(data) {
        this.addReasoning('Verification', `Citizen response: ${data.state}`);
        if (data.action === 'confirm') {
            this.updatePipeline('final');
            document.getElementById('step-verifying').classList.add('finished');
            document.getElementById('correction-area').style.display = 'none';
        } else if (data.action === 're_process') {
            // Show correction box to citizen
            document.getElementById('correction-area').style.display = 'block';
            this.addReasoning('Loop', 'Requesting correction from citizen...');
        }
    }

    handleEscalation(data) {
        this.updatePipeline('final');
        document.getElementById('step-final').innerText = '🚨 ESCALATED';
        document.getElementById('step-final').classList.add('val-high');
        this.addReasoning('System', `ESCALATED: ${data.reason}`);
    }

    handleActionResult(data) {
        this.updatePipeline('final');
        this.addReasoning('Agent', `Action taken: ${data.message}`);
        document.getElementById('step-final').classList.add('finished');
    }
}

window.app = new SamaavedaApp();
