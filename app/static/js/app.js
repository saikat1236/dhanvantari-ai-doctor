let currentView = 'patient';
let patientId = localStorage.getItem('dhanvantari_patient_id') || null;
let patientEmail = localStorage.getItem('dhanvantari_patient_email') || null;
let conversationId = null;
let activeReviewItemId = null;

// Live Doctor Call & Speech State
let isLiveCallActive = false;
let isVoiceMode = false;
let isListening = false;
let isProcessingTurn = false;
let isMicMuted = false;
let recognition = null;
const speechSynthesis = window.speechSynthesis;
let speechUtterance = null;
let listenTimeout = null;
let selectedVoiceLang = 'en-IN';
let currentAudioElement = null;

// Initialize SpeechRecognition if supported
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (patientId) {
        document.getElementById('consent-modal-overlay').style.display = 'none';
        const display = document.getElementById('patient-info-display');
        display.style.display = 'flex';
        display.querySelector('span').innerText = `Patient ID: ${patientId}`;
    }
    setupSpeechRecognition();
});

// View Swapper
function switchView(viewName) {
    currentView = viewName;
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.page-view').forEach(el => el.classList.remove('active'));

    if (viewName === 'patient') {
        document.getElementById('nav-patient').classList.add('active');
        document.getElementById('view-patient').classList.add('active');
        document.getElementById('view-title-text').innerText = 'Patient Triage Portal';
    } else if (viewName === 'doctor') {
        if (isLiveCallActive) {
            toggleLiveDoctorCall();
        }
        if (isVoiceMode) {
            document.getElementById('voice-mode-toggle').checked = false;
            disableVoiceMode();
        }
        document.getElementById('nav-doctor').classList.add('active');
        document.getElementById('view-doctor').classList.add('active');
        document.getElementById('view-title-text').innerText = 'RMP Doctor Dashboard';
        loadDoctorQueue();
    }
}

// Toast Helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = message;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// DPDP Consent Submission
async function submitConsentForm() {
    const email = document.getElementById('consent-patient-email').value;
    const agreed = document.getElementById('consent-checkbox-agreed').checked;

    if (!email) {
        showToast('Please enter your email.', 'error');
        return;
    }
    if (!agreed) {
        showToast('You must check the DPDP consent box to proceed.', 'error');
        return;
    }

    try {
        const response = await fetch('/api/auth/consent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: email,
                consent_scope: "Symptom analysis and triage consulting under India Telemedicine Guidelines 2020 and DPDP Act 2023."
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Consent registration failed.');
        }

        const data = await response.json();
        patientId = data.patient_id;
        patientEmail = data.email;
        
        localStorage.setItem('dhanvantari_patient_id', patientId);
        localStorage.setItem('dhanvantari_patient_email', patientEmail);

        document.getElementById('consent-modal-overlay').style.display = 'none';
        const display = document.getElementById('patient-info-display');
        display.style.display = 'flex';
        display.querySelector('span').innerText = `Patient ID: ${patientId}`;
        
        showToast('Consent captured. Secure channel opened.', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function ensurePatientConsent() {
    if (patientId) return true;
    try {
        const defaultEmail = `patient-${Math.random().toString(36).substring(2, 7)}@dhanvantari.in`;
        const response = await fetch('/api/auth/consent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: defaultEmail,
                consent_scope: "Symptom analysis and triage consulting under India Telemedicine Guidelines 2020 and DPDP Act 2023."
            })
        });
        if (response.ok) {
            const data = await response.json();
            patientId = data.patient_id;
            patientEmail = data.email;
            localStorage.setItem('dhanvantari_patient_id', patientId);
            localStorage.setItem('dhanvantari_patient_email', patientEmail);
            const modal = document.getElementById('consent-modal-overlay');
            if (modal) modal.style.display = 'none';
            const display = document.getElementById('patient-info-display');
            if (display) {
                display.style.display = 'flex';
                display.querySelector('span').innerText = `Patient ID: ${patientId}`;
            }
            return true;
        }
    } catch (e) {
        console.warn('Auto-consent registration error:', e);
    }
    return false;
}

// =======================================================
// 3D REALTIME LIVE DOCTOR CONSULTATION CALL MODE
// =======================================================

async function toggleLiveDoctorCall() {
    isLiveCallActive = !isLiveCallActive;
    const stage = document.getElementById('live-doctor-call-stage');
    const callBtn = document.getElementById('btn-toggle-live-call');
    const voiceToggle = document.getElementById('voice-mode-toggle');

    if (isLiveCallActive) {
        if (!patientId) {
            await ensurePatientConsent();
        }

        stage.classList.add('active');
        callBtn.classList.add('active');
        callBtn.innerHTML = '<span class="pulse-red-dot"></span> End 3D Doctor Call';
        
        voiceToggle.checked = true;
        isVoiceMode = true;
        isMicMuted = false;
        
        // Initialize 3D WebGL Three.js Visualizer
        if (typeof init3DDoctorVisualizer === 'function') {
            setTimeout(init3DDoctorVisualizer, 100);
        }

        // Connect mic stream to 3D audio analyser
        if (typeof connectMicrophoneToVisualizer === 'function') {
            connectMicrophoneToVisualizer();
        }

        updateLiveDoctorState('speaking', 'Dr. Dhanvantari connecting...');
        showToast('🔴 3D Live Doctor Consultation Started. Speak naturally.', 'success');

        // Initial Greeting
        const greetingText = selectedVoiceLang === 'hi-IN' 
            ? "नमस्ते! मैं डॉक्टर धनवंतरी हूँ। मैं आपको लाइव सुन रहा हूँ। आपकी क्या समस्या है? कृपया बताइए।"
            : "Hello, I am Dr. Dhanvantari. I am listening to you live in 3D. What symptoms are you experiencing today?";

        // Fetch natural neural VibeVoice audio
        try {
            const ttsResp = await fetch('/api/chat/tts/synthesize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: greetingText, language: selectedVoiceLang })
            });
            if (ttsResp.ok) {
                const ttsData = await ttsResp.json();
                playDoctorAudio(ttsData.audio_base64, greetingText);
            } else {
                playDoctorAudio(null, greetingText);
            }
        } catch (e) {
            playDoctorAudio(null, greetingText);
        }
    } else {
        stage.classList.remove('active');
        callBtn.classList.remove('active');
        callBtn.innerHTML = '<span class="pulse-red-dot"></span> Start 3D Live Doctor Call';
        
        voiceToggle.checked = false;
        disableVoiceMode();
        if (typeof set3DVisualizerState === 'function') {
            set3DVisualizerState('idle');
        }
        showToast('Live consultation ended.', 'info');
    }
}

function toggleStageMic() {
    if (!isLiveCallActive) return;
    isMicMuted = !isMicMuted;
    const btn = document.getElementById('btn-stage-mic');
    const label = document.getElementById('btn-stage-mic-label');

    if (isMicMuted) {
        stopSpeechListening();
        btn.style.background = '#334155';
        btn.style.borderColor = '#475569';
        btn.style.color = '#94a3b8';
        label.innerText = '🔇 Mic Paused (Tap to Speak)';
        updateLiveDoctorState('idle', 'Microphone paused');
    } else {
        btn.style.background = '#ef4444';
        btn.style.borderColor = '#f87171';
        btn.style.color = '#ffffff';
        label.innerText = '🎙️ Listening to You... (Tap to Pause)';
        startSpeechListening();
        updateLiveDoctorState('listening', 'Listening to you... Speak now');
    }
}

function updateLiveDoctorState(state, statusText, subtitleText = null) {
    const statusPill = document.getElementById('doctor-call-status');
    const caption = document.getElementById('live-subtitles-caption');
    const stageMicLabel = document.getElementById('btn-stage-mic-label');

    if (typeof set3DVisualizerState === 'function') {
        set3DVisualizerState(state);
    }

    if (statusPill) {
        statusPill.innerText = statusText;
    }
    if (subtitleText && caption) {
        // Strip any JSON formatting
        const cleanSub = subtitleText.replace(/\{.*"speech_text":\s*"([^"]+)".*\}/s, '$1').replace(/[*#_`~]/g, '');
        caption.innerText = `"${cleanSub}"`;
    }
    if (stageMicLabel) {
        if (state === 'speaking') {
            stageMicLabel.innerText = '👨‍⚕️ Dr. Dhanvantari Speaking (VibeVoice)...';
        } else if (state === 'listening' && !isMicMuted) {
            stageMicLabel.innerText = '🎙️ Listening to You... (Tap to Pause)';
        } else if (state === 'thinking') {
            stageMicLabel.innerText = '🧠 Dr. Dhanvantari Analyzing Symptoms...';
        }
    }
}

// =======================================================
// END VISIT & INSTANT PRESCRIPTION GENERATION
// =======================================================

async function endVisitAndGeneratePrescription() {
    if (!patientId) {
        showToast('Please register consent first.', 'error');
        return;
    }
    if (!conversationId) {
        showToast('Please chat with the doctor first before generating a prescription.', 'warning');
        return;
    }

    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
    if (speechSynthesis) speechSynthesis.cancel();
    if (isListening) stopSpeechListening();

    showToast('Generating official clinical prescription...', 'info');

    try {
        const response = await fetch('/api/chat/prescription/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_id: patientId,
                conversation_id: conversationId
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Prescription generation failed.');
        }

        const data = await response.json();

        // Populate Modal Fields
        document.getElementById('rx-patient-id').innerText = data.patient_id;
        document.getElementById('rx-date').innerText = new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
        document.getElementById('rx-consultation-id').innerText = `RX-${data.conversation_id.slice(-8)}`;
        
        const triageBadge = document.getElementById('rx-triage-badge');
        triageBadge.className = `triage-tag ${data.triage_level}`;
        triageBadge.innerText = data.triage_level.replace(/_/g, ' ').toUpperCase();

        document.getElementById('rx-diagnosis-text').innerText = `${data.diagnosis} (ICD-10: ${data.icd10})`;

        // Populate Medications Table
        const medTbody = document.getElementById('rx-medications-table-body');
        medTbody.innerHTML = '';
        (data.medications || []).forEach(med => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <strong>${med.molecule}</strong><br>
                    <span style="font-size: 11px; color: var(--text-muted);">${med.strength || 'Standard generic formulation'}</span>
                </td>
                <td>
                    ${med.dosage || med.standard_dose}<br>
                    <span style="font-size: 11px; color: var(--primary);">${med.frequency}</span>
                </td>
                <td>${med.duration}</td>
            `;
            medTbody.appendChild(tr);
        });

        // Populate Advice
        const adviceList = document.getElementById('rx-advice-list');
        adviceList.innerHTML = '';
        (data.advice || []).forEach(adv => {
            const li = document.createElement('li');
            li.innerText = adv;
            adviceList.appendChild(li);
        });

        // Update PDF Download link
        document.getElementById('btn-download-pdf-link').href = data.pdf_download_url;

        // Show Modal
        document.getElementById('prescription-modal-overlay').classList.add('active');

        // Play Closing Doctor voice
        const closingMsg = selectedVoiceLang === 'hi-IN'
            ? "आपका परामर्श पूरा हो गया है। मैंने आपका डिजिटल प्रिस्क्रिप्शन तैयार कर दिया है। आप आधिकारिक पीडीएफ डाउनलोड कर सकते हैं।"
            : "Your consultation is complete. I have generated your digital prescription with NLEM medication guidelines. You can download the official PDF now.";
        
        playDoctorAudio(null, closingMsg);
        showToast('Prescription generated successfully!', 'success');
    } catch (e) {
        showToast(`Error: ${e.message}`, 'error');
    }
}

function closePrescriptionModal() {
    document.getElementById('prescription-modal-overlay').classList.remove('active');
}

// Chat functions
function handleChatKey(e) {
    if (e.key === 'Enter') {
        sendChatMessage();
    }
}

function sendQuickMessage(txt) {
    document.getElementById('chat-user-input').value = txt;
    sendChatMessage();
}

async function sendChatMessage() {
    const input = document.getElementById('chat-user-input');
    const msg = input.value.trim();
    if (!msg) return;

    if (!patientId) {
        showToast('DPDP Patient Profile not verified. Reload to grant consent.', 'error');
        return;
    }

    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
    if (speechSynthesis) {
        speechSynthesis.cancel();
    }

    isProcessingTurn = true;
    appendChatBubble('user', msg);
    input.value = '';

    if (isLiveCallActive) {
        updateLiveDoctorState('thinking', 'Dr. Dhanvantari analyzing symptoms...', msg);
    }

    const typing = document.getElementById('chat-typing-indicator');
    typing.style.display = 'flex';
    scrollToBottom('chat-history-container');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                patient_id: patientId,
                conversation_id: conversationId,
                message: msg,
                language: selectedVoiceLang
            })
        });

        if (!response.ok) {
            const err = await response.json();
            if (response.status === 403) {
                localStorage.removeItem('dhanvantari_patient_id');
                localStorage.removeItem('dhanvantari_patient_email');
                patientId = null;
                patientEmail = null;
                document.getElementById('consent-modal-overlay').style.display = 'flex';
                document.getElementById('patient-info-display').style.display = 'none';
                showToast('Session reset. Please accept the DPDP consent again.', 'warning');
            }
            throw new Error(err.detail || 'Failed to process chat.');
        }

        const data = await response.json();
        conversationId = data.conversation_id;

        typing.style.display = 'none';
        appendChatBubble('assistant', data.reply);

        updateTriageBadge(data.triage_level);
        updateSymptomsList(data.symptoms);

        if (data.escalated_to_rmp) {
            showToast('Note: Triage escalated to RMP queue for practitioner review.', 'info');
        }

        scrollToBottom('chat-history-container');
        isProcessingTurn = false;

        if (isVoiceMode || isLiveCallActive) {
            playDoctorAudio(data.audio_base64, data.speech_reply);
        }
    } catch (e) {
        isProcessingTurn = false;
        typing.style.display = 'none';
        const replyErr = `Error processing symptoms: ${e.message}. Please try again.`;
        appendChatBubble('assistant', replyErr);
        scrollToBottom('chat-history-container');
        if (isVoiceMode || isLiveCallActive) {
            playDoctorAudio(null, replyErr);
        }
    }
}

// Multimodal File Upload (X-Ray, CT, Lab Reports)
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!patientId) {
        showToast('DPDP Patient Profile not verified. Reload to grant consent.', 'error');
        event.target.value = '';
        return;
    }

    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
    if (speechSynthesis) {
        speechSynthesis.cancel();
    }

    const userPreview = `📎 **Attached Document:** ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    appendChatBubble('user', userPreview);

    if (isLiveCallActive) {
        updateLiveDoctorState('thinking', 'Dr. Dhanvantari reviewing diagnostic scan...', file.name);
    }

    const typing = document.getElementById('chat-typing-indicator');
    typing.style.display = 'flex';
    scrollToBottom('chat-history-container');

    const formData = new FormData();
    formData.append('patient_id', patientId);
    if (conversationId) formData.append('conversation_id', conversationId);
    formData.append('language', selectedVoiceLang);
    formData.append('file', file);
    formData.append('notes', document.getElementById('chat-user-input').value.trim());

    document.getElementById('chat-user-input').value = '';

    try {
        const response = await fetch('/api/chat/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Multimodal upload failed.');
        }

        const data = await response.json();
        conversationId = data.conversation_id;

        typing.style.display = 'none';

        if (data.multimodal_findings) {
            renderMultimodalFindingsCard(data.multimodal_findings);
        }

        appendChatBubble('assistant', data.reply);
        updateTriageBadge(data.triage_level);
        updateSymptomsList(data.symptoms);

        showToast('Medical document parsed & escalated to Doctor queue.', 'info');
        scrollToBottom('chat-history-container');

        if (isVoiceMode || isLiveCallActive) {
            playDoctorAudio(data.audio_base64, data.speech_reply);
        }
    } catch (e) {
        typing.style.display = 'none';
        const errBubble = `Error processing document: ${e.message}. Please try again.`;
        appendChatBubble('assistant', errBubble);
        scrollToBottom('chat-history-container');
        if (isVoiceMode || isLiveCallActive) playDoctorAudio(null, errBubble);
    } finally {
        event.target.value = '';
    }
}

function renderMultimodalFindingsCard(findings) {
    const container = document.getElementById('chat-history-container');
    const cardDiv = document.createElement('div');
    cardDiv.className = 'chat-message assistant';

    const metricsHtml = (findings.extracted_metrics || []).map(m => `
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05); font-size: 11px;">
            <td style="padding: 4px 8px;">${m.test_name}</td>
            <td style="padding: 4px 8px; font-weight: bold;">${m.observed_value}</td>
            <td style="padding: 4px 8px; color: var(--text-muted);">${m.reference_range}</td>
            <td style="padding: 4px 8px;"><span class="triage-tag ${m.status === 'normal' ? 'self_care' : 'urgent'}">${m.status.toUpperCase()}</span></td>
        </tr>
    `).join('');

    cardDiv.innerHTML = `
        <div class="message-bubble" style="background: rgba(13, 148, 136, 0.04); border: 1px solid rgba(13, 148, 136, 0.2); width: 100%; max-width: 500px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="color: var(--primary); font-size: 13px;">🔬 Multimodal AI Radiologist Extractor</strong>
                <span class="triage-tag ${findings.clinical_urgency}">${findings.modality}</span>
            </div>
            <div style="font-size: 12px; margin-bottom: 8px;">
                <strong>Preliminary Impression:</strong> ${findings.preliminary_impression}
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">
                <strong>Key Observations:</strong> ${findings.key_findings}
            </div>
            ${metricsHtml ? `
                <table style="width: 100%; border-collapse: collapse; margin-top: 6px; margin-bottom: 8px;">
                    <thead>
                        <tr style="text-align: left; font-size: 10px; color: var(--text-muted); border-bottom: 1px solid rgba(0,0,0,0.1);">
                            <th style="padding: 4px 8px;">Metric</th>
                            <th style="padding: 4px 8px;">Value</th>
                            <th style="padding: 4px 8px;">Ref Range</th>
                            <th style="padding: 4px 8px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>${metricsHtml}</tbody>
                </table>
            ` : ''}
            <div style="font-size: 10px; color: var(--text-muted); border-top: 1px dashed rgba(0,0,0,0.1); padding-top: 6px;">
                ⚠️ <em>${findings.regulatory_disclaimer}</em>
            </div>
        </div>
        <div class="message-meta">Dhanvantari AI Vision • ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
    `;
    container.appendChild(cardDiv);
}

function appendChatBubble(role, content) {
    const container = document.getElementById('chat-history-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${role}`;
    
    // Clean any raw json markers if present
    const clean = content.replace(/\{.*"display_text":\s*"([^"]+)".*\}/s, '$1').replace(/\n/g, '<br>');

    msgDiv.innerHTML = `
        <div class="message-bubble">${clean}</div>
        <div class="message-meta">${role === 'user' ? 'Patient' : 'Dhanvantari AI'} • ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
    `;
    container.appendChild(msgDiv);
}

function updateTriageBadge(level) {
    const badge = document.getElementById('triage-status-badge');
    badge.className = 'status-badge';
    
    if (!level) {
        badge.innerText = 'NOT INITIALIZED';
        return;
    }

    badge.classList.add(level);
    badge.innerText = level.replace(/_/g, ' ').toUpperCase();
}

function updateSymptomsList(symptoms) {
    const container = document.getElementById('extracted-symptoms-list');
    container.innerHTML = '';

    if (!symptoms || symptoms.length === 0) {
        container.innerHTML = `
            <div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 10px;">
                Start chatting to extract symptoms.
            </div>`;
        return;
    }

    symptoms.forEach(s => {
        const item = document.createElement('div');
        item.className = 'symptom-tag-pill';
        
        let sub = '';
        if (s.onset) sub += ` (${s.onset})`;
        
        let sev = '';
        if (s.severity) sev = `<span class="severity">Sev: ${s.severity}/10</span>`;

        item.innerHTML = `
            <span><strong>${s.description}</strong>${sub}</span>
            ${sev}
        `;
        container.appendChild(item);
    });
}

function scrollToBottom(containerId) {
    const container = document.getElementById(containerId);
    container.scrollTop = container.scrollHeight;
}

// ==========================================
// Web Speech API STT and Neural Audio Playback
// ==========================================

function changeVoiceLanguage(event) {
    selectedVoiceLang = event.target.value;
    
    // Sync both selectors
    const sidebarSelect = document.getElementById('voice-language-select');
    const stageSelect = document.getElementById('stage-language-select');
    if (sidebarSelect) sidebarSelect.value = selectedVoiceLang;
    if (stageSelect) stageSelect.value = selectedVoiceLang;

    showToast(`Voice language set to: ${selectedVoiceLang === 'hi-IN' ? 'हिन्दी (Hindi / VibeVoice)' : 'English (Indian)'}`, 'info');
    
    if (recognition) {
        recognition.lang = selectedVoiceLang;
        if (isListening) {
            stopSpeechListening();
            setTimeout(() => {
                if (isVoiceMode || isLiveCallActive) startSpeechListening();
            }, 300);
        }
    }
}

function setupSpeechRecognition() {
    if (!SpeechRecognition) {
        console.warn('SpeechRecognition not supported in this browser.');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = selectedVoiceLang;

    recognition.onstart = () => {
        isListening = true;
        updateVoiceUIState('listening', 'Listening to you...');
        document.getElementById('btn-chat-mic').classList.add('listening');
        if (isLiveCallActive && !isMicMuted) {
            updateLiveDoctorState('listening', 'Listening to you... Speak now');
        }
    };

    recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }

        if (interimTranscript && isLiveCallActive) {
            const caption = document.getElementById('live-subtitles-caption');
            if (caption) caption.innerText = `"${interimTranscript}"`;
        }

        if (finalTranscript) {
            console.log('Transcribed speech input:', finalTranscript);
            document.getElementById('chat-user-input').value = finalTranscript;
            stopSpeechListening();
            sendChatMessage();
        }
    };

    recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'no-speech' || event.error === 'network' || event.error === 'aborted') {
            if ((isVoiceMode || isLiveCallActive) && !isProcessingTurn && !isMicMuted) {
                triggerNextSpeechListenTurn();
            } else {
                stopSpeechRecognitionState();
            }
        } else if (event.error === 'not-allowed') {
            showToast('Microphone access denied. Please allow mic in browser settings.', 'error');
            stopSpeechRecognitionState();
        } else {
            if (isVoiceMode || isLiveCallActive) {
                triggerNextSpeechListenTurn();
            }
        }
    };

    recognition.onend = () => {
        isListening = false;
        if ((isVoiceMode || isLiveCallActive) && !isProcessingTurn && !isMicMuted) {
            if (!currentAudioElement || currentAudioElement.paused) {
                triggerNextSpeechListenTurn();
            }
        } else {
            stopSpeechRecognitionState();
        }
    };
}

function toggleVoiceMode(event) {
    isVoiceMode = event.target.checked;
    
    if (isVoiceMode) {
        if (!SpeechRecognition) {
            showToast('Voice mode is not supported by your browser. Please try Google Chrome or Safari.', 'error');
            event.target.checked = false;
            isVoiceMode = false;
            return;
        }
        showToast('Voice Triage Mode enabled. Speak naturally to the AI Doctor.', 'success');
        updateVoiceUIState('idle', 'Voice Triage Active');
        startSpeechListening();
    } else {
        disableVoiceMode();
    }
}

function disableVoiceMode() {
    isVoiceMode = false;
    stopSpeechListening();
    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
    if (speechSynthesis) {
        speechSynthesis.cancel();
    }
    updateVoiceUIState('off', 'Voice Off');
    if (!isLiveCallActive) {
        showToast('Voice Triage Mode disabled.', 'info');
    }
}

function startSpeechListening() {
    if (!recognition || isListening || isProcessingTurn || isMicMuted) return;
    try {
        isListening = true;
        recognition.start();
    } catch (e) {
        if (e.name === 'InvalidStateError') {
            // Already running, ignore cleanly
        } else {
            isListening = false;
            console.warn('Speech recognition start info:', e);
        }
    }
}

function stopSpeechListening() {
    if (!recognition) return;
    try {
        recognition.stop();
        stopSpeechRecognitionState();
    } catch (e) {
        console.error('Error stopping recognition:', e);
    }
}

function stopSpeechRecognitionState() {
    isListening = false;
    document.getElementById('btn-chat-mic').classList.remove('listening');
    if (isVoiceMode || isLiveCallActive) {
        updateVoiceUIState('idle', 'Voice Triage Active');
    } else {
        updateVoiceUIState('off', 'Voice Off');
    }
}

function toggleMicRecording() {
    if (!SpeechRecognition) {
        showToast('Speech recognition not supported in this browser. Please try Google Chrome.', 'error');
        return;
    }
    
    if (isListening) {
        stopSpeechListening();
    } else {
        if (currentAudioElement) {
            currentAudioElement.pause();
            currentAudioElement = null;
        }
        if (speechSynthesis) {
            speechSynthesis.cancel();
        }
        startSpeechListening();
    }
}

function playDoctorAudio(audioBase64, fallbackSpeechText) {
    if (currentAudioElement) {
        currentAudioElement.pause();
        currentAudioElement = null;
    }
    if (speechSynthesis) {
        speechSynthesis.cancel();
    }

    if (audioBase64) {
        try {
            const audioSrc = "data:audio/mp3;base64," + audioBase64;
            currentAudioElement = new Audio(audioSrc);

            // Connect audio element to Three.js WebGL visualizer analyser
            if (typeof connectAudioElementToVisualizer === 'function') {
                connectAudioElementToVisualizer(currentAudioElement);
            }

            currentAudioElement.onplay = () => {
                updateVoiceUIState('speaking', 'Dr. Dhanvantari Speaking (VibeVoice)');
                if (isLiveCallActive) {
                    updateLiveDoctorState('speaking', 'Dr. Dhanvantari speaking (VibeVoice 1.5B)...', (fallbackSpeechText || '').slice(0, 140) + '...');
                }
            };

            currentAudioElement.onended = () => {
                currentAudioElement = null;
                updateVoiceUIState('idle', 'Voice Triage Active');
                if (isLiveCallActive && !isMicMuted) {
                    updateLiveDoctorState('listening', 'Listening to you... Speak now');
                    triggerNextSpeechListenTurn();
                } else if (isVoiceMode) {
                    triggerNextSpeechListenTurn();
                }
            };

            currentAudioElement.onerror = (err) => {
                console.warn('VibeVoice audio playback failed, falling back to Web Speech synthesis:', err);
                currentAudioElement = null;
                speakAIResponse(fallbackSpeechText);
            };

            currentAudioElement.play().catch(err => {
                console.warn('Playback error or blocked by autoplay:', err);
                currentAudioElement = null;
                speakAIResponse(fallbackSpeechText);
            });
            return;
        } catch (e) {
            console.warn('Error with Audio element:', e);
        }
    }

    // Fallback to browser speech synthesis
    speakAIResponse(fallbackSpeechText);
}

function speakAIResponse(text) {
    if (!speechSynthesis) return;

    speechSynthesis.cancel();
    const cleanText = (text || '').replace(/[*#_`~]/g, '');
    speechUtterance = new SpeechSynthesisUtterance(cleanText);
    
    const hasHindiCharacters = /[\u0900-\u097F]/.test(text || '');
    const voices = speechSynthesis.getVoices();
    let voiceCandidate = null;
    
    if (hasHindiCharacters || selectedVoiceLang === 'hi-IN') {
        speechUtterance.lang = 'hi-IN';
        voiceCandidate = voices.find(v => v.lang.includes('hi-IN'));
    } else {
        speechUtterance.lang = 'en-IN';
        voiceCandidate = voices.find(v => v.lang.includes('en-IN')) || 
                         voices.find(v => v.lang.includes('en-GB') || v.lang.includes('en-US'));
    }

    if (voiceCandidate) {
        speechUtterance.voice = voiceCandidate;
    }

    speechUtterance.onstart = () => {
        updateVoiceUIState('speaking', 'AI Doctor is speaking...');
        if (isLiveCallActive) {
            updateLiveDoctorState('speaking', 'Dr. Dhanvantari speaking...', cleanText.slice(0, 140) + '...');
        }
    };

    speechUtterance.onend = () => {
        updateVoiceUIState('idle', 'Voice Triage Active');
        if (isLiveCallActive && !isMicMuted) {
            updateLiveDoctorState('listening', 'Listening to you... Speak now');
            triggerNextSpeechListenTurn();
        } else if (isVoiceMode) {
            triggerNextSpeechListenTurn();
        }
    };

    speechUtterance.onerror = (e) => {
        console.error('Speech synthesis error:', e);
        updateVoiceUIState('idle', 'Voice Triage Active');
        if ((isVoiceMode || isLiveCallActive) && !isMicMuted) {
            triggerNextSpeechListenTurn();
        }
    };

    speechSynthesis.speak(speechUtterance);
}

function triggerNextSpeechListenTurn() {
    if (listenTimeout) clearTimeout(listenTimeout);
    listenTimeout = setTimeout(() => {
        if ((isVoiceMode || isLiveCallActive) && !isProcessingTurn && !isMicMuted) {
            startSpeechListening();
        }
    }, 600);
}

function updateVoiceUIState(state, text) {
    const indicator = document.getElementById('voice-indicator');
    const label = document.getElementById('voice-status-label');
    
    if (indicator) {
        indicator.className = 'voice-status-indicator';
        if (state === 'listening') {
            indicator.classList.add('listening');
        } else if (state === 'speaking') {
            indicator.classList.add('speaking');
        }
    }
    if (label) {
        label.innerText = text;
    }
}

// ==========================================
// Doctor Portal Actions
// ==========================================

async function loadDoctorQueue() {
    const container = document.getElementById('doctor-queue-container');
    container.innerHTML = '<div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 20px;">Loading review queue...</div>';

    try {
        const response = await fetch('/api/admin/queue');
        if (!response.ok) throw new Error('Failed to load queue.');
        const items = await response.json();

        container.innerHTML = '';
        if (items.length === 0) {
            container.innerHTML = '<div style="color: var(--text-muted); font-size: 12px; text-align: center; padding: 20px;">No pending cases escalated.</div>';
            return;
        }

        items.forEach(item => {
            const div = document.createElement('div');
            div.className = `queue-item ${activeReviewItemId === item.id ? 'active' : ''}`;
            div.onclick = () => selectCase(item.conversation_id, item.id, item.draft_prescription);

            const timestamp = new Date(item.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            div.innerHTML = `
                <div class="queue-item-header">
                    <span class="queue-item-id">${item.conversation_id}</span>
                    <span class="triage-tag ${item.triage_level}">${item.triage_level || 'Self Care'}</span>
                </div>
                <div class="queue-item-meta">
                    <span>Patient Email: ${item.patient_email || 'Anonymous'}</span>
                    <span>Status: <strong>${item.status}</strong></span>
                    <span>Escalated at: ${timestamp}</span>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        container.innerHTML = `<div style="color: var(--triage-urgent); font-size: 12px; text-align: center; padding: 20px;">Error: ${e.message}</div>`;
    }
}

async function selectCase(conId, reviewItemId, draftRx) {
    activeReviewItemId = reviewItemId;
    
    document.querySelectorAll('.queue-item').forEach(el => el.classList.remove('active'));
    
    const approvalPanel = document.getElementById('doctor-approval-container');
    approvalPanel.style.display = 'flex';
    document.getElementById('form-prescription-text').value = draftRx || '';
    
    const header = document.getElementById('selected-case-header');
    header.innerHTML = `
        <h3 style="font-family: var(--font-outfit);">Case ${conId}</h3>
        <p style="font-size: 12px; color: var(--text-muted);">Review history and approve diagnostic recommendation.</p>
    `;

    const chatContainer = document.getElementById('doctor-transcript-container');
    chatContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 20px;">Loading chat history...</div>';

    try {
        const response = await fetch(`/api/admin/conversation/${conId}`);
        if (!response.ok) throw new Error('Failed to load conversation transcript.');
        const details = await response.json();

        chatContainer.innerHTML = '';
        
        const consentLog = document.createElement('div');
        consentLog.style.background = 'rgba(13, 148, 136, 0.05)';
        consentLog.style.border = '1px solid rgba(13, 148, 136, 0.15)';
        consentLog.style.padding = '12px';
        consentLog.style.borderRadius = '8px';
        consentLog.style.marginBottom = '16px';
        consentLog.style.fontSize = '11px';
        consentLog.innerHTML = `
            <strong>DPDP Regulatory Audit Log:</strong><br>
            Patient Email: ${details.patient_email || 'Anonymous'}<br>
            Consent Captured: Yes (Scope: "${details.consent_scope}")
        `;
        chatContainer.appendChild(consentLog);

        details.messages.forEach(m => {
            const bubble = document.createElement('div');
            const isUser = m.role === 'user';
            bubble.className = `chat-message ${isUser ? 'user' : 'assistant'}`;
            
            let redFlagAlert = '';
            if (m.red_flag_detected) {
                redFlagAlert = `<div style="color: var(--triage-urgent); font-size: 11px; font-weight: bold; margin-bottom: 4px;">⚠️ EMERGENCY RED FLAG DETECTED</div>`;
            }

            bubble.innerHTML = `
                <div class="message-bubble" style="${isUser ? '' : 'background: #ffffff; border: 1px solid var(--border-color);'}">
                    ${redFlagAlert}
                    ${m.content.replace(/\n/g, '<br>')}
                </div>
                <div class="message-meta">${isUser ? 'Patient' : 'Dhanvantari AI'} • ${new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
            `;
            chatContainer.appendChild(bubble);
        });

        scrollToBottom('doctor-transcript-container');
    } catch (e) {
        chatContainer.innerHTML = `<div style="color: var(--triage-urgent); font-size: 13px; text-align: center; padding: 20px;">Error: ${e.message}</div>`;
    }
}

async function approvePrescription() {
    const docName = document.getElementById('form-doctor-name').value.trim();
    const license = document.getElementById('form-doctor-license').value.trim();
    const rxText = document.getElementById('form-prescription-text').value.trim();
    const signature = document.getElementById('form-doctor-signature').value.trim();

    if (!docName || !license || !rxText || !signature) {
        showToast('All fields are required to sign off the prescription.', 'error');
        return;
    }

    try {
        const response = await fetch('/api/admin/prescription/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                review_item_id: activeReviewItemId,
                rmp_id: `${docName} (${license})`,
                prescription_text: rxText,
                signature: signature
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Sign-off failed.');
        }

        const data = await response.json();
        showToast('Prescription authorized and signed successfully!', 'success');

        document.getElementById('doctor-approval-container').style.display = 'none';
        document.getElementById('selected-case-header').innerHTML = `
            <h3 style="font-family: var(--font-outfit);">No Case Selected</h3>
            <p style="font-size: 12px; color: var(--text-muted);">Select a case from the queue to review chat transcripts.</p>
        `;
        document.getElementById('doctor-transcript-container').innerHTML = `
            <div style="color: var(--text-muted); font-size: 14px; text-align: center; margin-top: 40px;">
                Transcript will load here.
            </div>
        `;
        
        activeReviewItemId = null;
        loadDoctorQueue();
    } catch (e) {
        showToast(e.message, 'error');
    }
}
