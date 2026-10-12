/**
 * CardioAI Centralized API Client
 * Seamlessly interfaces with the Backend REST API and FHIR services.
 */

const API_CONFIG = {
    // If running frontend on a separate port or file://, point to backend port 5000
    getBaseUrl: () => {
        if (window.location.port !== '5000' && window.location.protocol.startsWith('http')) {
            return `http://${window.location.hostname}:5000`;
        } else if (window.location.protocol === 'file:') {
            return 'http://127.0.0.1:5000';
        }
        return '';
    }
};

const API = {
    // 1. Health check
    checkHealth: async () => {
        const url = `${API_CONFIG.getBaseUrl()}/api/health`;
        const resp = await fetch(url);
        return await resp.json();
    },

    // 2. Real-time patient prediction
    predictPatient: async (patientData) => {
        const url = `${API_CONFIG.getBaseUrl()}/api/predict`;
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patientData)
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ message: 'Server error' }));
            throw new Error(err.message || 'Prediction failed');
        }
        return await resp.json();
    },

    // 3. Consultation history records
    getHistory: async () => {
        const url = `${API_CONFIG.getBaseUrl()}/api/history`;
        const resp = await fetch(url);
        return await resp.json();
    },

    // 4. Longitudinal patient tracking
    getLongitudinal: async (mrn) => {
        const url = `${API_CONFIG.getBaseUrl()}/api/longitudinal/${encodeURIComponent(mrn)}`;
        const resp = await fetch(url);
        return await resp.json();
    },

    // 5. Batch CSV screening
    processBatchCSV: async (file) => {
        const url = `${API_CONFIG.getBaseUrl()}/api/batch`;
        const formData = new FormData();
        formData.append('csv_file', file);
        const resp = await fetch(url, {
            method: 'POST',
            body: formData
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ message: 'Batch upload failed' }));
            throw new Error(err.message || 'Batch upload failed');
        }
        return await resp.json();
    },

    // 6. Model benchmark metrics
    getModelsAnalytics: async () => {
        const url = `${API_CONFIG.getBaseUrl()}/api/models`;
        const resp = await fetch(url);
        return await resp.json();
    },

    // 7. Clear history
    clearHistory: async () => {
        const url = `${API_CONFIG.getBaseUrl()}/api/clear-history`;
        const resp = await fetch(url, { method: 'POST' });
        return await resp.json();
    },

    // 8. Download URLs
    getReportDownloadUrl: (id) => `${API_CONFIG.getBaseUrl()}/api/download-report/${id}`,
    getCSVExportUrl: () => `${API_CONFIG.getBaseUrl()}/api/export-csv`,
    getSampleTemplateUrl: () => `${API_CONFIG.getBaseUrl()}/sample-template.csv`,
    getFHIRRiskUrl: (id) => `${API_CONFIG.getBaseUrl()}/fhir/RiskAssessment/${id}`
};
