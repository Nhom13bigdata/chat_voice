/**
 * Medical Intake Voice Assistant - Frontend Logic
 * Supports 16kHz PCM Input and 24kHz PCM Output
 */

class MedicalIntakeApp {
    constructor() {
        this.ws = null;
        this.audioContext = null;
        this.processor = null;
        this.inputSource = null;
        this.stream = null;
        this.isRecording = false;
        this.reconnectTimeout = null;
        this.lastAssistantBubble = null;
        this.lastPatientBubble = null;

        // Audio Settings
        this.INPUT_SAMPLE_RATE = 16000;
        this.OUTPUT_SAMPLE_RATE = 24000;
        this.BUFFER_SIZE = 4096;

        // DOM Elements
        this.elements = {
            startBtn: document.getElementById('start-btn'),
            stopBtn: document.getElementById('stop-btn'),
            transcript: document.getElementById('transcript'),
            statusMsg: document.getElementById('status-msg'),
            orb: document.getElementById('orb'),
            dot: document.getElementById('connection-dot'),
            connText: document.getElementById('connection-text'),
            dataPanel: document.getElementById('data-panel'),
            dataContent: document.getElementById('data-content'),
            toggleData: document.getElementById('toggle-data'),
            closeData: document.getElementById('close-data'),
            setupModal: document.getElementById('setup-modal'),
            apiKeyInput: document.getElementById('api-key-input'),
            saveApiKey: document.getElementById('save-api-key'),
            closeModal: document.getElementById('close-modal'),
            navLinks: document.querySelectorAll('.nav-links li'),
            views: document.querySelectorAll('.view'),
            debugInput: document.getElementById('debug-input'),
            sendDebugBtn: document.getElementById('send-debug-btn')
        };

        this.init();
    }

    init() {
        // Event Listeners
        this.elements.startBtn.addEventListener('click', () => this.startSession());
        this.elements.stopBtn.addEventListener('click', () => this.stopSession());
        this.elements.toggleData.addEventListener('click', () => this.elements.dataPanel.classList.toggle('open'));
        this.elements.closeData.addEventListener('click', () => this.elements.dataPanel.classList.remove('open'));
        
        this.elements.saveApiKey.addEventListener('click', () => {
            const key = this.elements.apiKeyInput.value;
            if (key) localStorage.setItem('gemini_api_key', key);
            this.elements.setupModal.classList.add('hidden');
            this.connect();
        });

        this.elements.closeModal.addEventListener('click', () => {
            this.elements.setupModal.classList.add('hidden');
            this.connect();
        });
        
        // Debug Chat
        this.elements.sendDebugBtn.addEventListener('click', () => this.sendDebugMessage());
        this.elements.debugInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendDebugMessage();
        });

        // Navigation
        this.elements.navLinks.forEach(link => {
            link.addEventListener('click', () => {
                const viewId = link.getAttribute('data-view');
                this.switchView(viewId);
            });
        });

        // Check for saved API key
        if (!localStorage.getItem('gemini_api_key')) {
            // Optional: show modal on load if you want
            // this.elements.setupModal.classList.remove('hidden');
        }
    }

    switchView(viewId) {
        this.elements.navLinks.forEach(l => l.classList.remove('active'));
        document.querySelector(`[data-view="${viewId}"]`).classList.add('active');
        
        this.elements.views.forEach(v => v.classList.remove('active'));
        document.getElementById(`${viewId}-view`).classList.add('active');
    }

    async startSession() {
        try {
            await this.initAudio();
            this.connect();
        } catch (err) {
            console.error('Failed to start session:', err);
            this.updateStatus('Error: ' + err.message, 'error');
        }
    }

    async initAudio() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
            sampleRate: this.INPUT_SAMPLE_RATE // Try to force 16kHz if browser allows
        });

        // If context sample rate isn't 16kHz, we'll need to manually downsample
        console.log('AudioContext Sample Rate:', this.audioContext.sampleRate);

        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.inputSource = this.audioContext.createMediaStreamSource(this.stream);
        
        // ScriptProcessor is deprecated but widely compatible for simple PCM work
        this.processor = this.audioContext.createScriptProcessor(this.BUFFER_SIZE, 1, 1);
        
        this.processor.onaudioprocess = (e) => {
            if (!this.isRecording || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            
            // Convert Float32 to Int16
            const pcmData = this.floatTo16BitPCM(inputData);
            this.ws.send(pcmData);
        };

        this.inputSource.connect(this.processor);
        this.processor.connect(this.audioContext.destination);
    }

    floatTo16BitPCM(input) {
        const output = new Int16Array(input.length);
        for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return output.buffer;
    }

    connect() {
        const apiKey = localStorage.getItem('gemini_api_key') || '';
        const url = `ws://localhost:8000/ws${apiKey ? `?api_key=${apiKey}` : ''}`;
        
        this.ws = new WebSocket(url);
        this.ws.binaryType = 'arraybuffer';

        this.ws.onopen = () => {
            this.updateStatus('Connected', 'online');
            this.elements.startBtn.classList.add('hidden');
            this.elements.stopBtn.classList.remove('hidden');
            document.body.classList.add('active-session');
            this.isRecording = true;
        };

        this.ws.onmessage = (event) => {
            if (event.data instanceof ArrayBuffer) {
                this.playAudio(event.data);
            } else {
                const msg = JSON.parse(event.data);
                this.handleJsonMessage(msg);
            }
        };

        this.ws.onclose = () => {
            this.updateStatus('Disconnected', 'offline');
            this.stopSession();
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket Error:', err);
            this.addTranscript('System', 'Connection error occurred.', 'system');
        };
    }

    handleJsonMessage(msg) {
        switch (msg.type) {
            case 'status':
                this.elements.statusMsg.innerText = msg.message;
                break;
            case 'transcript':
                this.addTranscript(msg.role, msg.text, msg.role);
                break;
            case 'turn_complete':
                // Reset the active bubbles when a turn is finished
                this.lastAssistantBubble = null;
                this.lastPatientBubble = null;
                break;
            case 'extracted_data':
                this.updateDataPanel(msg.data);
                break;
            case 'intake_complete':
                this.addTranscript('System', 'Intake completed successfully.', 'system');
                this.elements.statusMsg.innerText = 'Intake Complete';
                break;
            case 'error':
                this.addTranscript('Error', msg.message, 'system');
                break;
        }
    }

    playAudio(arrayBuffer) {
        // AI Audio is 24kHz 16-bit PCM Mono
        const int16Array = new Int16Array(arrayBuffer);
        const float32Array = new Float32Array(int16Array.length);
        
        for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
        }

        const buffer = this.audioContext.createBuffer(1, float32Array.length, this.OUTPUT_SAMPLE_RATE);
        buffer.getChannelData(0).set(float32Array);

        const source = this.audioContext.createBufferSource();
        source.buffer = buffer;
        source.connect(this.audioContext.destination);
        source.start();
    }

    addTranscript(role, text, type) {
        // Skip empty text
        if (!text || text.trim() === '') return;

        // Implementation of intelligent appending
        if (type === 'assistant' && this.lastAssistantBubble) {
            this.lastAssistantBubble.innerText += ' ' + text;
            this.elements.transcript.scrollTop = this.elements.transcript.scrollHeight;
            return;
        }
        
        if (type === 'patient' && this.lastPatientBubble) {
            this.lastPatientBubble.innerText += ' ' + text;
            this.elements.transcript.scrollTop = this.elements.transcript.scrollHeight;
            return;
        }

        // Otherwise create new bubble
        const entry = document.createElement('div');
        entry.className = `transcript-entry ${type}`;
        entry.innerText = text;
        this.elements.transcript.appendChild(entry);
        this.elements.transcript.scrollTop = this.elements.transcript.scrollHeight;

        // Save reference to the active bubble
        if (type === 'assistant') this.lastAssistantBubble = entry;
        if (type === 'patient') this.lastPatientBubble = entry;
    }

    updateDataPanel(data) {
        this.elements.dataContent.innerHTML = '';
        
        const sections = [
            { key: 'chief_complaint', label: 'Chief Complaint' },
            { key: 'current_medications', label: 'Medications', isList: true },
            { key: 'allergies', label: 'Allergies', isList: true },
            { key: 'past_medical_history', label: 'Medical History', isObj: true },
            { key: 'social_history', label: 'Social History', isObj: true }
        ];

        sections.forEach(sec => {
            const val = data[sec.key];
            if (!val || (Array.isArray(val) && val.length === 0)) return;

            const card = document.createElement('div');
            card.className = 'data-card';
            card.innerHTML = `<h4>${sec.label}</h4>`;

            if (sec.isList) {
                val.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'data-item';
                    itemDiv.innerHTML = `<span class="data-value">• ${JSON.stringify(item).replace(/[{}"]/g, '')}</span>`;
                    card.appendChild(itemDiv);
                });
            } else if (sec.isObj) {
                Object.entries(val).forEach(([k, v]) => {
                    if (v && v.length > 0) {
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'data-item';
                        itemDiv.innerHTML = `<span class="data-label">${k.replace(/_/g, ' ')}</span><span class="data-value">${v}</span>`;
                        card.appendChild(itemDiv);
                    }
                });
            } else {
                card.innerHTML += `<span class="data-value">${val}</span>`;
            }

            this.elements.dataContent.appendChild(card);
        });

        if (this.elements.dataContent.innerHTML === '') {
            this.elements.dataContent.innerHTML = '<div class="empty-state">No data extracted yet.</div>';
        } else {
            // Open panel on first data
            this.elements.dataPanel.classList.add('open');
        }
    }

    updateStatus(message, state) {
        this.elements.connText.innerText = message;
        this.elements.dot.className = `dot ${state}`;
    }

    stopSession() {
        this.isRecording = false;
        
        if (this.ws) {
            if (this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'end_session' }));
            }
            this.ws.close();
            this.ws = null;
        }

        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }

        if (this.audioContext) {
            // this.audioContext.close(); // Not closing to allow reuse
        }

        this.elements.startBtn.classList.remove('hidden');
        this.elements.stopBtn.classList.add('hidden');
        document.body.classList.remove('active-session');
        this.elements.statusMsg.innerText = 'Session ended';
    }

    sendDebugMessage() {
        const text = this.elements.debugInput.value.trim();
        if (text && this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('Sending debug text:', text);
            this.ws.send(JSON.stringify({
                type: 'chat_text',
                text: text
            }));
            this.elements.debugInput.value = '';
        }
    }
}

// Instantiate App
window.addEventListener('DOMContentLoaded', () => {
    window.app = new MedicalIntakeApp();
});
