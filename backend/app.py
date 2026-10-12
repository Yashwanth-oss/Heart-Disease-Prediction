"""
CardioAI Backend REST API & HL7 FHIR Service
Flask Application with CORS support, ML Inference, FHIR R4, and Report Generation.
"""

import os
import json
import sqlite3
import io
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timezone
from flask import (
    Flask, request, jsonify, send_file, make_response, send_from_directory
)
from flask_cors import CORS

from clinical_scoring import (
    evaluate_biomarkers, calculate_framingham_risk, generate_clinical_recommendations
)
from explainability_engine import (
    calculate_local_attributions, compute_counterfactual_recourse,
    calculate_conformal_confidence, get_guideline_evidence_citations, generate_soap_note
)
from fhir_service import (
    create_fhir_patient, create_fhir_observations, create_fhir_risk_assessment
)
from report_generator import generate_pdf_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

DB_PATH = os.path.join(BASE_DIR, 'heart_disease.db')
PIPELINE_PATH = os.path.join(BASE_DIR, 'model_pipeline.pkl')
LEGACY_MODEL_PATH = os.path.join(BASE_DIR, 'model.pkl')
LEGACY_SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')
LEGACY_FEATURES_PATH = os.path.join(BASE_DIR, 'feature_names.pkl')
METRICS_PATH = os.path.join(BASE_DIR, 'model_metrics.json')
FEATURE_IMPORTANCE_PATH = os.path.join(BASE_DIR, 'feature_importance.json')
TEMPLATE_CSV_PATH = os.path.join(BASE_DIR, 'sample_template.csv')

pipeline = None
legacy_model = None
legacy_scaler = None
feature_names = [
    'age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 
    'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'
]

def load_ml_artifacts():
    global pipeline, legacy_model, legacy_scaler, feature_names
    
    if os.path.exists(PIPELINE_PATH):
        try:
            pipeline = joblib.load(PIPELINE_PATH)
            print(f"[OK] Successfully loaded end-to-end pipeline: '{PIPELINE_PATH}'")
            return True
        except Exception as e:
            print(f"Warning: Failed loading '{PIPELINE_PATH}': {e}")

    if os.path.exists(LEGACY_MODEL_PATH) and os.path.exists(LEGACY_SCALER_PATH):
        try:
            legacy_model = joblib.load(LEGACY_MODEL_PATH)
            legacy_scaler = joblib.load(LEGACY_SCALER_PATH)
            if os.path.exists(LEGACY_FEATURES_PATH):
                feature_names = joblib.load(LEGACY_FEATURES_PATH)
            print("[OK] Loaded legacy model and scaler.")
            return True
        except Exception as e:
            print(f"Warning: Failed loading legacy artifacts: {e}")

    return False

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            patient_name TEXT DEFAULT 'Patient',
            mrn TEXT DEFAULT 'MRN-00001',
            age INTEGER,
            sex INTEGER,
            cp INTEGER,
            trestbps INTEGER,
            chol INTEGER,
            fbs INTEGER,
            restecg INTEGER,
            thalach INTEGER,
            exang INTEGER,
            oldpeak REAL,
            slope INTEGER,
            ca INTEGER,
            thal INTEGER,
            prediction INTEGER,
            probability REAL,
            risk_level TEXT
        )
    ''')
    
    # Schema check
    c.execute("PRAGMA table_info(predictions)")
    columns = [row[1] for row in c.fetchall()]
    if 'patient_name' not in columns:
        c.execute("ALTER TABLE predictions ADD COLUMN patient_name TEXT DEFAULT 'Patient'")
    if 'mrn' not in columns:
        c.execute("ALTER TABLE predictions ADD COLUMN mrn TEXT DEFAULT 'MRN-00001'")
    if 'probability' not in columns:
        c.execute("ALTER TABLE predictions ADD COLUMN probability REAL DEFAULT 0.0")
    if 'risk_level' not in columns:
        c.execute("ALTER TABLE predictions ADD COLUMN risk_level TEXT DEFAULT 'Unknown'")
        
    conn.commit()
    conn.close()

def predict_single(input_dict):
    df_input = pd.DataFrame([input_dict])[feature_names]
    
    if pipeline is not None:
        prediction = int(pipeline.predict(df_input)[0])
        if hasattr(pipeline, 'predict_proba'):
            probability = float(pipeline.predict_proba(df_input)[0][1])
        else:
            probability = 1.0 if prediction == 1 else 0.0
    elif legacy_model is not None and legacy_scaler is not None:
        scaled_input = legacy_scaler.transform(df_input)
        prediction = int(legacy_model.predict(scaled_input)[0])
        if hasattr(legacy_model, 'predict_proba'):
            probability = float(legacy_model.predict_proba(scaled_input)[0][1])
        else:
            probability = 1.0 if prediction == 1 else 0.0
    else:
        raise RuntimeError("No model or pipeline loaded. Please train first.")
        
    if probability >= 0.65:
        risk_level = "High Risk"
    elif probability >= 0.35:
        risk_level = "Moderate Risk"
    else:
        risk_level = "Low Risk"
        
    return prediction, probability, risk_level

def get_record_by_id(pred_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM predictions WHERE id = ?", (pred_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None, None
        
    keys = row.keys()
    patient_data = {
        'id': row['id'],
        'timestamp': row['timestamp'],
        'patient_name': row['patient_name'] if 'patient_name' in keys and row['patient_name'] else 'Patient',
        'mrn': row['mrn'] if 'mrn' in keys and row['mrn'] else f"MRN-{row['id']}",
        'age': row['age'],
        'sex': row['sex'],
        'cp': row['cp'],
        'trestbps': row['trestbps'],
        'chol': row['chol'],
        'fbs': row['fbs'],
        'restecg': row['restecg'],
        'thalach': row['thalach'],
        'exang': row['exang'],
        'oldpeak': row['oldpeak'],
        'slope': row['slope'],
        'ca': row['ca'],
        'thal': row['thal'],
    }
    pred = int(row['prediction']) if 'prediction' in keys and row['prediction'] is not None else 0
    prob = float(row['probability']) if 'probability' in keys and row['probability'] is not None else (1.0 if pred == 1 else 0.0)
    risk = str(row['risk_level']) if 'risk_level' in keys and row['risk_level'] else ('High Risk' if pred == 1 else 'Low Risk')
    return patient_data, (pred, prob, risk)

# ----------------- REST API ENDPOINTS ----------------- #

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        'status': 'healthy',
        'model_loaded': (pipeline is not None) or (legacy_model is not None),
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.get_json(force=True)
        input_data = {
            'patient_name': data.get('patient_name', 'Patient Screening'),
            'mrn': data.get('mrn', 'MRN-' + datetime.now().strftime("%y%m%d"))
        }
        for col in feature_names:
            val = data.get(col, 0)
            input_data[col] = float(val) if col in ['oldpeak'] else int(float(val))
            
        prediction, probability, risk_level = predict_single(input_data)
        biomarkers = evaluate_biomarkers(input_data)
        framingham = calculate_framingham_risk(input_data)
        recommendations = generate_clinical_recommendations(input_data, prediction, probability)
        
        attributions = calculate_local_attributions(pipeline, input_data, feature_names) if pipeline else []
        recourse = compute_counterfactual_recourse(pipeline, input_data, feature_names) if pipeline else {}
        conformal = calculate_conformal_confidence(probability)
        citations = get_guideline_evidence_citations(input_data)
        soap = generate_soap_note(input_data, prediction, probability, risk_level, biomarkers, framingham, recourse)
        
        # Persist to database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO predictions (
                timestamp, patient_name, mrn, age, sex, cp, trestbps, chol, fbs, restecg,
                thalach, exang, oldpeak, slope, ca, thal, prediction, probability, risk_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp, input_data['patient_name'], input_data['mrn'],
            input_data['age'], input_data['sex'], input_data['cp'],
            input_data['trestbps'], input_data['chol'], input_data['fbs'],
            input_data['restecg'], input_data['thalach'], input_data['exang'],
            input_data['oldpeak'], input_data['slope'], input_data['ca'],
            input_data['thal'], prediction, probability, risk_level
        ))
        last_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'id': last_id,
            'prediction': prediction,
            'probability': probability,
            'risk_level': risk_level,
            'biomarkers': biomarkers,
            'framingham': framingham,
            'recommendations': recommendations,
            'attributions': attributions,
            'recourse': recourse,
            'conformal_interval': conformal,
            'guideline_citations': citations,
            'soap_note': soap
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/history', methods=['GET'])
def api_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM predictions ORDER BY id DESC")
    records = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'status': 'success', 'records': records})

@app.route('/api/longitudinal/<mrn>', methods=['GET'])
def api_longitudinal(mrn):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM predictions WHERE mrn = ? ORDER BY id ASC", (mrn,))
    records = [dict(r) for r in c.fetchall()]
    conn.close()
    return jsonify({'status': 'success', 'mrn': mrn, 'records': records})

@app.route('/api/batch', methods=['POST'])
def api_batch():
    if 'csv_file' not in request.files or request.files['csv_file'].filename == '':
        return jsonify({'status': 'error', 'message': 'No CSV file provided'}), 400
        
    file = request.files['csv_file']
    try:
        df = pd.read_csv(file)
        missing = [c for c in feature_names if c not in df.columns]
        if missing:
            return jsonify({'status': 'error', 'message': f"Missing columns: {', '.join(missing)}"}), 400
            
        results = []
        high_count = 0
        low_count = 0
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            pred, prob, risk = predict_single(row_dict)
            row_dict['prediction'] = pred
            row_dict['probability'] = prob
            row_dict['risk_level'] = risk
            row_dict['patient_name'] = str(row_dict.get('patient_name', f"Patient {idx+1}"))
            row_dict['mrn'] = str(row_dict.get('mrn', f"MRN-B{idx+1:04d}"))
            results.append(row_dict)
            if pred == 1:
                high_count += 1
            else:
                low_count += 1
                
        return jsonify({
            'status': 'success',
            'results': results,
            'summary': {
                'total': len(results),
                'high_risk_count': high_count,
                'low_risk_count': low_count
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/models', methods=['GET'])
def api_models():
    metrics = {}
    feature_importance = {}
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
        except Exception as e:
            print(f"Error reading metrics: {e}")
            
    if os.path.exists(FEATURE_IMPORTANCE_PATH):
        try:
            with open(FEATURE_IMPORTANCE_PATH, 'r', encoding='utf-8') as f:
                feature_importance = json.load(f)
        except Exception as e:
            print(f"Error reading feature importances: {e}")
            
    return jsonify({
        'status': 'success',
        'metrics': metrics,
        'feature_importance': feature_importance
    })

@app.route('/api/download-report/<int:pred_id>', methods=['GET'])
def api_download_report(pred_id):
    patient_data, scores = get_record_by_id(pred_id)
    if not patient_data:
        return jsonify({'error': 'Record not found'}), 404
        
    pred, prob, risk = scores
    biomarkers = evaluate_biomarkers(patient_data)
    framingham = calculate_framingham_risk(patient_data)
    recs = generate_clinical_recommendations(patient_data, pred, prob)
    
    attributions = calculate_local_attributions(pipeline, patient_data, feature_names) if pipeline else None
    recourse = compute_counterfactual_recourse(pipeline, patient_data, feature_names) if pipeline else None
    conformal = calculate_conformal_confidence(prob)
    citations = get_guideline_evidence_citations(patient_data)
    soap = generate_soap_note(patient_data, pred, prob, risk, biomarkers, framingham, recourse)
    
    pdf_bytes = generate_pdf_report(
        patient_data=patient_data,
        prediction=pred,
        probability=prob,
        risk_level=risk,
        biomarkers=biomarkers,
        framingham=framingham,
        recommendations=recs,
        attributions=attributions,
        recourse=recourse,
        citations=citations,
        soap_note=soap,
        conformal=conformal
    )
    
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"CardioAI_Report_Patient_{pred_id}.pdf"
    )

@app.route('/api/export-csv', methods=['GET'])
def api_export_csv():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM predictions ORDER BY id DESC", conn)
    conn.close()
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    
    response = make_response(csv_buffer.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=cardioai_predictions_history.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/api/clear-history', methods=['POST'])
def api_clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM predictions")
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'All patient records cleared successfully.'})

@app.route('/sample-template.csv', methods=['GET'])
def sample_template():
    if os.path.exists(TEMPLATE_CSV_PATH):
        return send_file(
            TEMPLATE_CSV_PATH,
            mimetype='text/csv',
            as_attachment=True,
            download_name='cardioai_batch_sample.csv'
        )
    return "Template file not found", 404

# ----------------- HL7 FHIR R4 INTEROPERABILITY ----------------- #

@app.route('/fhir/Patient/<int:pred_id>')
def fhir_patient(pred_id):
    patient_data, _ = get_record_by_id(pred_id)
    if not patient_data:
        return jsonify({'error': 'Patient record not found'}), 404
    return jsonify(create_fhir_patient(patient_data, pred_id))

@app.route('/fhir/Observation/<int:pred_id>')
def fhir_observation(pred_id):
    patient_data, _ = get_record_by_id(pred_id)
    if not patient_data:
        return jsonify({'error': 'Observation record not found'}), 404
    return jsonify({
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": obs} for obs in create_fhir_observations(patient_data, pred_id)]
    })

@app.route('/fhir/RiskAssessment/<int:pred_id>')
def fhir_risk_assessment(pred_id):
    patient_data, scores = get_record_by_id(pred_id)
    if not patient_data:
        return jsonify({'error': 'Record not found'}), 404
    pred, prob, risk = scores
    return jsonify(create_fhir_risk_assessment(patient_data, pred, prob, risk, pred_id))

# ----------------- FRONTEND STATIC SERVING ----------------- #

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    if path != "" and os.path.exists(os.path.join(FRONTEND_DIR, f"{path}.html")):
        return send_from_directory(FRONTEND_DIR, f"{path}.html")
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ----------------- INITIALIZATION ----------------- #

init_db()
load_ml_artifacts()

if __name__ == '__main__':
    print("=" * 60)
    print("CardioAI Backend API & FHIR Server")
    print("=" * 60)
    print("Serving on http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
