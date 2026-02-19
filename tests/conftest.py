"""Shared test fixtures for openclaw-homeassistant."""

import sys
from pathlib import Path

# Ensure the src directory is on the path for local development
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
