/**
 * CardioAI Longitudinal Risk Progression Tracker
 * Retrieves and renders chronological patient vitals and risk trajectory.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const mrn = params.get('mrn');

    const patientHeader = document.getElementById('patientHeader');
    const patientMeta = document.getElementById('patientMeta');
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    const timelineContainer = document.getElementById('timelineContainer');
    const riskTrendBadge = document.getElementById('riskTrendBadge');
    const pageSubtitle = document.getElementById('pageSubtitle');

    if (!mrn) {
        loadingState.style.display = 'none';
        emptyState.style.display = 'block';
        patientHeader.textContent = 'MRN Missing';
        patientMeta.textContent = 'Please select a patient from the history records table.';
        return;
    }

    pageSubtitle.innerHTML = `Tracking cardiovascular vitals and machine learning risk trajectories for MRN <b class="font-mono">${escapeHtml(mrn)}</b>`;

    try {
        const data = await API.getLongitudinal(mrn);
        loadingState.style.display = 'none';

        if (!data.records || data.records.length === 0) {
            emptyState.style.display = 'block';
            patientHeader.textContent = `No Records for ${mrn}`;
            patientMeta.textContent = 'Zero clinical consultations recorded under this identifier.';
            return;
        }

        const records = data.records;
        const firstRecord = records[0];
        const lastRecord = records[records.length - 1];
        
        patientHeader.textContent = `Patient: ${firstRecord.patient_name || 'Anonymous'}`;
        patientMeta.textContent = `Medical Record: ${mrn} • Total Recorded Visits: ${records.length}`;

        // Compute risk trajectory trend
        if (records.length > 1) {
            const firstProb = firstRecord.probability || 0;
            const lastProb = lastRecord.probability || 0;
            const delta = lastProb - firstProb;

            if (delta > 0.1) {
                riskTrendBadge.innerHTML = `<span class="badge badge-danger">Risk Worsening (+${(delta * 100).toFixed(1)}%)</span>`;
            } else if (delta < -0.1) {
                riskTrendBadge.innerHTML = `<span class="badge badge-success">Risk Improving (${(delta * 100).toFixed(1)}%)</span>`;
            } else {
                riskTrendBadge.innerHTML = `<span class="badge badge-info">Risk Trajectory Stable</span>`;
            }
        }

        timelineContainer.innerHTML = '';
        records.forEach((row, idx) => {
            const isHigh = row.prediction === 1;
            const probPct = ((row.probability || 0) * 100).toFixed(1);
            const dotClass = isHigh ? 'high' : 'low';
            const riskBadge = isHigh ? '<span class="badge badge-danger">High Risk</span>' : '<span class="badge badge-success">Low Risk</span>';

            const item = document.createElement('div');
            item.className = 'timeline-item';
            item.innerHTML = `
                <div class="timeline-dot ${dotClass}"></div>
                <div class="visit-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; border-bottom: 1px solid var(--slate-100); padding-bottom: 12px; margin-bottom: 12px;">
                        <div>
                            <div style="font-size: 0.775rem; font-weight: 700; color: var(--slate-400); text-transform: uppercase; letter-spacing: 0.04em;">
                                VISIT #${idx + 1} &bull; ${escapeHtml(row.timestamp || 'N/A')}
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                                <span style="font-size: 1.15rem; font-weight: 800; color: var(--slate-900);">${escapeHtml(row.risk_level || (isHigh ? 'High Risk' : 'Low Risk'))}</span>
                                ${riskBadge}
                                <span style="font-size: 0.85rem; font-weight: 600; color: var(--slate-500);">(${probPct}% ML Risk)</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <a href="${API.getReportDownloadUrl(row.id)}" class="btn btn-outline btn-sm">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                                Visit PDF
                            </a>
                            <a href="${API.getFHIRRiskUrl(row.id)}" target="_blank" class="btn btn-outline btn-sm" title="View HL7 FHIR JSON">
                                FHIR R4
                            </a>
                        </div>
                    </div>

                    <div class="vitals-grid">
                        <div class="vital-stat">
                            <div class="vital-lbl">Resting Blood Pressure</div>
                            <div class="vital-val">${row.trestbps} <span style="font-size: 0.75rem; font-weight: 400; color: var(--slate-500);">mmHg</span></div>
                        </div>
                        <div class="vital-stat">
                            <div class="vital-lbl">Serum Cholesterol</div>
                            <div class="vital-val">${row.chol} <span style="font-size: 0.75rem; font-weight: 400; color: var(--slate-500);">mg/dL</span></div>
                        </div>
                        <div class="vital-stat">
                            <div class="vital-lbl">Peak Heart Rate</div>
                            <div class="vital-val">${row.thalach} <span style="font-size: 0.75rem; font-weight: 400; color: var(--slate-500);">bpm</span></div>
                        </div>
                        <div class="vital-stat">
                            <div class="vital-lbl">ST Depression</div>
                            <div class="vital-val">${row.oldpeak} <span style="font-size: 0.75rem; font-weight: 400; color: var(--slate-500);">mm</span></div>
                        </div>
                        <div class="vital-stat">
                            <div class="vital-lbl">Exercise Angina</div>
                            <div class="vital-val">${row.exang == 1 ? '<span style="color: var(--danger);">Yes</span>' : '<span style="color: var(--success);">No</span>'}</div>
                        </div>
                        <div class="vital-stat">
                            <div class="vital-lbl">Fluoroscopy Vessels</div>
                            <div class="vital-val">${row.ca} <span style="font-size: 0.75rem; font-weight: 400; color: var(--slate-500);">vessels</span></div>
                        </div>
                    </div>
                </div>
            `;
            timelineContainer.appendChild(item);
        });

        timelineContainer.style.display = 'block';

    } catch (err) {
        loadingState.style.display = 'none';
        emptyState.style.display = 'block';
        patientHeader.textContent = 'Connection Error';
        patientMeta.textContent = `Failed to query backend: ${err.message}`;
    }
});

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
