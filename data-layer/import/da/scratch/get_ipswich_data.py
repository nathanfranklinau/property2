#!/usr/bin/env python3
"""Quick wrapper to run Ipswich importer."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from import_developmenti_da import COUNCILS, run

if __name__ == "__main__":
    run(COUNCILS["ipswich"])
