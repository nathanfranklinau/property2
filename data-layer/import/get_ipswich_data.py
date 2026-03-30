#!/usr/bin/env python3
"""Quick wrapper to run Ipswich importer."""

import sys
sys.path.insert(0, '.')

from import_developmenti_da import COUNCILS, run

if __name__ == "__main__":
    run(COUNCILS["ipswich"])
