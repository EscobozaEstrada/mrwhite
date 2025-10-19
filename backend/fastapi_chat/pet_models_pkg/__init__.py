# Models package - Re-export everything from the original models.py

# Import everything from the parent directory's models.py file
import importlib.util
import os

# Load the original models.py module
models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.py')
spec = importlib.util.spec_from_file_location("original_models", models_path)
original_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original_models)

# Re-export everything from original models.py
for name in dir(original_models):
    if not name.startswith('_'):
        globals()[name] = getattr(original_models, name)

# Also make our pet models available
from .pet_models import PetProfile, PetProfileCreate, PetProfileUpdate, PetProfileResponse
