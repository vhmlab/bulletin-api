import sys
from pathlib import Path

# Ensure repository root is on sys.path so `import app` works regardless of cwd
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
