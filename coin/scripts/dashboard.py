#!/usr/bin/env python
"""Render the Rich pipeline dashboard."""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from careerops.pipeline import init_db, dashboard

if __name__ == "__main__":
    init_db()
    dashboard()
