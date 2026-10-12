/**
 * CardioAI History Records Controller
 */

let allRecords = [];

document.addEventListener('DOMContentLoaded', async () => {
    const csvExportBtn = document.getElementById('csvExportBtn');
    if (csvExportBtn) {
        csvExportBtn.href = API.getCSVExportUrl();
    }

    const clearBtn = document.getElementById('clearHistoryBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to delete all historical clinical records?')) {
                await API.clearHistory();
                await loadRecords();
            }
        });
    }

    await loadRecords();
});

async function loadRecords() {
    try {
        const res = await API.getHistory();
        allRecords = res.records || [];
        updateSummaryStats(allRecords);
        renderTable(allRecords);
    } catch (err) {
        console.error('Failed to load history:', err);
    }
}

function updateSummaryStats(records) {
    document.getElementById('totalCount').textContent = records.length;
    const high = records.filter(r => r.prediction === 1).length;
    const low = records.filter(r => r.prediction === 0).length;
    document.getElementById('highCount').textContent = high;
    document.getElementById('lowCount').textContent = low;
}

function renderTable(records) {
    const tbody = document.getElementById('historyTbody');
    if (!tbody) return;

    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 36px; color: var(--slate-400);">No consultation records found.</td></tr>`;
        return;
    }

    let html = '';
    records.forEach(row => {
        const isHigh = row.prediction === 1;
        html += `
        <tr class="table-row" data-risk="${isHigh ? 'high' : 'low'}" style="border-bottom: 1px solid var(--slate-200);">
            <td style="padding: 14px 18px;">
                <b>${row.patient_name || 'Patient'}</b>
                <div style="font-size: 0.775rem; color: var(--slate-400);">${row.mrn || 'N/A'} &bull; #${row.id}</div>
            </td>
            <td style="padding: 14px 18px; font-size: 0.8rem; color: var(--slate-600);">${row.timestamp}</td>
            <td style="padding: 14px 18px;">${row.age}y, ${row.sex === 1 ? 'Male' : 'Female'}</td>
            <td style="padding: 14px 18px;">${row.trestbps} mmHg / ${row.chol} mg/dL</td>
            <td style="padding: 14px 18px;">${row.thalach} bpm &bull; ${row.oldpeak} mm</td>
            <td style="padding: 14px 18px;">
                <span class="badge ${isHigh ? 'badge-danger' : 'badge-success'}">
                    ${row.risk_level || (isHigh ? 'High Risk' : 'Low Risk')} (${((row.probability || 0) * 100).toFixed(1)}%)
                </span>
            </td>
            <td style="padding: 14px 18px;">
                <div style="display: flex; gap: 6px;">
                    <a href="${API.getReportDownloadUrl(row.id)}" class="btn btn-outline btn-sm">PDF</a>
                    <a href="longitudinal.html?mrn=${encodeURIComponent(row.mrn)}" class="btn btn-outline btn-sm">Timeline</a>
                    <a href="${API.getFHIRRiskUrl(row.id)}" target="_blank" class="btn btn-outline btn-sm">FHIR</a>
                </div>
            </td>
        </tr>
        `;
    });
    tbody.innerHTML = html;
}

function filterRecords(type, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (type === 'all') {
        renderTable(allRecords);
    } else if (type === 'high') {
        renderTable(allRecords.filter(r => r.prediction === 1));
    } else {
        renderTable(allRecords.filter(r => r.prediction === 0));
    }
}
