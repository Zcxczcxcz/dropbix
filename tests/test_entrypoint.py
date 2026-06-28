import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import main as root_main


def test_main_entrypoint_exists() -> None:
    assert callable(root_main.main)
