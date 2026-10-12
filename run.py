"""
CardioAI Root Launcher
Launches the CardioAI Backend & Decoupled Frontend Server.
"""

import os
import sys

# Ensure backend directory is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Switch working directory to backend so all relative database & model paths work seamlessly
os.chdir(BACKEND_DIR)

from app import app, init_db, load_ml_artifacts

if __name__ == '__main__':
    print("=" * 65)
    print("  CardioAI Clinical Decision Support Platform")
    print("=" * 65)
    print("  - Backend REST API & FHIR Server: Active")
    print("  - Decoupled Frontend Client:      Active")
    print("  - Access the application at:      http://127.0.0.1:5000")
    print("=" * 65)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
