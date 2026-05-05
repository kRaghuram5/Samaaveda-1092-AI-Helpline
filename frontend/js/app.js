/**
 * Main Application Orchestrator
 */
class SamaavedaApp {
    constructor() {
        this.currentStep = 'listening';
        this.isProcessing = false; // Guard against multiple clicks
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

    /**
     * RESET UI FOR NEW CASE - Clear all logs and return to listening state
     */
    resetUIForNewCase() {
        console.log('[App] Resetting UI for new case...');
        
        // 1. Clear reasoning log completely
        const reasoningLog = document.getElementById('reasoning-log');
        reasoningLog.innerHTML = '<div class="reason-item"><span>Status:</span> System Idle</div>';
        
        // 2. Hide all verification UI
        document.getElementById('verification-loop').style.display = 'none';
        document.getElementById('verification-loop').style.borderColor = '';
        document.getElementById('correction-area').style.display = 'none';
        
        // 3. Clear all input fields
        document.getElementById('field-intent').value = '';
        document.getElementById('field-issue-type').value = '';
        document.getElementById('field-location').value = '';
        document.getElementById('field-duration').value = '';
        document.getElementById('citizen-correction-input').value = '';
        
        // 4. Clear all transcript displays
        document.getElementById('full-transcript').innerText = 'Waiting for caller...';
        document.getElementById('live-transcript-preview').innerText = 'Awaiting voice input...';
        
        // 5. Reset all stats to default
        document.getElementById('confidence-val').innerText = '0%';
        document.getElementById('confidence-status').innerText = '--';
        document.getElementById('emotion-val').innerText = 'NEUTRAL';
        document.getElementById('urgency-val').innerText = 'LOW';
        document.getElementById('suggested-action').innerText = 'IDLE';
        document.getElementById('status-text').innerText = 'System Ready';
        
        // 6. Reset confidence styles
        const confEl = document.getElementById('confidence-val');
        confEl.className = 'stat-val';
        
        // 7. Reset urgency card
        const urgencyCard = document.getElementById('urgency-card');
        const urgencyVal = document.getElementById('urgency-val');
        urgencyCard.classList.remove('urgency-high');
        urgencyVal.className = 'stat-val val-low';
        
        // 8. Reset pipeline steps
        const stepElements = document.querySelectorAll('.step');
        stepElements.forEach(s => {
            s.classList.remove('active', 'finished');
        });
        document.getElementById('step-listening').classList.add('active');
        
        // 9. Reset final step display
        const finalStep = document.getElementById('step-final');
        finalStep.innerHTML = '<i>5</i> <span>Final Action</span>';
        finalStep.classList.remove('val-high', 'finished');
        
        // 10. Re-enable all buttons
        document.getElementById('btn-correct').disabled = false;
        document.getElementById('btn-correct').style.opacity = '';
        document.getElementById('btn-partial').disabled = false;
        document.getElementById('btn-partial').style.opacity = '';
        document.getElementById('btn-wrong').disabled = false;
        document.getElementById('btn-wrong').style.opacity = '';
        document.getElementById('escalate-btn').disabled = false;
        document.getElementById('escalate-btn').style.opacity = '';
        
        // 11. Reset processing flag
        this.isProcessing = false;
        
        // 12. Enable mic button
        const micBtn = document.getElementById('mic-btn');
        micBtn.disabled = false;
        micBtn.classList.remove('recording');
        
        console.log('[App] UI reset complete');
    }


    updatePipeline(step) {
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'finished'));
        const el = document.getElementById(`step-${step}`);
        if (el) el.classList.add('active');
        this.currentStep = step;
    }

    addReasoning(key, value) {
        const log = document.getElementById('reasoning-log');
        
        // Check if key already exists in the log
        let existingItem = null;
        const items = log.querySelectorAll('.reason-item');
        for (const item of items) {
            const span = item.querySelector('span');
            if (span && span.innerText.includes(key)) {
                existingItem = item;
                break;
            }
        }

        if (existingItem) {
            // Update existing item with animation
            existingItem.style.opacity = '0.5';
            existingItem.innerHTML = `<span>${key}:</span> ${value}`;
            setTimeout(() => existingItem.style.opacity = '1', 50);
            
            // Move to top to show it's the latest update
            log.prepend(existingItem);
        } else {
            // Create new item
            const item = document.createElement('div');
            item.className = 'reason-item';
            item.innerHTML = `<span>${key}:</span> ${value}`;
            log.prepend(item);
            
            // Limit total items
            if (items.length >= 6) {
                items[items.length - 1].remove();
            }
        }
        
        // Pulse the indicator
        const indicator = document.getElementById('thinking-indicator');
        if (indicator) {
            indicator.style.display = 'inline-block';
            setTimeout(() => indicator.style.display = 'none', 1000);
        }
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
        console.log('[App] Verification result:', data);
        this.addReasoning('Verification', `Citizen feedback: ${data.state.toUpperCase()}`);
        
        if (data.action === 'confirm') {
            // Clear verification loop
            document.getElementById('verification-loop').style.display = 'none';
            document.getElementById('correction-area').style.display = 'none';
            
            // Show confirmed state
            this.updatePipeline('final');
            const finalStep = document.getElementById('step-final');
            finalStep.classList.add('finished');
            finalStep.innerHTML = '<i>5</i> <span>CONFIRMED</span>';
            
            this.addReasoning('System', '✓ DATA VALIDATED - Finalizing case...');
            this.addReasoning('Action', 'Case details synchronized with command center.');
            
            // Auto-reset after 3 seconds
            setTimeout(() => this.resetUIForNewCase(), 3000);
            
        } else if (data.action === 're_process') {
            // Entering confirmation loop
            this.updatePipeline('verifying');
            document.getElementById('correction-area').style.display = 'block';
            document.getElementById('citizen-correction-input').focus();
            
            this.addReasoning('Loop', 'Discrepancy detected. Entering correction loop...');
            this.addReasoning('AI', 'Awaiting citizen input to refine extraction.');
            
            // Visual feedback on the card
            const vCard = document.getElementById('verification-loop');
            vCard.style.borderColor = 'var(--warning)';
            document.getElementById('confirmation-sentence').innerText = "Please provide the correct details below.";
            
            // RESET PROCESSING to allow the loop to continue
            this.isProcessing = false;
            
            // Re-enable buttons if they were disabled
            ['btn-correct', 'btn-partial', 'btn-wrong'].forEach(id => {
                const btn = document.getElementById(id);
                btn.disabled = false;
                btn.style.opacity = '';
            });
        }
    }



    handleEscalation(data) {
        console.log('[App] Escalation received:', data.reason);
        
        // Show escalation visually immediately
        this.updatePipeline('final');
        
        // Hide verification UI
        document.getElementById('verification-loop').style.display = 'none';
        document.getElementById('correction-area').style.display = 'none';
        
        // Show escalation visually in the pipeline
        const finalStep = document.getElementById('step-final');
        finalStep.innerHTML = '<i>5</i> 🚨 ESCALATED';
        finalStep.classList.add('val-high', 'finished');
        
        this.addReasoning('System', `🚨 ESCALATED: ${data.reason}`);
        this.addReasoning('Action', 'Connecting to emergency dispatcher...');
        
        // Reset UI after 4 seconds (longer for user to see the result)
        setTimeout(() => this.resetUIForNewCase(), 4000);
    }

    handleActionResult(data) {
        console.log('[App] Action result received:', data.message);
        
        this.updatePipeline('final');
        this.addReasoning('Agent', `✓ ${data.message}`);
        
        const finalStep = document.getElementById('step-final');
        finalStep.classList.add('finished');
        finalStep.innerHTML = '<i>5</i> <span>RESOLVED</span>';
        
        // Reset UI after 3 seconds
        setTimeout(() => this.resetUIForNewCase(), 3000);
    }
}


window.app = new SamaavedaApp();
