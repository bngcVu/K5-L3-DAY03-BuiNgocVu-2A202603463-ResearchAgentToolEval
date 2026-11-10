"""Streamlit screen: run an eval for a chosen version and compare versions side by side.

Reads every runs/*.json written by run_eval.py, so new versions (v2, v3, v4-local, ...)
show up automatically; nothing here hard-codes a version name.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent
METRICS = [
    ("case_accuracy", "Case accuracy"),
    ("tool_routing_accuracy", "Tool routing"),
    ("argument_accuracy", "Argument"),
    ("multiturn_accuracy", "Multi-turn"),
]
GREEN, RED = "#3fb950", "#f85149"


def _natural_key(text: str) -> list[Any]:
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]


@st.cache_data(show_spinner=False)
def _load_runs(runs_dir: str, signature: tuple) -> list[dict[str, Any]]:
    """`signature` (file names + mtimes) busts the cache when runs/ changes."""
    runs: list[dict[str, Any]] = []
    for path in sorted(Path(runs_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict) or "results" not in data or "summary" not in data:
            continue
        runs.append({
            "file": path.name,
            "version": str(data.get("version", path.stem)),
            "artifact_version": data.get("artifact_version", ""),
            "prompt_hash": (data.get("prompt_hash") or "")[:8],
            "tools_hash": (data.get("tools_hash") or "")[:8],
            "suite": data.get("suite", ""),
            "model": data.get("model", ""),
            "generated_at": data.get("generated_at", ""),
            "summary": data["summary"],
            "results": data["results"],
        })
    runs.sort(key=lambda r: (_natural_key(r["version"]), r["generated_at"]))
    return runs


def _pct(value: Any) -> str:
    return "—" if value is None or pd.isna(value) else f"{value * 100:.0f}%"


def _label(run: dict[str, Any], taken: set[str]) -> str:
    acc = run["summary"].get("case_accuracy")
    base = f"{run['version']} · {run['generated_at'][5:16].replace('T', ' ')} · {_pct(acc)}"
    label, n = base, 2
    while label in taken:
        label, n = f"{base} #{n}", n + 1
    taken.add(label)
    return label


def _status(result: dict[str, Any] | None) -> str:
    if result is None:
        return "—"
    return "✅" if result["result"].get("passed") else "❌"


def run_eval_subprocess(
    *,
    version: str,
    prompt_path: Path,
    tools_path: Path,
    provider: str,
    model: str | None = None,
    eval_cases: Path = ROOT / "data" / "eval_base.json",
    runs_dir: Path = ROOT / "runs",
    suite: str = "base",
    timeout: int = 900,
) -> tuple[int, str]:
    """Run run_eval.py with the given version's prompt/tools. Returns (exit_code, combined output)."""
    cmd = [
        sys.executable, str(ROOT / "run_eval.py"),
        "--provider", provider, "--version", version, "--suite", suite,
        "--eval-cases", str(eval_cases),
        "--system-prompt", str(prompt_path), "--tools", str(tools_path),
        "--runs-dir", str(runs_dir),
    ]
    if model:
        cmd += ["--model", model]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"Hết thời gian chờ ({timeout}s)."
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _delta_style(value: Any) -> str:
    if value is None or pd.isna(value) or value == 0:
        return "color: #8b949e"
    return f"color: {GREEN}; font-weight: 600" if value > 0 else f"color: {RED}; font-weight: 600"


def render(
    runs_dir: Path,
    *,
    version: str,
    run_label: str,
    prompt_path: Path,
    tools_path: Path,
    provider: str,
    model: str | None,
) -> None:
    # ---------- 0. Run an eval for the selected version ----------
    st.subheader("▶ Chạy eval cho version đang chọn")
    left, right = st.columns([3, 2])
    with left:
        st.write(f"Version: **{version}** · prompt `{prompt_path.parent.name}/{prompt_path.name}` · tools `{tools_path.name}`")
        st.caption(f"Provider: `{provider}` · model: `{model or 'mặc định'}` · 20 case base, mất khoảng 1 phút và **tốn credit API**. "
                   f"Kết quả ghi vào `runs/` với nhãn `{run_label}`.")
    with right:
        go = st.button("▶ Chạy eval ngay", type="primary", width="stretch")
    if go:
        with st.spinner(f"Đang chạy eval cho {run_label}… (khoảng 1 phút)"):
            code, output = run_eval_subprocess(
                version=run_label, prompt_path=prompt_path, tools_path=tools_path,
                provider=provider, model=model, runs_dir=runs_dir,
            )
        tail = "\n".join(output.strip().splitlines()[-30:])
        if code == 0:
            st.success(f"Xong. Run `{run_label}` đã được thêm vào bảng bên dưới.")
        else:
            st.error(f"Eval thất bại (exit code {code}).")
        with st.expander("Output", expanded=code != 0):
            st.code(tail or "(không có output)")

    st.divider()
    st.subheader("📊 So sánh version")
    st.caption("Đọc từ `runs/*.json`. Chạy eval cho một version mới là nó tự xuất hiện ở đây.")

    signature = tuple((p.name, p.stat().st_mtime_ns) for p in sorted(runs_dir.glob("*.json"))) if runs_dir.exists() else ()
    runs = _load_runs(str(runs_dir), signature)
    if not runs:
        st.info("Chưa có run nào. Bấm **▶ Chạy eval ngay** ở trên để tạo run đầu tiên.")
        return

    # ---------- 1. All runs ----------
    with st.expander(f"Tất cả các lần chạy ({len(runs)})", expanded=False):
        st.dataframe(pd.DataFrame([{
            "Version": r["version"],
            "Thời gian": r["generated_at"].replace("T", " "),
            "Đạt": f"{r['summary'].get('passed_cases')}/{r['summary'].get('total_cases')}",
            "Case acc": _pct(r["summary"].get("case_accuracy")),
            "Routing": _pct(r["summary"].get("tool_routing_accuracy")),
            "Args": _pct(r["summary"].get("argument_accuracy")),
            "Multi-turn": _pct(r["summary"].get("multiturn_accuracy")),
            "Model": r["model"],
            "Prompt hash": r["prompt_hash"],
            "Tools hash": r["tools_hash"],
            "File": r["file"],
        } for r in runs]), width="stretch", hide_index=True)

    by_version: dict[str, set[tuple[str, str]]] = {}
    for r in runs:
        by_version.setdefault(r["version"], set()).add((r["prompt_hash"], r["tools_hash"]))
    mixed = [v for v, hashes in by_version.items() if len(hashes) > 1]
    if mixed:
        st.warning(
            "Các version sau có nhiều lần chạy với **prompt/tools khác nhau** (khác hash): "
            + ", ".join(f"`{v}`" for v in mixed)
            + ". Hãy so sánh theo hash, không chỉ theo tên version."
        )

    # ---------- 2. Pick runs ----------
    taken: set[str] = set()
    labels = [_label(r, taken) for r in runs]
    by_label = dict(zip(labels, runs))
    latest: dict[str, str] = {}
    for label, run in zip(labels, runs):
        latest[run["version"]] = label
    chosen = st.multiselect(
        "Chọn các run để so sánh", labels, default=list(latest.values())[:4],
        help="Mặc định: lần chạy mới nhất của mỗi version. Chọn từ 2 run trở lên.",
    )
    if len(chosen) < 2:
        st.info("Chọn ít nhất 2 run để so sánh.")
        return
    selected = [by_label[label] for label in chosen]
    baseline_label = st.selectbox("Mốc so sánh (Δ tính so với run này)", chosen, index=0)
    baseline = by_label[baseline_label]

    # ---------- 3. Metrics with delta ----------
    rows: list[dict[str, Any]] = []
    for label, run in zip(chosen, selected):
        row: dict[str, Any] = {"Run": label}
        for key, name in METRICS:
            value, base_value = run["summary"].get(key), baseline["summary"].get(key)
            row[name] = value
            is_base = label == baseline_label
            row[f"Δ {name}"] = None if is_base or value is None or base_value is None else (value - base_value) * 100
        rows.append(row)
    table = pd.DataFrame(rows).set_index("Run")
    metric_cols = [name for _, name in METRICS]
    delta_cols = [f"Δ {name}" for name in metric_cols]
    styler = (
        table.style
        .format(lambda v: _pct(v), subset=metric_cols)
        .format(lambda v: "mốc" if v is None or pd.isna(v) else f"{v:+.0f} điểm", subset=delta_cols)
    )
    (styler.map if hasattr(styler, "map") else styler.applymap)(_delta_style, subset=delta_cols)
    st.markdown("##### Chỉ số")
    st.dataframe(styler, width="stretch")
    st.bar_chart(table[metric_cols].astype(float).T, height=260)

    # ---------- 4. Per-case matrix ----------
    st.markdown("##### Từng case: run nào đúng, run nào sai")
    case_ids: list[str] = []
    for run in selected:
        for item in run["results"]:
            if item["id"] not in case_ids:
                case_ids.append(item["id"])
    index = [{item["id"]: item for item in run["results"]} for run in selected]
    matrix_rows = []
    for cid in case_ids:
        marks = [_status(idx.get(cid)) for idx in index]
        row = {"Case": cid, **dict(zip(chosen, marks))}
        row["Khác nhau"] = "⚠️" if len(set(m for m in marks if m != "—")) > 1 else ""
        matrix_rows.append(row)
    matrix = pd.DataFrame(matrix_rows)
    changed_only = st.checkbox("Chỉ hiện case có kết quả khác nhau giữa các run", value=False)
    shown = matrix[matrix["Khác nhau"] == "⚠️"] if changed_only else matrix
    st.dataframe(shown, width="stretch", hide_index=True)
    st.caption(f"{(matrix['Khác nhau'] == '⚠️').sum()}/{len(matrix)} case có kết quả khác nhau. ✅ đúng · ❌ sai · — run đó không có case này.")

    # ---------- 5. Case detail ----------
    st.markdown("##### Chi tiết một case")
    options = list(shown["Case"]) or case_ids
    focus = st.selectbox("Case", options)
    columns = st.columns(len(selected))
    for column, label, idx in zip(columns, chosen, index):
        item = idx.get(focus)
        with column:
            st.markdown(f"**{label}**")
            if item is None:
                st.caption("Không có case này.")
                continue
            result = item["result"]
            if result.get("passed"):
                st.success("PASS")
            else:
                st.error(f"FAIL · {result.get('observed_mismatch') or result.get('failure_type')}")
                for failure in result.get("failures", []):
                    st.write(f"- {failure}")
            st.caption("Tool agent gọi")
            st.json(result.get("actual_tool_calls", []), expanded=True)
            if result.get("actual_text"):
                st.caption("Text trả lời")
                st.write(result["actual_text"])
    first = next((i.get(focus) for i in index if i.get(focus)), None)
    if first:
        with st.expander("Đầu vào và kết quả mong đợi"):
            st.write(first.get("input"))
            st.json(first.get("expect", {}), expanded=True)
