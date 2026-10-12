"""
Legacy Training Wrapper
Forwards execution to backend/training.py for seamless backward compatibility.
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.chdir(BACKEND_DIR)

import training

if __name__ == '__main__':
    training.train_and_evaluate()
