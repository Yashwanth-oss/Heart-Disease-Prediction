"""
Clinical Scoring and Cardiovascular Health Assessment Module
Provides medical guideline benchmarks (Framingham 10-Year Risk, Biomarker Stratification,
and Personalized Clinical Recommendations).
"""

def evaluate_biomarkers(data):
    """
    Evaluates individual patient biomarkers against AHA/ACC guidelines.
    Returns status flags, risk level, and clinical interpretations.
    """
    age = float(data.get('age', 50))
    trestbps = float(data.get('trestbps', 120))
    chol = float(data.get('chol', 200))
    fbs = int(data.get('fbs', 0))
    thalach = float(data.get('thalach', 150))
    exang = int(data.get('exang', 0))
    oldpeak = float(data.get('oldpeak', 0.0))
    cp = int(data.get('cp', 0))
    
    biomarkers = {}
    
    # Blood Pressure (AHA/ACC 2017)
    if trestbps < 120:
        biomarkers['trestbps'] = {
            'value': f"{int(trestbps)} mmHg",
            'status': 'Normal',
            'severity': 'success',
            'detail': 'Resting BP within optimal healthy range (<120 mmHg).'
        }
    elif trestbps <= 129:
        biomarkers['trestbps'] = {
            'value': f"{int(trestbps)} mmHg",
            'status': 'Elevated',
            'severity': 'warning',
            'detail': 'Systolic pressure slightly elevated (120-129 mmHg).'
        }
    elif trestbps <= 139:
        biomarkers['trestbps'] = {
            'value': f"{int(trestbps)} mmHg",
            'status': 'Stage 1 Hypertension',
            'severity': 'danger',
            'detail': 'Mild hypertension (130-139 mmHg). Lifestyle modifications advised.'
        }
    else:
        biomarkers['trestbps'] = {
            'value': f"{int(trestbps)} mmHg",
            'status': 'Stage 2 Hypertension',
            'severity': 'danger',
            'detail': 'Substantial blood pressure elevation (≥140 mmHg). Medical review recommended.'
        }
        
    # Serum Cholesterol (NCEP ATP III)
    if chol < 200:
        biomarkers['chol'] = {
            'value': f"{int(chol)} mg/dL",
            'status': 'Desirable',
            'severity': 'success',
            'detail': 'Total serum cholesterol within target range (<200 mg/dL).'
        }
    elif chol <= 239:
        biomarkers['chol'] = {
            'value': f"{int(chol)} mg/dL",
            'status': 'Borderline High',
            'severity': 'warning',
            'detail': 'Borderline elevation (200-239 mg/dL). Monitor lipid profile.'
        }
    else:
        biomarkers['chol'] = {
            'value': f"{int(chol)} mg/dL",
            'status': 'High Cholesterol',
            'severity': 'danger',
            'detail': 'Significantly elevated cholesterol (≥240 mg/dL). Atherosclerosis risk.'
        }
        
    # Fasting Blood Sugar
    if fbs == 1:
        biomarkers['fbs'] = {
            'value': '> 120 mg/dL',
            'status': 'Elevated',
            'severity': 'warning',
            'detail': 'Fasting blood sugar indicates prediabetes/diabetic risk factor.'
        }
    else:
        biomarkers['fbs'] = {
            'value': '≤ 120 mg/dL',
            'status': 'Normal',
            'severity': 'success',
            'detail': 'Fasting blood glucose within acceptable standard limits.'
        }
        
    # Maximum Heart Rate Capacity (Fox & Haskell Formula: 220 - Age)
    predicted_max_hr = 220 - age
    target_85_pct = 0.85 * predicted_max_hr
    if thalach >= target_85_pct:
        biomarkers['thalach'] = {
            'value': f"{int(thalach)} bpm",
            'status': 'Adequate',
            'severity': 'success',
            'detail': f"Achieved ≥85% of age-predicted peak ({int(predicted_max_hr)} bpm)."
        }
    else:
        biomarkers['thalach'] = {
            'value': f"{int(thalach)} bpm",
            'status': 'Sub-target HR',
            'severity': 'warning',
            'detail': f"Max HR reached was below 85% of age target ({int(target_85_pct)} bpm)."
        }
        
    # ST Depression (oldpeak)
    if oldpeak < 1.0:
        biomarkers['oldpeak'] = {
            'value': f"{oldpeak:.1f} mm",
            'status': 'Normal',
            'severity': 'success',
            'detail': 'No significant exercise-induced ischemic ST segment deviation.'
        }
    elif oldpeak < 2.0:
        biomarkers['oldpeak'] = {
            'value': f"{oldpeak:.1f} mm",
            'status': 'Moderate Depression',
            'severity': 'warning',
            'detail': 'Moderate ST depression (1.0-1.9 mm). Potential exercise ischemia.'
        }
    else:
        biomarkers['oldpeak'] = {
            'value': f"{oldpeak:.1f} mm",
            'status': 'Marked Depression',
            'severity': 'danger',
            'detail': 'Marked ST segment depression (≥2.0 mm). High correlation with CAD.'
        }
        
    # Exercise Induced Angina
    if exang == 1:
        biomarkers['exang'] = {
            'value': 'Yes',
            'status': 'Present',
            'severity': 'danger',
            'detail': 'Exertional chest discomfort triggered by exercise stress testing.'
        }
    else:
        biomarkers['exang'] = {
            'value': 'No',
            'status': 'Absent',
            'severity': 'success',
            'detail': 'No angina symptoms induced during exercise test.'
        }
        
    return biomarkers

def calculate_framingham_risk(data):
    """
    Estimates 10-Year Cardiovascular Disease Risk using simplified
    Framingham Risk Point System.
    """
    age = float(data.get('age', 50))
    sex = int(data.get('sex', 1))  # 1 = Male, 0 = Female
    chol = float(data.get('chol', 200))
    trestbps = float(data.get('trestbps', 120))
    fbs = int(data.get('fbs', 0))
    
    points = 0
    
    # Points based on Sex & Age
    if sex == 1:  # Male
        if age < 35: points += -9
        elif age <= 39: points += -4
        elif age <= 44: points += 0
        elif age <= 49: points += 3
        elif age <= 54: points += 6
        elif age <= 59: points += 8
        elif age <= 64: points += 10
        elif age <= 69: points += 11
        elif age <= 74: points += 12
        else: points += 13
        
        # Cholesterol points
        if chol < 160: points += 0
        elif chol <= 199: points += 1
        elif chol <= 239: points += 2
        elif chol <= 279: points += 3
        else: points += 4
        
        # Blood pressure points
        if trestbps < 120: points += 0
        elif trestbps <= 129: points += 1
        elif trestbps <= 139: points += 2
        elif trestbps <= 159: points += 3
        else: points += 4
        
        # Diabetic / FBS factor
        if fbs == 1: points += 2
        
        # Risk estimation based on points
        if points <= 0: est_risk = 2.0
        elif points <= 4: est_risk = 5.0
        elif points <= 7: est_risk = 8.0
        elif points <= 9: est_risk = 12.0
        elif points <= 11: est_risk = 17.0
        elif points <= 13: est_risk = 22.0
        else: est_risk = 30.0
        
    else:  # Female
        if age < 35: points += -7
        elif age <= 39: points += -3
        elif age <= 44: points += 0
        elif age <= 49: points += 3
        elif age <= 54: points += 6
        elif age <= 59: points += 8
        elif age <= 64: points += 10
        elif age <= 69: points += 12
        elif age <= 74: points += 14
        else: points += 16
        
        if chol < 160: points += 0
        elif chol <= 199: points += 1
        elif chol <= 239: points += 3
        elif chol <= 279: points += 4
        else: points += 5
        
        if trestbps < 120: points += 0
        elif trestbps <= 129: points += 1
        elif trestbps <= 139: points += 2
        elif trestbps <= 159: points += 3
        else: points += 4
        
        if fbs == 1: points += 3
        
        if points <= 2: est_risk = 1.0
        elif points <= 6: est_risk = 3.0
        elif points <= 9: est_risk = 6.0
        elif points <= 11: est_risk = 11.0
        elif points <= 13: est_risk = 17.0
        elif points <= 15: est_risk = 24.0
        else: est_risk = 30.0
        
    category = "Low Risk (<10%)" if est_risk < 10 else ("Intermediate Risk (10-20%)" if est_risk <= 20 else "High Risk (>20%)")
    
    return {
        'points': points,
        'estimated_10yr_risk_pct': est_risk,
        'category': category
    }

def generate_clinical_recommendations(data, ml_prediction, ml_probability):
    """
    Generates actionable clinical guidance and lifestyle suggestions.
    """
    recommendations = []
    
    trestbps = float(data.get('trestbps', 120))
    chol = float(data.get('chol', 200))
    fbs = int(data.get('fbs', 0))
    exang = int(data.get('exang', 0))
    oldpeak = float(data.get('oldpeak', 0.0))
    
    if ml_probability >= 0.65:
        recommendations.append({
            'icon': 'stethoscope',
            'type': 'Urgent Clinical Review',
            'text': 'The machine learning model indicates high cardiovascular risk. Comprehensive evaluation by a board-certified cardiologist (including 12-lead ECG and echocardiogram) is strongly advised.'
        })
    elif ml_probability >= 0.35:
        recommendations.append({
            'icon': 'alert-circle',
            'type': 'Moderate Risk Monitoring',
            'text': 'Moderate cardiac risk profile identified. Regular blood pressure tracking and follow-up cardiovascular risk assessment recommended.'
        })
    else:
        recommendations.append({
            'icon': 'shield-check',
            'type': 'Preventative Maintenance',
            'text': 'Low risk indicators observed. Maintain routine annual preventative health checks and heart-healthy dietary patterns.'
        })
        
    if trestbps >= 130:
        recommendations.append({
            'icon': 'activity',
            'type': 'Blood Pressure Optimization',
            'text': f"Resting BP is {int(trestbps)} mmHg. Adopt the DASH diet (sodium < 2,300 mg/day), regular aerobic exercise (150 min/week), and consult a physician regarding antihypertensive evaluation."
        })
        
    if chol >= 200:
        recommendations.append({
            'icon': 'pie-chart',
            'type': 'Lipid Management',
            'text': f"Total cholesterol is {int(chol)} mg/dL. Emphasize Mediterranean diet, soluble fiber, reduce saturated fats, and obtain a full fasting lipid panel (LDL, HDL, Triglycerides)."
        })
        
    if fbs == 1:
        recommendations.append({
            'icon': 'droplet',
            'type': 'Glucose Screening',
            'text': 'Fasting blood glucose > 120 mg/dL. Recommended HbA1c test to screen for diabetes or insulin resistance.'
        })
        
    if exang == 1 or oldpeak >= 1.5:
        recommendations.append({
            'icon': 'heart',
            'type': 'Ischemia Investigation',
            'text': 'Signs of exercise-induced ischemia (exercise angina or ST depression). Exercise stress echocardiography or myocardial perfusion imaging may be warranted.'
        })
        
    return recommendations
