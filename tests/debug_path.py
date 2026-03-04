import sys
import os

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print("\nSearch paths (sys.path):")
for path in sys.path:
    print(f" - {path}")

try:
    import pandas
    print(f"\n[OK] pandas found at: {pandas.__file__}")
    print(f"pandas version: {pandas.__version__}")
except ImportError as e:
    print(f"\n[ERROR] pandas NOT found: {e}")

# Check for virtual environment indicators
print(f"\nVIRTUAL_ENV env var: {os.environ.get('VIRTUAL_ENV', 'Not set')}")
print(f"sys.prefix: {sys.prefix}")
print(f"sys.base_prefix: {sys.base_prefix}")
