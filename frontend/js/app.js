/**
 * CardioAI Main Patient Assessment Controller
 */

const PRESETS = {
    healthy: {
        patient_name: "Sarah Miller", mrn: "MRN-10023",
        age: 28, sex: 0, cp: 2, trestbps: 110, chol: 175, fbs: 0,
        restecg: 0, thalach: 182, exang: 0, oldpeak: 0.0, slope: 2, ca: 0, thal: 1
    },
    moderate: {
        patient_name: "Robert Davis", mrn: "MRN-10045",
        age: 54, sex: 1, cp: 1, trestbps: 135, chol: 235, fbs: 0,
        restecg: 1, thalach: 148, exang: 0, oldpeak: 1.2, slope: 1, ca: 1, thal: 2
    },
    cardiac: {
        patient_name: "James Wilson", mrn: "MRN-10088",
        age: 63, sex: 1, cp: 0, trestbps: 155, chol: 288, fbs: 1,
        restecg: 1, thalach: 118, exang: 1, oldpeak: 2.8, slope: 1, ca: 2, thal: 3
    }
};

function applyPreset(name) {
    const p = PRESETS[name];
    if (!p) return;
    for (const [key, val] of Object.entries(p)) {
        const el = document.getElementById('input_' + key);
        if (el) el.value = val;
    }
}

// Form Submission & Async Prediction
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('predictionForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner"></span> Running Clinical Assessment...';
            submitBtn.disabled = true;

            try {
                const formData = new FormData(form);
                const payload = {};
                formData.forEach((value, key) => {
                    if (['patient_name', 'mrn'].includes(key)) {
                        payload[key] = value.trim();
                    } else if (['oldpeak'].includes(key)) {
                        payload[key] = parseFloat(value);
                    } else {
                        payload[key] = parseInt(value, 10);
                    }
                });

                const result = await API.predictPatient(payload);
                renderAssessmentResults(result, payload);
            } catch (err) {
                alert('Prediction Error: ' + err.message);
            } finally {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });

        const urlParams = new URLSearchParams(window.location.search);
        const autoPreset = urlParams.get('auto');
        if (autoPreset && PRESETS[autoPreset]) {
            applyPreset(autoPreset);
            setTimeout(() => {
                form.dispatchEvent(new Event('submit'));
            }, 100);
        }
    }
});

function renderAssessmentResults(data, inputData) {
    const container = document.getElementById('resultsContainer');
    if (!container) return;

    const probPct = (data.probability * 100).toFixed(1);
    const riskClass = data.risk_level === 'High Risk' ? 'high-risk' : (data.risk_level === 'Moderate Risk' ? 'moderate-risk' : 'low-risk');

    let html = `
    <div class="card">
        <div class="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="m9 12 2 2 4-4"></path></svg>
            Assessment Outcome
        </div>

        <div class="risk-banner ${riskClass}">
            <div class="gauge-circle">${probPct}%</div>
            <div class="risk-headline">${data.risk_level} Identified</div>
            <div style="font-size: 0.8rem; margin-top: 6px; font-weight: 600;">
                <span class="badge badge-${data.conformal_interval.reliability_badge}">${data.conformal_interval.confidence_tier}</span>
                &bull; 95% Conf: ${data.conformal_interval.coverage_interval}
            </div>
        </div>

        <!-- Fast Actions -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
            <a href="${API.getReportDownloadUrl(data.id)}" class="btn btn-primary btn-sm" style="font-weight: 700;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Download Medical PDF
            </a>
            <a href="${API.getFHIRRiskUrl(data.id)}" target="_blank" class="btn btn-outline btn-sm">
                View HL7 FHIR JSON
            </a>
        </div>
    `;

    // Local Feature Attributions
    if (data.attributions && data.attributions.length > 0) {
        html += `
        <div style="font-size: 0.825rem; font-weight: 700; color: var(--slate-400); text-transform: uppercase; margin-bottom: 8px;">
            Patient-Specific Risk Drivers (Local Attributions)
        </div>
        <div style="background-color: var(--slate-50); border: 1px solid var(--slate-200); border-radius: var(--radius-md); padding: 14px; margin-bottom: 18px;">
        `;
        data.attributions.slice(0, 5).forEach(a => {
            const isPos = a.direction === 'increases_risk';
            const width = Math.min(a.impact_pct * 35, 100);
            html += `
            <div class="attr-row" style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 0.8rem;">
                <span style="width: 150px; font-weight: 600; text-align: right; color: var(--slate-700);">${a.feature}</span>
                <div style="flex: 1; background-color: var(--slate-200); height: 8px; border-radius: 9999px; overflow: hidden;">
                    <div style="height: 100%; width: ${width}%; background-color: ${isPos ? 'var(--danger)' : 'var(--success)'};"></div>
                </div>
                <span style="width: 65px; font-weight: 700; color: ${isPos ? 'var(--danger)' : 'var(--success)'};">
                    ${isPos ? '+' : '-'}${a.impact_pct}
                </span>
            </div>
            `;
        });
        html += `</div>`;
    }

    // Counterfactual Recourse
    if (data.recourse && data.recourse.needed) {
        html += `
        <div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: var(--radius-md); padding: 16px; margin-bottom: 20px;">
            <div style="font-size: 0.925rem; font-weight: 800; color: #065f46; margin-bottom: 6px;">
                Actionable Recourse: Projected Risk Reduction (-${data.recourse.risk_reduction_pct}%)
            </div>
            <p style="font-size: 0.8rem; color: #064e3b; margin-bottom: 10px;">
                Targeted lifestyle targets bring projected risk to <b>${(data.recourse.projected_probability * 100).toFixed(1)}%</b>.
            </p>
        `;
        data.recourse.recourse_actions.forEach(act => {
            html += `
            <div style="font-size: 0.8rem; margin-bottom: 6px; color: #065f46;">
                &bull; <b>${act.biomarker}:</b> ${act.current} &rarr; <b>${act.target}</b> (${act.change})
            </div>
            `;
        });
        html += `</div>`;
    }

    // Interactive What-If Simulation
    html += `
    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--slate-200);">
        <div style="font-size: 1rem; font-weight: 700; margin-bottom: 4px;">Interactive "What-If" Scenario Simulator</div>
        <p style="font-size: 0.8rem; color: var(--slate-500); margin-bottom: 14px;">Adjust sliders to see immediate risk projection in real time.</p>
        
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.825rem; font-weight: 600; margin-bottom: 4px;">
                <span>Resting Blood Pressure:</span>
                <span id="sim_bp_val">${inputData.trestbps} mmHg</span>
            </div>
            <input type="range" style="width: 100%; accent-color: var(--primary);" id="sim_bp" min="90" max="200" value="${inputData.trestbps}" oninput="handleSimUpdate()">
        </div>

        <div style="margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; font-size: 0.825rem; font-weight: 600; margin-bottom: 4px;">
                <span>Serum Cholesterol:</span>
                <span id="sim_chol_val">${inputData.chol} mg/dL</span>
            </div>
            <input type="range" style="width: 100%; accent-color: var(--primary);" id="sim_chol" min="120" max="400" value="${inputData.chol}" oninput="handleSimUpdate()">
        </div>

        <div style="background-color: var(--slate-100); border-radius: var(--radius-md); padding: 12px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 0.85rem; font-weight: 600;">Simulated Projection:</span>
            <span id="sim_result_badge" class="badge badge-primary" style="font-size: 0.85rem; background-color: var(--primary); color: white;">
                ${probPct}% Risk (${data.risk_level})
            </span>
        </div>
    </div>
    `;

    // Clinical SOAP Note
    if (data.soap_note) {
        html += `
        <div style="margin-top: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 0.825rem; font-weight: 700; color: var(--slate-400); text-transform: uppercase;">EHR Clinical SOAP Note</span>
                <button type="button" class="btn btn-outline btn-sm" onclick="copySoapNote()" style="padding: 2px 8px; font-size: 0.75rem;">Copy SOAP Note</button>
            </div>
            <div id="soapContent" style="background-color: var(--slate-900); color: #f8fafc; border-radius: var(--radius-md); padding: 14px; font-family: monospace; font-size: 0.75rem; max-height: 200px; overflow-y: auto; white-space: pre-wrap;">${data.soap_note}</div>
        </div>
        `;
    }

    html += `</div>`;
    container.innerHTML = html;
}

async function handleSimUpdate() {
    const bp = document.getElementById('sim_bp').value;
    const chol = document.getElementById('sim_chol').value;
    document.getElementById('sim_bp_val').textContent = bp + ' mmHg';
    document.getElementById('sim_chol_val').textContent = chol + ' mg/dL';

    const form = document.getElementById('predictionForm');
    const formData = new FormData(form);
    const payload = {};
    formData.forEach((val, key) => payload[key] = parseFloat(val));
    payload['trestbps'] = parseFloat(bp);
    payload['chol'] = parseFloat(chol);

    try {
        const res = await API.predictPatient(payload);
        const badge = document.getElementById('sim_result_badge');
        const prob = (res.probability * 100).toFixed(1);
        badge.textContent = `${prob}% Risk (${res.risk_level})`;
        badge.style.backgroundColor = res.risk_level === 'High Risk' ? '#dc2626' : (res.risk_level === 'Moderate Risk' ? '#d97706' : '#16a34a');
    } catch (e) {
        console.error(e);
    }
}

function copySoapNote() {
    const el = document.getElementById('soapContent');
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        alert('SOAP Note copied to clipboard for EHR charting!');
    });
}

// Voice Dictation
let recognition = null;
let isRecording = false;

function toggleVoiceDictation() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert('Web Speech API is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
        return;
    }
    const btn = document.getElementById('voiceBtn');
    const text = document.getElementById('voiceText');

    if (isRecording) {
        recognition.stop();
        btn.classList.remove('recording');
        text.textContent = 'Voice Dictation';
        isRecording = false;
        return;
    }

    recognition = new SpeechRec();
    recognition.continuous = false;
    recognition.lang = 'en-US';

    recognition.onstart = function() {
        isRecording = true;
        btn.classList.add('recording');
        text.textContent = 'Listening... (Speak vitals)';
    };

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript.toLowerCase();
        console.log('Voice transcript:', transcript);

        const ageMatch = transcript.match(/(?:age|years old)\s*(\d+)/);
        if (ageMatch) document.getElementById('input_age').value = ageMatch[1];

        const bpMatch = transcript.match(/(?:blood pressure|bp)\s*(\d+)/);
        if (bpMatch) document.getElementById('input_trestbps').value = bpMatch[1];

        const cholMatch = transcript.match(/(?:cholesterol)\s*(\d+)/);
        if (cholMatch) document.getElementById('input_chol').value = cholMatch[1];

        const hrMatch = transcript.match(/(?:heart rate|pulse)\s*(\d+)/);
        if (hrMatch) document.getElementById('input_thalach').value = hrMatch[1];

        if (transcript.includes('female')) document.getElementById('input_sex').value = '0';
        else if (transcript.includes('male')) document.getElementById('input_sex').value = '1';

        alert('Voice recognized: "' + transcript + '" - Vitals mapped to form!');
    };

    recognition.onerror = function() {
        btn.classList.remove('recording');
        text.textContent = 'Voice Dictation';
        isRecording = false;
    };
    recognition.onend = function() {
        btn.classList.remove('recording');
        text.textContent = 'Voice Dictation';
        isRecording = false;
    };
    recognition.start();
}
