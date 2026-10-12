/**
 * CardioAI Batch Screening Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    const templateLink = document.getElementById('templateLink');
    if (templateLink) {
        templateLink.href = API.getSampleTemplateUrl();
    }

    const fileInput = document.getElementById('csv_file');
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            const label = document.getElementById('file_selected');
            if (fileInput.files && fileInput.files[0]) {
                label.textContent = 'Selected: ' + fileInput.files[0].name;
            }
        });
    }

    const form = document.getElementById('batchForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files || !fileInput.files[0]) {
                alert('Please choose a CSV file first.');
                return;
            }

            const btn = form.querySelector('button[type="submit"]');
            const origText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner"></span> Processing Screening...';
            btn.disabled = true;

            try {
                const res = await API.processBatchCSV(fileInput.files[0]);
                renderBatchResults(res);
            } catch (err) {
                alert('Error: ' + err.message);
            } finally {
                btn.innerHTML = origText;
                btn.disabled = false;
            }
        });
    }
});

function renderBatchResults(data) {
    const container = document.getElementById('batchResultsContainer');
    if (!container) return;

    let html = `
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <h3 style="font-size: 1.15rem; font-weight: 700;">Screening Results (${data.summary.total} Patients Processed)</h3>
                <p style="font-size: 0.825rem; color: var(--slate-500);">Automated machine learning risk classifications generated</p>
            </div>
        </div>

        <div style="display: flex; gap: 16px; margin-bottom: 16px;">
            <span class="badge badge-danger" style="font-size: 0.85rem; padding: 6px 12px;">
                🚨 High Risk: ${data.summary.high_risk_count}
            </span>
            <span class="badge badge-success" style="font-size: 0.85rem; padding: 6px 12px;">
                ✓ Low Risk: ${data.summary.low_risk_count}
            </span>
        </div>

        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                <thead>
                    <tr style="background-color: var(--slate-50); border-bottom: 1px solid var(--slate-200); text-align: left;">
                        <th style="padding: 10px 14px;">#</th>
                        <th style="padding: 10px 14px;">Patient & MRN</th>
                        <th style="padding: 10px 14px;">Age / Sex</th>
                        <th style="padding: 10px 14px;">BP / Chol</th>
                        <th style="padding: 10px 14px;">Max HR</th>
                        <th style="padding: 10px 14px;">Probability</th>
                        <th style="padding: 10px 14px;">Classification</th>
                    </tr>
                </thead>
                <tbody>
    `;

    data.results.forEach((row, i) => {
        const isHigh = row.prediction === 1;
        html += `
            <tr style="border-bottom: 1px solid var(--slate-200);">
                <td style="padding: 10px 14px;"><b>${i+1}</b></td>
                <td style="padding: 10px 14px;"><b>${row.patient_name}</b><br><small style="color: var(--slate-400);">${row.mrn}</small></td>
                <td style="padding: 10px 14px;">${row.age}y / ${row.sex === 1 ? 'M' : 'F'}</td>
                <td style="padding: 10px 14px;">${row.trestbps} / ${row.chol}</td>
                <td style="padding: 10px 14px;">${row.thalach} bpm</td>
                <td style="padding: 10px 14px;"><b>${(row.probability * 100).toFixed(1)}%</b></td>
                <td style="padding: 10px 14px;">
                    <span class="badge ${isHigh ? 'badge-danger' : 'badge-success'}">
                        ${row.risk_level}
                    </span>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    </div>
    `;
    container.innerHTML = html;
}
