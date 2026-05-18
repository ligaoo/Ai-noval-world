from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path


def new_simulation_dir(outputs_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    suffix = secrets.token_hex(3)
    sim_dir = outputs_dir / f"sim_{ts}_{suffix}"
    sim_dir.mkdir(parents=True, exist_ok=False)
    return sim_dir

