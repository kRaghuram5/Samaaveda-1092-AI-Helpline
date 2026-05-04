/**
 * Agent Dashboard — handles agent-side UI updates and interactions.
 */
class AgentDashboard {
    constructor() {
        this.init();
    }

    init() {
        console.log('[Agent] UI Initialized');

        // Helper to show button click
        const flashBtn = (id) => {
            const el = document.getElementById(id);
            el.style.transform = 'scale(0.95)';
            setTimeout(() => el.style.transform = '', 100);
        };

        // --- 1. VERIFICATION LOOP BUTTONS ---
        document.getElementById('btn-correct').addEventListener('click', () => {
            console.log('[Agent] Correct Clicked');
            flashBtn('btn-correct');
            window.wsClient.sendJSON({ type: 'verification_response', response: 'yes' });
        });

        document.getElementById('btn-partial').addEventListener('click', () => {
            console.log('[Agent] Partial Clicked');
            flashBtn('btn-partial');
            window.wsClient.sendJSON({ type: 'verification_response', response: 'partial' });
        });

        document.getElementById('btn-wrong').addEventListener('click', () => {
            console.log('[Agent] Wrong Clicked');
            flashBtn('btn-wrong');
            window.wsClient.sendJSON({ type: 'verification_response', response: 'no' });
        });

        // --- 2. ESCALATION BUTTON ---
        document.getElementById('escalate-btn').addEventListener('click', () => {
            console.log('[Agent] Escalate Clicked');
            flashBtn('escalate-btn');
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
