"""
Backend REST & FHIR API Test Suite
Validates health endpoints, ML predictions, longitudinal tracking,
batch screening, model benchmark metrics, and FHIR resource delivery.
"""

import os
import unittest
import json
import io
from app import app, init_db, load_ml_artifacts, predict_single, pipeline, feature_names
from clinical_scoring import evaluate_biomarkers, calculate_framingham_risk
from explainability_engine import calculate_local_attributions, compute_counterfactual_recourse

class TestBackendAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        loaded = load_ml_artifacts()
        if not loaded:
            raise RuntimeError("ML artifacts could not be loaded for testing.")
        cls.client = app.test_client()

    def test_health_endpoint(self):
        """Verify that /api/health returns 200 and healthy status."""
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data.get('status'), 'healthy')
        self.assertTrue(data.get('model_loaded'))

    def test_predict_api_low_risk(self):
        """Verify REST prediction for low-risk clinical profile."""
        payload = {
            'patient_name': 'Test Low Risk',
            'mrn': 'MRN-TEST-LOW',
            'age': 52, 'sex': 1, 'cp': 0, 'trestbps': 125, 'chol': 212, 'fbs': 0,
            'restecg': 1, 'thalach': 168, 'exang': 0, 'oldpeak': 1.0, 'slope': 2, 'ca': 2, 'thal': 3
        }
        resp = self.client.post('/api/predict', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['prediction'], 0)
        self.assertEqual(data['risk_level'], 'Low Risk')
        self.assertTrue('biomarkers' in data)
        self.assertTrue('attributions' in data)
        self.assertTrue('conformal_interval' in data)
        self.assertTrue('soap_note' in data)

    def test_predict_api_high_risk(self):
        """Verify REST prediction for high-risk clinical profile."""
        payload = {
            'patient_name': 'Test High Risk',
            'mrn': 'MRN-TEST-HIGH',
            'age': 58, 'sex': 0, 'cp': 0, 'trestbps': 100, 'chol': 248, 'fbs': 0,
            'restecg': 0, 'thalach': 122, 'exang': 0, 'oldpeak': 1.0, 'slope': 1, 'ca': 0, 'thal': 2
        }
        resp = self.client.post('/api/predict', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['prediction'], 1)
        self.assertEqual(data['risk_level'], 'High Risk')
        self.assertTrue(data['probability'] >= 0.5)

    def test_history_and_longitudinal_api(self):
        """Verify consultation history retrieval and patient MRN longitudinal tracking."""
        mrn = 'MRN-LONG-01'
        # Post two visits for the same patient
        for bp in [130, 145]:
            self.client.post('/api/predict', json={
                'patient_name': 'Longitudinal Subject',
                'mrn': mrn,
                'age': 60, 'sex': 1, 'cp': 2, 'trestbps': bp, 'chol': 220, 'fbs': 0,
                'restecg': 1, 'thalach': 150, 'exang': 0, 'oldpeak': 0.8, 'slope': 2, 'ca': 0, 'thal': 2
            })

        # Test history
        hist_resp = self.client.get('/api/history')
        self.assertEqual(hist_resp.status_code, 200)
        hist_data = json.loads(hist_resp.data)
        self.assertEqual(hist_data['status'], 'success')
        self.assertTrue(len(hist_data['records']) >= 2)

        # Test longitudinal
        long_resp = self.client.get(f'/api/longitudinal/{mrn}')
        self.assertEqual(long_resp.status_code, 200)
        long_data = json.loads(long_resp.data)
        self.assertEqual(long_data['status'], 'success')
        self.assertEqual(long_data['mrn'], mrn)
        self.assertTrue(len(long_data['records']) >= 2)

    def test_models_analytics_api(self):
        """Verify /api/models returns benchmark metrics and feature importance."""
        resp = self.client.get('/api/models')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('metrics' in data)
        self.assertTrue('feature_importance' in data)
        self.assertTrue('model_comparison' in data['metrics'])

    def test_batch_screening_api(self):
        """Verify batch CSV processing."""
        csv_content = (
            "age,sex,cp,trestbps,chol,fbs,restecg,thalach,exang,oldpeak,slope,ca,thal\n"
            "52,1,0,125,212,0,1,168,0,1.0,2,2,3\n"
            "58,0,0,100,248,0,0,122,0,1.0,1,0,2\n"
        )
        data = {
            'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv')
        }
        resp = self.client.post('/api/batch', data=data, content_type='multipart/form-data')
        self.assertEqual(resp.status_code, 200)
        res_data = json.loads(resp.data)
        self.assertEqual(res_data['status'], 'success')
        self.assertEqual(len(res_data['results']), 2)

    def test_fhir_endpoints(self):
        """Verify HL7 FHIR Patient, Observation, and RiskAssessment endpoints."""
        resp = self.client.post('/api/predict', json={
            'patient_name': 'FHIR Subject',
            'mrn': 'MRN-FHIR-01',
            'age': 55, 'sex': 0, 'cp': 1, 'trestbps': 120, 'chol': 200, 'fbs': 0,
            'restecg': 0, 'thalach': 160, 'exang': 0, 'oldpeak': 0.0, 'slope': 2, 'ca': 0, 'thal': 2
        })
        record_id = json.loads(resp.data)['id']

        # Patient
        p_resp = self.client.get(f'/fhir/Patient/{record_id}')
        self.assertEqual(p_resp.status_code, 200)
        p_fhir = json.loads(p_resp.data)
        self.assertEqual(p_fhir['resourceType'], 'Patient')

        # Observations
        o_resp = self.client.get(f'/fhir/Observation/{record_id}')
        self.assertEqual(o_resp.status_code, 200)
        o_fhir = json.loads(o_resp.data)
        self.assertEqual(o_fhir['resourceType'], 'Bundle')

        # RiskAssessment
        r_resp = self.client.get(f'/fhir/RiskAssessment/{record_id}')
        self.assertEqual(r_resp.status_code, 200)
        r_fhir = json.loads(r_resp.data)
        self.assertEqual(r_fhir['resourceType'], 'RiskAssessment')

if __name__ == '__main__':
    unittest.main()
