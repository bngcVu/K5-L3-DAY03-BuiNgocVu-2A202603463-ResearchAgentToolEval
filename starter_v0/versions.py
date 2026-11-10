"""Version registry: each version is a folder artifacts/versions/<label>/{system_prompt.md,tools.yaml}.

The dropdown in the UI lists these folders plus the live working copy in artifacts/.
To create v1/v2/...: edit artifacts/system_prompt.md + tools.yaml, then use "Lưu thành version".
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"
VERSIONS = ARTIFACTS / "versions"
CURRENT = "current (artifacts/)"
FILES = ("system_prompt.md", "tools.yaml")
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,39}$")


def _natural_key(text: str) -> list:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]


def list_versions() -> list[str]:
    if not VERSIONS.exists():
        return []
    found = [d.name for d in VERSIONS.iterdir() if d.is_dir() and all((d / f).exists() for f in FILES)]
    return sorted(found, key=_natural_key)


def paths_for(label: str) -> tuple[Path, Path]:
    base = ARTIFACTS if label == CURRENT else VERSIONS / label
    return base / FILES[0], base / FILES[1]


def save_snapshot(label: str, *, overwrite: bool = False) -> Path:
    """Copy the working-copy prompt/tools into versions/<label>/. Raises ValueError on bad input."""
    label = label.strip()
    if not LABEL_RE.match(label):
        raise ValueError("Tên version chỉ gồm chữ, số, '.', '_', '-' (tối đa 40 ký tự), ví dụ: v1, v2, v4-local.")
    target = VERSIONS / label
    if target.exists() and not overwrite:
        raise ValueError(f"Version '{label}' đã tồn tại. Chọn tên khác (không ghi đè để giữ bằng chứng).")
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(ARTIFACTS / name, target / name)
    return target
