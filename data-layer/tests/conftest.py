import sys
import os

# Add data-layer/import and data-layer/import/da to sys.path.
# (The 'import' directory can't be imported as a package since 'import' is a
# Python keyword, so we add it to the path instead.)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "import"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "import", "da"))
