"""Streamlit UI for the research agent.

Run:  streamlit run app.py
Reuses chat.run_model_tool_loop, so the UI and `python chat.py` share one agent loop,
and every session is logged to transcripts/*.transcript.json like chat.py does.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

# chat.run_model_tool_loop prints an emoji; on Windows the default console codec (cp1252)
# cannot encode it and raises UnicodeEncodeError. Force UTF-8 so the UI works everywhere.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from chat import ARTIFACTS_DIR, ROOT, now_iso, run_model_tool_loop, safe_slug, trim_history, write_transcript
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")

PROVIDERS = ["openrouter", "openai", "anthropic", "gemini", "ollama"]
SAMPLES = [
    "Tweet mới nhất của Sam Altman là gì?",
    "Tin tức AI hôm nay có gì nổi bật?",
    "Mọi người đang bàn gì về GPT-5 trên Twitter?",
    "Tóm tắt 5 tweet mới nhất giúp mình",
    "Đăng bản tin này lên Telegram giúp mình",
]


def init_state() -> None:
    st.session_state.setdefault("messages", [])  # what is rendered
    st.session_state.setdefault("history", [])   # plain user/assistant text sent to the model
    st.session_state.setdefault("turns", [])     # transcript records
    st.session_state.setdefault("queued", None)  # text injected by a button
    st.session_state.setdefault("transcript_id", None)


def reset_chat() -> None:
    for key in ("messages", "history", "turns"):
        st.session_state[key] = []
    st.session_state["queued"] = None
    st.session_state["transcript_id"] = None


def queue(text: str) -> None:
    st.session_state["queued"] = text


def render_tool_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        result = event.get("result", {})
        label = f"🔧 {event.get('tool')}({json.dumps(event.get('args', {}), ensure_ascii=False)})"
        with st.expander(label, expanded=False):
            st.json(result, expanded=False)


def pending_yes_no(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in events:
        result = event.get("result", {})
        if isinstance(result, dict) and result.get("awaiting_user") and result.get("response_type") == "yes_no":
            return result
    return None


init_state()

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ Cấu hình")
    provider_name = st.selectbox("Provider", PROVIDERS, index=0)
    model = st.text_input("Model (để trống = mặc định)", value="") or None
    version = st.text_input("Version label", value="ui")
    system_prompt_path = Path(st.text_input("System prompt", value=str(ARTIFACTS_DIR / "system_prompt.md")))
    tools_path = Path(st.text_input("Tools", value=str(ARTIFACTS_DIR / "tools.yaml")))
    history_window = st.slider("Số cặp hội thoại giữ lại", 1, 10, 5)
    max_rounds = st.slider("Số vòng tool tối đa", 1, 6, 4)
    if st.button("🗑️ Cuộc trò chuyện mới", use_container_width=True):
        reset_chat()
        st.rerun()

    st.divider()
    st.subheader("Câu hỏi mẫu")
    for sample in SAMPLES:
        st.button(sample, key=f"sample_{sample}", on_click=queue, args=(sample,), use_container_width=True)

try:
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(declarations)
    artifact_version = build_artifact_version(version, system_prompt_path, tools_path)
except Exception as exc:  # bad path / invalid yaml
    st.error(f"Không đọc được prompt/tools: {type(exc).__name__}: {exc}")
    st.stop()

with st.sidebar:
    st.divider()
    st.caption(f"artifact_version: `{artifact_version.artifact_version}`")
    st.caption(f"{len(declarations)} tools: " + ", ".join(item["name"] for item in declarations))

st.title("🔎 Research Agent")
st.caption("Tìm tin, tweet, đọc URL, paper và gửi bản tin lên Telegram (chỉ khi bạn xác nhận).")

# ---------------- History ----------------
for index, message in enumerate(st.session_state["messages"]):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("tool_events"):
            render_tool_events(message["tool_events"])
        if message.get("error"):
            st.error(message["error"])

# Yes/No buttons when the agent asked a confirmation (e.g. before sending to Telegram).
messages = st.session_state["messages"]
if messages and messages[-1]["role"] == "assistant":
    confirm = pending_yes_no(messages[-1].get("tool_events", []))
    if confirm:
        yes_col, no_col, _ = st.columns([1, 1, 6])
        yes_col.button("✅ Có, gửi", on_click=queue, args=("Có, mình xác nhận gửi.",), key=f"yes_{len(messages)}")
        no_col.button("❌ Không", on_click=queue, args=("Không, đừng gửi.",), key=f"no_{len(messages)}")

# ---------------- New turn ----------------
user_text = st.chat_input("Nhập yêu cầu…") or st.session_state.pop("queued", None)
if user_text:
    with st.chat_message("user"):
        st.markdown(user_text)

    request_messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state["history"], history_window),
        {"role": "user", "content": user_text},
    ]
    turn: dict[str, Any] = {
        "turn_index": len(st.session_state["turns"]) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    assistant: dict[str, Any] = {"role": "assistant", "content": "", "tool_events": []}

    with st.chat_message("assistant"):
        with st.spinner("Agent đang xử lý…"):
            try:
                provider = make_provider(provider_name)
                result = run_model_tool_loop(
                    provider=provider,
                    messages=request_messages,
                    tools=openai_tools,
                    model=model,
                    max_tool_rounds=max_rounds,
                )
                turn.update(result)
                assistant["content"] = result["assistant_text"] or "_(không có nội dung trả lời)_"
                assistant["tool_events"] = result["tool_events"]
                st.session_state["history"] += [
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": result["assistant_text"] or ""},
                ]
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                turn.update({"status": "provider_error", "error": error})
                assistant["content"] = "Đã xảy ra lỗi khi gọi model."
                assistant["error"] = error
        st.markdown(assistant["content"])
        if assistant["tool_events"]:
            render_tool_events(assistant["tool_events"])
        if assistant.get("error"):
            st.error(assistant["error"])

    st.session_state["messages"] += [{"role": "user", "content": user_text}, assistant]

    # Transcript, same schema as chat.py.
    turn["ended_at"] = now_iso()
    st.session_state["turns"].append(turn)
    if not st.session_state["transcript_id"]:
        st.session_state["transcript_id"] = "_".join([
            safe_slug(version), "ui", safe_slug(provider_name), datetime.now().strftime("%Y%m%dT%H%M%S%f"),
        ])
    transcript = {
        "transcript_id": st.session_state["transcript_id"],
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": model or getattr(make_provider(provider_name), "default_model", None),
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_rounds,
        "created_at": st.session_state["turns"][0]["started_at"],
        "turns": st.session_state["turns"],
    }
    write_transcript(ROOT / "transcripts" / f"{st.session_state['transcript_id']}.transcript.json", transcript)
    st.rerun()
