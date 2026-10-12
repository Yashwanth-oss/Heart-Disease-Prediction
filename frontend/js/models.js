/**
 * CardioAI Model Analytics & Cross-Validation Benchmark
 * Loads metrics, confusion matrices, and feature importances from backend.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const loadingState = document.getElementById('loadingState');
    const analyticsContent = document.getElementById('analyticsContent');
    const modelStatusBadge = document.getElementById('modelStatusBadge');
    const metricsTableBody = document.getElementById('metricsTableBody');
    const featureImportanceList = document.getElementById('featureImportanceList');

    const cmTN = document.getElementById('cmTN');
    const cmFP = document.getElementById('cmFP');
    const cmFN = document.getElementById('cmFN');
    const cmTP = document.getElementById('cmTP');
    const cmStats = document.getElementById('cmStats');

    try {
        const res = await API.getModelsAnalytics();
        loadingState.style.display = 'none';
        analyticsContent.style.display = 'block';

        const metrics = res.metrics || {};
        const featureImportance = res.feature_importance || {};
        const bestModelName = metrics.best_model || 'Random Forest';

        modelStatusBadge.innerHTML = `<span class="badge badge-success">Pipeline Serving: ${escapeHtml(bestModelName)}</span>`;

        // 1. Populate Comparison Table
        metricsTableBody.innerHTML = '';
        if (metrics.model_comparison) {
            Object.entries(metrics.model_comparison).forEach(([name, row]) => {
                const isBest = name === bestModelName;
                const tr = document.createElement('tr');
                if (isBest) tr.className = 'best-row';

                const acc = ((row.accuracy || 0) * 100).toFixed(2);
                const rec = ((row.recall || 0) * 100).toFixed(2);
                const prec = ((row.precision || 0) * 100).toFixed(2);
                const f1 = ((row.f1 || 0) * 100).toFixed(2);
                const roc = ((row.roc_auc || 0) * 100).toFixed(2);

                tr.innerHTML = `
                    <td>
                        <b>${escapeHtml(name)}</b>
                        ${isBest ? '<span class="badge badge-success" style="font-size: 0.65rem; margin-left: 6px;">WINNING MODEL</span>' : ''}
                    </td>
                    <td>${acc}%</td>
                    <td>${rec}%</td>
                    <td>${prec}%</td>
                    <td>${f1}%</td>
                    <td><b>${roc}%</b></td>
                    <td>
                        ${isBest 
                            ? '<span class="badge badge-success">Serving in Pipeline</span>' 
                            : '<span style="font-size: 0.75rem; color: var(--slate-400);">Benchmark Candidate</span>'}
                    </td>
                `;
                metricsTableBody.appendChild(tr);
            });
        } else {
            metricsTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--slate-400);">No benchmark data recorded. Run python training.py to generate benchmarks.</td></tr>`;
        }

        // 2. Populate Confusion Matrix
        if (metrics.test_confusion_matrix && metrics.test_confusion_matrix.length === 2) {
            const cm = metrics.test_confusion_matrix;
            const tn = cm[0][0];
            const fp = cm[0][1];
            const fn = cm[1][0];
            const tp = cm[1][1];

            cmTN.textContent = tn;
            cmFP.textContent = fp;
            cmFN.textContent = fn;
            cmTP.textContent = tp;

            const sensitivity = ((tp / (tp + fn || 1)) * 100).toFixed(1);
            const specificity = ((tn / (tn + fp || 1)) * 100).toFixed(1);

            cmStats.innerHTML = `<b>Sensitivity (Recall):</b> ${sensitivity}% &bull; <b>Specificity:</b> ${specificity}%`;
        }

        // 3. Populate Feature Importances
        featureImportanceList.innerHTML = '';
        const featEntries = Object.entries(featureImportance);
        if (featEntries.length > 0) {
            const maxScore = Math.max(...featEntries.map(([, score]) => score)) || 1;
            
            featEntries.slice(0, 10).forEach(([feat, score]) => {
                const pct = Math.min(100, Math.max(5, (score / maxScore) * 100)).toFixed(1);
                const row = document.createElement('div');
                row.className = 'feat-bar-row';
                row.innerHTML = `
                    <span class="feat-name">${escapeHtml(feat)}</span>
                    <div class="feat-bar-wrap">
                        <div class="feat-bar-fill" style="width: ${pct}%;"></div>
                    </div>
                    <span class="feat-score">${score.toFixed(2)}</span>
                `;
                featureImportanceList.appendChild(row);
            });
        } else {
            featureImportanceList.innerHTML = `<p style="font-size: 0.85rem; color: var(--slate-400);">Feature importance profile not available.</p>`;
        }

    } catch (err) {
        loadingState.style.display = 'none';
        analyticsContent.style.display = 'block';
        modelStatusBadge.innerHTML = `<span class="badge badge-danger">Backend Disconnected</span>`;
        metricsTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 24px;">Failed to load benchmark data from backend: ${escapeHtml(err.message)}</td></tr>`;
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
