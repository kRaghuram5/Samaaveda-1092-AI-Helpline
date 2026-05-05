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
        // Check if WebSocket client is available
        if (!window.wsClient) {
            console.warn('[App] WebSocket client not available, retrying in 100ms');
            setTimeout(() => this.init(), 100);
            return;
        }

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
        const fullTranscript = document.getElementById('full-transcript');
        if (fullTranscript) fullTranscript.innerText = 'Waiting for caller...';
        
        const livePreview = document.getElementById('live-transcript-preview');
        if (livePreview) livePreview.innerText = 'Awaiting voice input...';
        
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
        const item = document.createElement('div');
        item.className = 'reason-item';
        item.innerHTML = `<span>${key}:</span> ${value}`;
        log.prepend(item);
        
        // Keep only last 8 items to prevent stacking
        const items = log.querySelectorAll('.reason-item');
        if (items.length > 8) {
            items[items.length - 1].remove();
        }
        
        // Pulse the indicator
        const indicator = document.getElementById('thinking-indicator');
        indicator.style.display = 'inline-block';
        setTimeout(() => indicator.style.display = 'none', 1000);
    }

    handleStatus(data) {
        console.log('[App] handleStatus:', data);
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
        if (data.state === 'verified') {
            console.log('[App] Analysis complete, clearing processing flag');
            this.isProcessing = false;
            this.updatePipeline('verifying');
            this.addReasoning('System', '✓ Analysis complete');
            
            // Show verification UI
            document.getElementById('verification-loop').style.display = 'flex';
            document.getElementById('verification-loop').style.borderColor = '#ffb800';
        }
        if (data.state === 'awaiting_verification') {
            this.updatePipeline('verifying');
            this.addReasoning('Logic', 'Matching against Vector Memory...');
        }
    }

    handleTranscript(data) {
        if (data.is_final) {
            const ft = document.getElementById('full-transcript');
            if (ft) ft.innerText = data.text;
            
            const ltp = document.getElementById('live-transcript-preview');
            if (ltp) ltp.innerText = data.text;
            
            const cl = document.getElementById('citizen-lang');
            if (cl) cl.innerText = data.language.toUpperCase();
            
            this.addReasoning('Transcription', `Detected ${data.language} with ${Math.round(data.confidence * 100)}% confidence`);
            this.updatePipeline('thinking');
        }
    }

    handleSummary(data) {
        console.log('[App] handleSummary called with:', data);
        
        const d = data.data;
        console.log('[App] Extracted data:', d);
        
        document.getElementById('field-intent').value = d.intent || '';
        document.getElementById('field-issue-type').value = d.issue_type || '';
        document.getElementById('field-location').value = d.location || '';
        document.getElementById('field-duration').value = d.duration || 'not_specified';
        
        console.log(`[App] Updated fields: intent=${d.intent}, duration=${d.duration}`);
        
        this.addReasoning('Extracted', `Intent: ${d.issue_type} | Location: ${d.location} | Duration: ${d.duration || 'N/A'}`);
        
        // Update emotion and urgency from LLM output
        if (d.emotion) {
            document.getElementById('emotion-val').innerText = d.emotion.toUpperCase();
        }
        if (d.urgency_level) {
            const urgencyEl = document.getElementById('urgency-val');
            urgencyEl.innerText = d.urgency_level.toUpperCase();
            
            // Color code urgency
            urgencyEl.className = 'stat-val';
            if (d.urgency_level === 'critical' || d.urgency_level === 'CRITICAL') {
                urgencyEl.classList.add('val-high');
                document.getElementById('urgency-card').classList.add('urgency-high');
            } else if (d.urgency_level === 'high' || d.urgency_level === 'HIGH') {
                urgencyEl.classList.add('val-high');
                document.getElementById('urgency-card').classList.add('urgency-high');
            } else {
                urgencyEl.classList.add('val-low');
            }
        }
        
        if (d.dialect_notes) this.addReasoning('Dialect', d.dialect_notes);
    }

    handleEmotion(data) {
        console.log('[App] handleEmotion called with:', data);
        
        const emotionEl = document.getElementById('emotion-val');
        const urgencyEl = document.getElementById('urgency-val');
        const urgencyCard = document.getElementById('urgency-card');

        // Use primary_emotion not primary
        const emotion = data.primary_emotion || data.primary || 'NEUTRAL';
        const urgency = data.urgency_level || 'low';

        console.log(`[App] Setting emotion=${emotion}, urgency=${urgency}`);
        
        emotionEl.innerText = emotion.toUpperCase();
        urgencyEl.innerText = urgency.toUpperCase();
        
        // Remove classes
        urgencyEl.className = 'stat-val';
        urgencyCard.classList.remove('urgency-high');

        if (urgency === 'high' || urgency === 'critical') {
            urgencyEl.classList.add('val-high');
            urgencyCard.classList.add('urgency-high');
            this.addReasoning('Alert', 'High Urgency detected in voice sentiment');
        } else if (urgency === 'medium') {
            urgencyEl.classList.add('val-medium');
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
            
            // Show submit dialog
            this.showSubmitDialog();
            
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
                if (btn) {
                    btn.disabled = false;
                    btn.style.opacity = '';
                }
            });
        }
    }

    showSubmitDialog() {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;
        
        // Create dialog
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: var(--glass-bg);
            border: 2px solid var(--accent-green);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            text-align: center;
            color: white;
            font-family: Inter, sans-serif;
        `;
        
        dialog.innerHTML = `
            <h2 style="margin-bottom: 15px; font-size: 1.5rem;">✓ Submit Case</h2>
            <p style="margin-bottom: 30px; font-size: 1.1rem; color: #aaa;">
                Ready to forward this case to the human agent?
            </p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button id="submit-yes" style="
                    background: linear-gradient(135deg, #00ff88, #00bd65);
                    border: none;
                    padding: 12px 30px;
                    border-radius: 10px;
                    color: black;
                    font-weight: 600;
                    cursor: pointer;
                    font-size: 1rem;
                ">✓ SUBMIT</button>
                <button id="submit-no" style="
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.3);
                    padding: 12px 30px;
                    border-radius: 10px;
                    color: white;
                    font-weight: 600;
                    cursor: pointer;
                    font-size: 1rem;
                ">✗ KEEP REVIEWING</button>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // Handle YES
        document.getElementById('submit-yes').addEventListener('click', () => {
            this.addReasoning('Agent', '✓ Forwarding to human agent...');
            
            // Send to backend
            window.wsClient.sendJSON({
                type: 'agent_submit_case',
                action: 'submit_to_human_agent'
            });
            
            // Remove dialog
            overlay.remove();
            
            // Save data to localStorage
            const caseData = {
                intent: document.getElementById('field-intent').value,
                issueType: document.getElementById('field-issue-type').value,
                location: document.getElementById('field-location').value,
                duration: document.getElementById('field-duration').value,
                urgency: document.getElementById('urgency-val').innerText,
                confidence: document.getElementById('confidence-val').innerText,
                sentiment: document.getElementById('emotion-val').innerText,
                state: 'SUBMITTED'
            };
            localStorage.setItem('final_case_data', JSON.stringify(caseData));
            
            // Redirect to final page
            window.location.href = '/final';
        });
        
        // Handle NO
        document.getElementById('submit-no').addEventListener('click', () => {
            overlay.remove();
            document.getElementById('verification-loop').style.display = 'block';
        });
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
        
        // Save to localStorage and redirect
        const caseData = {
            intent: document.getElementById('field-intent').value || 'Not extracted',
            issueType: document.getElementById('field-issue-type').value || 'Unknown',
            location: document.getElementById('field-location').value || 'Unknown',
            duration: document.getElementById('field-duration').value || 'Unknown',
            urgency: document.getElementById('urgency-val').innerText,
            confidence: document.getElementById('confidence-val').innerText,
            sentiment: document.getElementById('emotion-val').innerText,
            state: 'ESCALATED'
        };
        localStorage.setItem('final_case_data', JSON.stringify(caseData));
        
        // Wait 2.5s so agent can see the escalation text, then redirect
        setTimeout(() => {
            window.location.href = '/final';
        }, 2500);
    }

    handleActionResult(data) {
        console.log('[App] Action result received:', data.message);
        
        this.updatePipeline('final');
        this.addReasoning('Agent', `✓ ${data.message}`);
        
        const finalStep = document.getElementById('step-final');
        finalStep.classList.add('finished');
        finalStep.innerHTML = '<i>5</i> <span>RESOLVED</span>';
    }
}


try {
    window.app = new SamaavedaApp();
    console.log('[App] SamaavedaApp instance created successfully');
} catch (error) {
    console.error('[App] Failed to create SamaavedaApp:', error);
    // Create a dummy app object so the rest of the app can still run
    window.app = {
        handleSummary: () => {},
        handleEmotion: () => {},
        handleStatus: () => {},
        handleTranscript: () => {},
        handleConfidence: () => {},
        handleVerification: () => {},
        handleEscalation: () => {},
        handleActionResult: () => {},
        handleVerificationResult: () => {},
        addReasoning: () => {},
        updatePipeline: () => {},
        resetUIForNewCase: () => {}
    };
}
