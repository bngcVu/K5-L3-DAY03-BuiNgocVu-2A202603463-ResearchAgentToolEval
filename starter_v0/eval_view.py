"""Streamlit screen: browse eval runs and compare versions side by side.

Reads every runs/*.json written by run_eval.py, so new versions (v2, v3, v4-local, ...)
show up automatically; nothing here hard-codes a version name.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

METRICS = [
    ("case_accuracy", "Case accuracy"),
    ("tool_routing_accuracy", "Tool routing"),
    ("argument_accuracy", "Argument"),
    ("multiturn_accuracy", "Multi-turn"),
]


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
    return "—" if value is None else f"{value * 100:.0f}%"


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


def render(runs_dir: Path) -> None:
    st.title("📊 So sánh version")
    st.caption("Đọc từ các file `runs/*.json`. Chạy thêm `run_eval.py` với `--version` mới là version đó tự xuất hiện ở đây.")

    signature = tuple((p.name, p.stat().st_mtime_ns) for p in sorted(runs_dir.glob("*.json"))) if runs_dir.exists() else ()
    runs = _load_runs(str(runs_dir), signature)
    if not runs:
        st.info("Chưa có run nào. Chạy: `python run_eval.py --provider openrouter --version v0 --suite base --eval-cases data/eval_base.json`")
        return

    # ---------- 1. All runs ----------
    st.subheader("1. Tất cả các lần chạy")
    table = pd.DataFrame([{
        "Version": r["version"],
        "Thời gian": r["generated_at"].replace("T", " "),
        "Đạt": f"{r['summary'].get('passed_cases')}/{r['summary'].get('total_cases')}",
        "Case acc": _pct(r["summary"].get("case_accuracy")),
        "Routing": _pct(r["summary"].get("tool_routing_accuracy")),
        "Args": _pct(r["summary"].get("argument_accuracy")),
        "Multi-turn": _pct(r["summary"].get("multiturn_accuracy")),
        "Suite": r["suite"],
        "Model": r["model"],
        "Prompt hash": r["prompt_hash"],
        "Tools hash": r["tools_hash"],
        "File": r["file"],
    } for r in runs])
    st.dataframe(table, width="stretch", hide_index=True)

    # Same label but different prompt/tools hash means the artifacts changed under the same name.
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
    st.subheader("2. Chọn các run để so sánh")
    taken: set[str] = set()
    labels = [_label(r, taken) for r in runs]
    by_label = dict(zip(labels, runs))
    # Default: latest run of each version, in version order.
    latest: dict[str, str] = {}
    for label, run in zip(labels, runs):
        latest[run["version"]] = label
    default = list(latest.values())[:4]
    chosen = st.multiselect("Run", labels, default=default, help="Chọn từ 2 run trở lên. Run đầu tiên được dùng làm mốc để tính chênh lệch.")
    if len(chosen) < 2:
        st.info("Chọn ít nhất 2 run để so sánh.")
        return
    selected = [by_label[label] for label in chosen]

    # ---------- 3. Metrics ----------
    st.subheader("3. Chỉ số")
    metric_rows = []
    for key, name in METRICS:
        row: dict[str, Any] = {"Chỉ số": name}
        base = selected[0]["summary"].get(key)
        for label, run in zip(chosen, selected):
            row[label] = run["summary"].get(key)
        last = selected[-1]["summary"].get(key)
        row["Δ (cuối − đầu)"] = None if base is None or last is None else last - base
        metric_rows.append(row)
    metrics = pd.DataFrame(metric_rows).set_index("Chỉ số")
    st.dataframe(
        metrics.style.format(lambda v: "—" if v is None or pd.isna(v) else f"{v * 100:.0f}%", subset=chosen)
        .format(lambda v: "—" if v is None or pd.isna(v) else f"{v * 100:+.0f} điểm", subset=["Δ (cuối − đầu)"]),
        width="stretch",
    )
    st.bar_chart(metrics[chosen].astype(float).T, height=260)

    # ---------- 4. Per-case matrix ----------
    st.subheader("4. Từng case: version nào đúng, version nào sai")
    case_ids: list[str] = []
    for run in selected:
        for item in run["results"]:
            if item["id"] not in case_ids:
                case_ids.append(item["id"])
    index = [{item["id"]: item for item in run["results"]} for run in selected]

    rows = []
    for cid in case_ids:
        marks = [_status(idx.get(cid)) for idx in index]
        row = {"Case": cid, **dict(zip(chosen, marks))}
        row["Khác nhau"] = "⚠️" if len(set(m for m in marks if m != "—")) > 1 else ""
        rows.append(row)
    matrix = pd.DataFrame(rows)
    changed_only = st.checkbox("Chỉ hiện case có kết quả khác nhau giữa các run", value=False)
    shown = matrix[matrix["Khác nhau"] == "⚠️"] if changed_only else matrix
    st.dataframe(shown, width="stretch", hide_index=True)
    st.caption(f"{(matrix['Khác nhau'] == '⚠️').sum()}/{len(matrix)} case có kết quả khác nhau giữa các run đã chọn. ✅ đúng · ❌ sai · — run đó không có case này.")

    # ---------- 5. Case detail ----------
    st.subheader("5. Chi tiết một case")
    focus = st.selectbox("Case", case_ids, index=case_ids.index(shown["Case"].iloc[0]) if len(shown) else 0)
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
    first = index[0].get(focus) or next((i.get(focus) for i in index if i.get(focus)), None)
    if first:
        with st.expander("Đầu vào và kết quả mong đợi"):
            st.write(first.get("input"))
            st.json(first.get("expect", {}), expanded=True)
