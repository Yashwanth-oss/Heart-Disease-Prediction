"""
Test Suite Wrapper
Forwards test execution to backend/test_backend.py.
"""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.chdir(BACKEND_DIR)

import test_backend

if __name__ == '__main__':
    unittest.main(module=test_backend)
