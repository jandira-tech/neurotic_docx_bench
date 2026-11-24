"""Paths owned by this service."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "work"
LOG_DIR = ROOT / "logs"
