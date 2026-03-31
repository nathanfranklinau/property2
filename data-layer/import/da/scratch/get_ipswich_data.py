#!/usr/bin/env python3
"""Quick wrapper to run Ipswich importer."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from import_ipswich_da import CONFIG
from import_developmenti_da import run

if __name__ == "__main__":
    run(CONFIG)
