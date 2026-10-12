"""
HL7 FHIR R4 Interoperability Module
Generates standardized FHIR R4 JSON resources for Patient, Observation,
and RiskAssessment according to HL7 international specifications.
"""

from datetime import datetime, timezone

def get_iso_timestamp(patient_dict):
    ts = patient_dict.get('timestamp')
    if ts:
        return ts
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def create_fhir_patient(patient_dict, patient_id=1):
    gender = "male" if int(patient_dict.get('sex', 1)) == 1 else "female"
    name = patient_dict.get('patient_name', f"Patient {patient_id}")
    mrn = patient_dict.get('mrn', f"MRN-{patient_id:05d}")
    
    return {
        "resourceType": "Patient",
        "id": str(patient_id),
        "identifier": [
            {
                "use": "usual",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical Record Number"
                        }
                    ]
                },
                "value": mrn
            }
        ],
        "active": True,
        "name": [
            {
                "use": "official",
                "text": name
            }
        ],
        "gender": gender,
        "telecom": [
            {
                "system": "phone",
                "value": "Confidential"
            }
        ]
    }

def create_fhir_observations(patient_dict, patient_id=1):
    timestamp = get_iso_timestamp(patient_dict)
    observations = []
    
    bp_val = float(patient_dict.get('trestbps', 120))
    observations.append({
        "resourceType": "Observation",
        "id": f"obs-bp-{patient_id}",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Systolic blood pressure"
                }
            ],
            "text": "Resting Blood Pressure"
        },
        "subject": { "reference": f"Patient/{patient_id}" },
        "effectiveDateTime": timestamp,
        "valueQuantity": {
            "value": bp_val,
            "unit": "mmHg",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]"
        }
    })
    
    chol_val = float(patient_dict.get('chol', 200))
    observations.append({
        "resourceType": "Observation",
        "id": f"obs-chol-{patient_id}",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "2093-3",
                    "display": "Cholesterol [Mass/volume] in Serum or Plasma"
                }
            ],
            "text": "Serum Total Cholesterol"
        },
        "subject": { "reference": f"Patient/{patient_id}" },
        "effectiveDateTime": timestamp,
        "valueQuantity": {
            "value": chol_val,
            "unit": "mg/dL",
            "system": "http://unitsofmeasure.org",
            "code": "mg/dL"
        }
    })
    
    hr_val = float(patient_dict.get('thalach', 150))
    observations.append({
        "resourceType": "Observation",
        "id": f"obs-hr-{patient_id}",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate"
                }
            ],
            "text": "Peak Exercise Heart Rate"
        },
        "subject": { "reference": f"Patient/{patient_id}" },
        "effectiveDateTime": timestamp,
        "valueQuantity": {
            "value": hr_val,
            "unit": "/min",
            "system": "http://unitsofmeasure.org",
            "code": "/min"
        }
    })
    
    return observations

def create_fhir_risk_assessment(patient_dict, prediction, probability, risk_level, patient_id=1):
    timestamp = get_iso_timestamp(patient_dict)
    prob_float = float(probability)
    
    return {
        "resourceType": "RiskAssessment",
        "id": f"risk-cardio-{patient_id}",
        "status": "final",
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "occurrenceDateTime": timestamp,
        "method": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "709491003",
                    "display": "Machine learning clinical decision support algorithm"
                }
            ],
            "text": "CardioAI Multi-Model Classifier Pipeline"
        },
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "42343007",
                    "display": "Congestive heart failure / Coronary heart disease screening"
                }
            ],
            "text": "Cardiovascular Disease Risk Assessment"
        },
        "prediction": [
            {
                "outcome": {
                    "text": "Presence of Coronary Artery Disease" if int(prediction) == 1 else "Absence of Coronary Artery Disease"
                },
                "probabilityDecimal": round(prob_float, 4),
                "qualitativeRisk": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/risk-probability",
                            "code": "high" if risk_level == "High Risk" else ("moderate" if risk_level == "Moderate Risk" else "low"),
                            "display": risk_level
                        }
                    ],
                    "text": risk_level
                }
            }
        ],
        "basis": [
            { "reference": f"Observation/obs-bp-{patient_id}" },
            { "reference": f"Observation/obs-chol-{patient_id}" },
            { "reference": f"Observation/obs-hr-{patient_id}" }
        ]
    }
