"""Answer-level eval: run the SAME multi-round loop as chat.py / the UI and grade what the user reads.

`run_eval.py` stops after the first model step. This script lets the agent call tools, read the
results and write the final answer, then grades that answer with `answer_checks.py`
(language, real URLs, no duplicates, freshness). Results go to runs_answers/ so they never mix
with the routing runs in runs/.

    python run_answer_eval.py --provider openrouter --version v3 --eval-cases data/eval_answers.json

Case format (data/eval_answers.json):
    {"id": ..., "turns": ["user message", ...], "clarify_reply": "optional reply used only if the
     agent asks a clarifying question", "expect": {"language": "vi", "requires_sources": true,
     "timeframe": "day"}}
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from answer_checks import grade_answer, passed
from chat import run_model_tool_loop
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "artifacts"
DATA_DIR = ROOT / "data"


def run_case(provider: Any, case: dict[str, Any], system_prompt: str, tools: list[dict[str, Any]], model: str | None) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    turns = list(case["turns"])
    clarify_reply = case.get("clarify_reply")
    all_events: list[dict[str, Any]] = []
    transcript: list[dict[str, Any]] = []
    asked_clarify = False
    last: dict[str, Any] = {"status": "no_turns", "assistant_text": ""}

    index = 0
    while index < len(turns):
        user_text = turns[index]
        index += 1
        messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": user_text}]
        last = run_model_tool_loop(provider=provider, messages=messages, tools=tools, model=model, max_tool_rounds=4)
        all_events.extend(last["tool_events"])
        transcript.append({
            "user": user_text,
            "status": last["status"],
            "assistant_text": last["assistant_text"],
            "tool_calls": [{"name": c["name"], "args": c["args"]} for r in last["rounds"] for c in r["tool_calls"]],
        })
        history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": last["assistant_text"] or ""}]
        if last["status"] == "waiting_for_user":
            asked_clarify = True
            if clarify_reply:
                turns.append(clarify_reply)
                clarify_reply = None  # answer at most one clarifying question

    expect = case.get("expect", {})
    timeframe = expect.get("timeframe")
    if timeframe is None:
        for event in reversed(all_events):
            if event.get("tool") in ("lookup", "web_search"):
                timeframe = (event.get("args") or {}).get("timeframe")
                break
    final_text = last["assistant_text"] or ""
    answered = last["status"] == "answered"
    grade = grade_answer(
        final_text, all_events,
        language=expect.get("language", "vi"),
        timeframe=timeframe,
        requires_sources=bool(expect.get("requires_sources")),
    )
    failures = list(grade["failures"])
    if not answered:
        failures.append(f"no final answer (status={last['status']})")
    grade["failures"] = failures
    return {
        "id": case["id"],
        "turns": case["turns"],
        "asked_clarify": asked_clarify,
        "answered": answered,
        "passed": answered and passed(grade),
        "grade": grade,
        "final_text": final_text,
        "transcript": transcript,
        "tool_events": all_events,
    }


def _rate(results: list[dict[str, Any]], key: str) -> float | None:
    applicable = [r["grade"][key] for r in results if r["grade"].get(key) is not None]
    return round(sum(1 for v in applicable if v) / len(applicable), 4) if applicable else None


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    ok = sum(1 for r in results if r["passed"])
    return {
        "total_cases": total,
        "passed_cases": ok,
        "answer_pass_rate": round(ok / total, 4) if total else 0.0,
        "language_rate": _rate(results, "language_ok"),
        "grounded_rate": _rate(results, "grounded_ok"),
        "fresh_rate": _rate(results, "fresh_ok"),
        "no_duplicates_rate": _rate(results, "no_duplicates_ok"),
        "sources_rate": _rate(results, "sources_ok"),
        "clarify_rate": round(sum(1 for r in results if r["asked_clarify"]) / total, 4) if total else 0.0,
    }


def main() -> None:
    for stream in (sys.stdout, sys.stderr):  # chat.run_model_tool_loop prints an emoji
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_lab_env(ROOT)
    parser = argparse.ArgumentParser(description="Answer-level eval (final text, multi-round).")
    parser.add_argument("--version", required=True)
    parser.add_argument("--provider", choices=["openai", "openrouter", "anthropic", "gemini", "ollama"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--eval-cases", type=Path, default=DATA_DIR / "eval_answers.json")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "runs_answers")
    args = parser.parse_args()

    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    artifact_version = build_artifact_version(args.version, args.system_prompt, args.tools)
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    dataset = json.loads(args.eval_cases.read_text(encoding="utf-8"))
    tools = to_openai_tools(load_tool_declarations(args.tools))

    results = []
    for case in dataset["cases"]:
        print(f"Running {case['id']}...", flush=True)
        try:
            results.append(run_case(provider, case, system_prompt, tools, args.model))
        except Exception as exc:  # keep going: one provider hiccup must not lose the whole run
            results.append({"id": case["id"], "turns": case["turns"], "asked_clarify": False, "answered": False,
                            "passed": False, "grade": {"failures": [f"{type(exc).__name__}: {exc}"]},
                            "final_text": "", "transcript": [], "tool_events": []})

    summary = summarize(results)
    now = datetime.now()
    run_id = f"{args.version}_answers_{args.provider}_{now.strftime('%Y%m%dT%H%M%S%f')}"
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    out = args.runs_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id, "version": args.version, **artifact_version_dict(artifact_version),
        "suite": "answers", "provider": args.provider, "model": selected_model,
        "system_prompt": str(args.system_prompt), "tools": str(args.tools), "eval_cases": str(args.eval_cases),
        "generated_at": now.isoformat(timespec="seconds"), "summary": summary, "results": results,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for r in results:
        asked = " (hỏi lại)" if r["asked_clarify"] else ""
        print(f"{r['id']:<28} {'PASS' if r['passed'] else 'FAIL'}{asked}  {'; '.join(r['grade']['failures'])[:110]}")
    print()
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nArtifact version: {artifact_version.artifact_version}\n\nSaved: {out}")


if __name__ == "__main__":
    main()
