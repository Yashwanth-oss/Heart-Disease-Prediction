import os
import json
import warnings
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')

DATA_PATH = 'heart.csv'
METRICS_PATH = 'model_metrics.json'
FEATURE_IMPORTANCE_PATH = 'feature_importance.json'

def load_and_preprocess_data():
    """
    Loads dataset, analyzes duplicates, and prepares features/target.
    """
    print("\n" + "="*70)
    print("STEP 1: DATA INGESTION & DATA LEAKAGE PREVENTION")
    print("="*70)
    
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Error: '{DATA_PATH}' not found in project directory.")
        
    raw_df = pd.read_csv(DATA_PATH)
    total_records = len(raw_df)
    duplicates_count = raw_df.duplicated().sum()
    
    print(f"Total records in '{DATA_PATH}': {total_records}")
    print(f"Duplicate records detected: {duplicates_count} ({(duplicates_count/total_records)*100:.1f}%)")
    
    # Crucial Data Science Fix:
    # Deduplicate dataset to prevent identical patients leaking into test folds
    df = raw_df.drop_duplicates().reset_index(drop=True)
    print(f"Unique patient records for training & validation: {len(df)}")
    
    # Feature classification
    num_features = ['age', 'trestbps', 'chol', 'thalach', 'oldpeak']
    cat_features = ['sex', 'cp', 'fbs', 'restecg', 'exang', 'slope', 'ca', 'thal']
    
    X = df.drop('target', axis=1)
    y = df['target']
    
    print(f"Features: {list(X.columns)}")
    print(f"Target Distribution: {dict(y.value_counts())} (0: No Disease, 1: Heart Disease)")
    
    return raw_df, df, X, y, num_features, cat_features

def build_preprocessor(num_features, cat_features):
    """
    Creates a ColumnTransformer that standardizes continuous variables
    and applies One-Hot Encoding to categorical variables.
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_features),
            ('cat', OneHotEncoder(drop='first', handle_unknown='ignore', sparse_output=False), cat_features)
        ],
        remainder='drop'
    )
    return preprocessor

def evaluate_models(X, y, preprocessor):
    """
    Runs 5-fold Stratified Cross-Validation across multiple classifiers
    and benchmarks accuracy, recall, precision, f1, and roc_auc.
    """
    print("\n" + "="*70)
    print("STEP 2: 5-FOLD STRATIFIED CROSS-VALIDATION BENCHMARK")
    print("="*70)
    
    candidate_models = {
        'Logistic Regression': LogisticRegression(C=0.5, max_iter=1000, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=120, max_depth=5, min_samples_split=4, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42),
        'XGBoost': XGBClassifier(n_estimators=90, max_depth=3, learning_rate=0.05, eval_metric='logloss', random_state=42),
        'K-Nearest Neighbors': KNeighborsClassifier(n_neighbors=7),
        'Support Vector Machine': SVC(kernel='rbf', C=1.0, probability=True, random_state=42)
    }
    
    # Also add a Soft-Voting Ensemble combining top diverse models
    voting_ensemble = VotingClassifier(
        estimators=[
            ('lr', LogisticRegression(C=0.5, max_iter=1000, random_state=42)),
            ('rf', RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)),
            ('xgb', XGBClassifier(n_estimators=80, max_depth=3, learning_rate=0.05, eval_metric='logloss', random_state=42))
        ],
        voting='soft'
    )
    candidate_models['Voting Ensemble (Soft)'] = voting_ensemble
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ['accuracy', 'recall', 'precision', 'f1', 'roc_auc']
    
    results = {}
    print(f"{'Model Name':<26} | {'Accuracy':<10} | {'Recall':<10} | {'Precision':<10} | {'F1-Score':<10} | {'ROC-AUC':<10}")
    print("-" * 88)
    
    for name, clf in candidate_models.items():
        pipeline = Pipeline([
            ('preprocessor', preprocessor),
            ('classifier', clf)
        ])
        
        cv_scores = cross_validate(pipeline, X, y, cv=cv, scoring=scoring)
        
        acc = float(cv_scores['test_accuracy'].mean())
        rec = float(cv_scores['test_recall'].mean())
        prec = float(cv_scores['test_precision'].mean())
        f1 = float(cv_scores['test_f1'].mean())
        auc = float(cv_scores['test_roc_auc'].mean())
        
        results[name] = {
            'accuracy': acc,
            'recall': rec,
            'precision': prec,
            'f1': f1,
            'roc_auc': auc,
            'accuracy_std': float(cv_scores['test_accuracy'].std()),
            'roc_auc_std': float(cv_scores['test_roc_auc'].std())
        }
        
        print(f"{name:<26} | {acc*100:6.2f}%    | {rec*100:6.2f}%    | {prec*100:6.2f}%    | {f1*100:6.2f}%    | {auc*100:6.2f}%")
        
    return candidate_models, results

def select_and_fit_best_model(candidate_models, results, X, y, preprocessor):
    """
    Selects the best model (optimizing for balanced ROC-AUC & Recall)
    and trains on the train-test split for deep confusion matrix reporting,
    then trains on the entire dataset for final deployment.
    """
    print("\n" + "="*70)
    print("STEP 3: MODEL SELECTION & IN-DEPTH VALIDATION")
    print("="*70)
    
    # We rank by combined score of ROC-AUC and Recall (Sensitivity to avoid missing heart disease)
    ranked_models = sorted(
        results.keys(),
        key=lambda m: (results[m]['roc_auc'] * 0.6 + results[m]['recall'] * 0.4),
        reverse=True
    )
    
    best_model_name = ranked_models[0]
    best_stats = results[best_model_name]
    print(f"Top-Ranked Model: '{best_model_name}'")
    print(f"CV ROC-AUC: {best_stats['roc_auc']*100:.2f}% (±{best_stats['roc_auc_std']*100:.2f}%)")
    print(f"CV Recall (Sensitivity): {best_stats['recall']*100:.2f}%")
    print(f"CV Accuracy: {best_stats['accuracy']*100:.2f}% (±{best_stats['accuracy_std']*100:.2f}%)")
    
    # Train-test split (80-20) for detailed holdout metrics
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    eval_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', candidate_models[best_model_name])
    ])
    eval_pipeline.fit(X_train, y_train)
    
    y_pred = eval_pipeline.predict(X_test)
    y_proba = eval_pipeline.predict_proba(X_test)[:, 1] if hasattr(eval_pipeline, 'predict_proba') else None
    
    cm = confusion_matrix(y_test, y_pred).tolist()
    cr = classification_report(y_test, y_pred, target_names=['No Disease', 'Heart Disease'], output_dict=True)
    
    print("\nHold-out Test Set Confusion Matrix (20% sample):")
    print(f"[[TN={cm[0][0]}, FP={cm[0][1]}], [FN={cm[1][0]}, TP={cm[1][1]}]]")
    
    # Final Fit on entire unique dataset
    final_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', candidate_models[best_model_name])
    ])
    final_pipeline.fit(X, y)
    
    # Compute feature importances
    feature_importance_dict = compute_feature_importance(final_pipeline, X, y)
    
    return best_model_name, final_pipeline, results, cm, cr, feature_importance_dict

def compute_feature_importance(pipeline, X, y):
    """
    Extracts feature importances or linear weights from the trained pipeline.
    """
    preprocessor = pipeline.named_steps['preprocessor']
    clf = pipeline.named_steps['classifier']
    
    # Get encoded feature names
    cat_names = []
    if hasattr(preprocessor.named_transformers_['cat'], 'get_feature_names_out'):
        cat_names = list(preprocessor.named_transformers_['cat'].get_feature_names_out())
    
    num_names = list(preprocessor.transformers_[0][2])
    all_feature_names = num_names + cat_names
    
    importance_scores = {}
    
    # Tree model feature importances
    if hasattr(clf, 'feature_importances_'):
        scores = clf.feature_importances_
        for name, score in zip(all_feature_names, scores):
            importance_scores[name] = float(score)
    # Linear model coefficients
    elif hasattr(clf, 'coef_'):
        scores = np.abs(clf.coef_[0])
        for name, score in zip(all_feature_names, scores):
            importance_scores[name] = float(score)
    # Ensemble with estimators
    elif hasattr(clf, 'estimators_'):
        all_scores = []
        for est in clf.estimators_:
            if hasattr(est, 'feature_importances_'):
                all_scores.append(est.feature_importances_)
            elif hasattr(est, 'coef_'):
                all_scores.append(np.abs(est.coef_[0]))
        if all_scores:
            mean_scores = np.mean(all_scores, axis=0)
            for name, score in zip(all_feature_names, mean_scores):
                importance_scores[name] = float(score)
                
    # Sort descending
    sorted_importances = dict(sorted(importance_scores.items(), key=lambda x: x[1], reverse=True))
    return sorted_importances

def save_artifacts(best_name, final_pipeline, results, cm, cr, feature_importances, X):
    """
    Saves trained pipeline, model metrics, feature names, and legacy fallback files.
    """
    print("\n" + "="*70)
    print("STEP 4: SAVING PRODUCTION PIPELINE & METRICS")
    print("="*70)
    
    # 1. Save complete modern end-to-end Pipeline
    joblib.dump(final_pipeline, 'model_pipeline.pkl')
    print("[OK] Saved modern end-to-end pipeline: 'model_pipeline.pkl'")
    
    # 2. Save backward-compatible legacy artifacts for existing code
    clf = final_pipeline.named_steps['classifier']
    preprocessor = final_pipeline.named_steps['preprocessor']
    scaler = preprocessor.named_transformers_['num']
    
    joblib.dump(clf, 'model.pkl')
    joblib.dump(scaler, 'scaler.pkl')
    joblib.dump(list(X.columns), 'feature_names.pkl')
    print("[OK] Saved backward-compatible legacy artifacts: 'model.pkl', 'scaler.pkl', 'feature_names.pkl'")
    
    # 3. Save comprehensive metrics and comparison data
    metrics_data = {
        'best_model': best_name,
        'model_comparison': results,
        'test_confusion_matrix': cm,
        'test_classification_report': cr,
        'training_timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        'dataset_size_unique': len(X),
        'features': list(X.columns)
    }
    with open(METRICS_PATH, 'w', encoding='utf-8') as f:
        json.dump(metrics_data, f, indent=4)
    print(f"[OK] Saved detailed validation metrics: '{METRICS_PATH}'")
    
    with open(FEATURE_IMPORTANCE_PATH, 'w', encoding='utf-8') as f:
        json.dump(feature_importances, f, indent=4)
    print(f"[OK] Saved feature importance rankings: '{FEATURE_IMPORTANCE_PATH}'")
    
    print("\n" + "="*70)
    print("TRAINING PIPELINE COMPLETE & READY FOR PRODUCTION!")
    print("="*70 + "\n")

if __name__ == '__main__':
    raw_df, df, X, y, num_features, cat_features = load_and_preprocess_data()
    preprocessor = build_preprocessor(num_features, cat_features)
    candidate_models, results = evaluate_models(X, y, preprocessor)
    best_name, final_pipeline, results, cm, cr, feature_importances = select_and_fit_best_model(
        candidate_models, results, X, y, preprocessor
    )
    save_artifacts(best_name, final_pipeline, results, cm, cr, feature_importances, X)
