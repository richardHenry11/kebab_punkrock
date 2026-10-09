import sys
import os

# Add parent directory to path so it can import app, models, seed_data
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
