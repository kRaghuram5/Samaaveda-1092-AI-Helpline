/**
 * Agent Dashboard — handles agent-side UI updates and interactions.
 */
class AgentDashboard {
    constructor() {
        this.init();
    }

    init() {
        console.log('[Agent] UI Initialized');

        // Helper to disable button temporarily
        const disableButtonTemporarily = (id, duration = 3000) => {
            const el = document.getElementById(id);
            el.disabled = true;
            el.style.opacity = '0.5';
            setTimeout(() => {
                el.disabled = false;
                el.style.opacity = '';
            }, duration);
        };

        // Helper to show button click
        const flashBtn = (id) => {
            const el = document.getElementById(id);
            el.style.transform = 'scale(0.95)';
            setTimeout(() => el.style.transform = '', 100);
        };

        // --- 1. VERIFICATION LOOP BUTTONS ---
        document.getElementById('btn-correct').addEventListener('click', () => {
            console.log('[Agent] Correct Clicked');
            if (window.app.isProcessing) return; // Guard
            
            window.app.isProcessing = true;
            flashBtn('btn-correct');
            disableButtonTemporarily('btn-correct', 2000);
            disableButtonTemporarily('btn-partial', 2000);
            disableButtonTemporarily('btn-wrong', 2000);
            
            window.wsClient.sendJSON({ type: 'verification_response', response: 'yes' });
        });

        document.getElementById('btn-partial').addEventListener('click', () => {
            console.log('[Agent] Partial Clicked');
            if (window.app.isProcessing) return; // Guard
            
            window.app.isProcessing = true;
            flashBtn('btn-partial');
            disableButtonTemporarily('btn-correct', 2000);
            disableButtonTemporarily('btn-partial', 2000);
            disableButtonTemporarily('btn-wrong', 2000);
            
            window.wsClient.sendJSON({ type: 'verification_response', response: 'partial' });
        });

        document.getElementById('btn-wrong').addEventListener('click', () => {
            console.log('[Agent] Wrong Clicked');
            if (window.app.isProcessing) return; // Guard
            
            window.app.isProcessing = true;
            flashBtn('btn-wrong');
            disableButtonTemporarily('btn-correct', 2000);
            disableButtonTemporarily('btn-partial', 2000);
            disableButtonTemporarily('btn-wrong', 2000);
            
            window.wsClient.sendJSON({ type: 'verification_response', response: 'no' });
        });

        // --- 2. ESCALATION BUTTON ---
        document.getElementById('escalate-btn').addEventListener('click', () => {
            console.log('[Agent] Escalate Clicked');
            if (window.app.isProcessing) return; 
            
            // Immediate UI feedback
            window.app.isProcessing = true;
            flashBtn('escalate-btn');
            const btn = document.getElementById('escalate-btn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ESCALATING...';
            btn.style.background = 'var(--accent-primary)';
            
            window.wsClient.sendJSON({
                type: 'agent_escalate',
                reason: 'Agent manually requested escalation'
            });
        });


        // --- 3. INLINE EDITING FOR SUMMARY ---
        ['intent', 'issue-type', 'location', 'duration'].forEach(field => {
            const el = document.getElementById(`field-${field}`);
            if (el) {
                el.addEventListener('change', () => {
                    console.log(`[Agent] Editing ${field} to ${el.value}`);
                    window.wsClient.sendJSON({
                        type: 'agent_edit',
                        field: field.replace('-', '_'),
                        value: el.value
                    });
                });
            }
        });
    }
}

window.agentDashboard = new AgentDashboard();
