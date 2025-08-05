import sys
import os

# Add backend path
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
sys.path.append(backend_path)

# Import Units schemas
try:
    from schemas.core import UnitCreate, UnitRead, UnitUpdate
    print("✅ Unit schemas imported successfully!")
except ImportError as e:
    print(f"❌ Import error: {e}")

