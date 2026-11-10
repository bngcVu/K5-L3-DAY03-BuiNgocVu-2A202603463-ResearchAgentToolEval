# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team:
- Members:
- Provider/model:

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

> 1–2 câu mô tả agent dùng để làm gì (cho team khác hiểu nhanh).

Ví dụ: "Research agent: tìm tin theo từ khóa / theo tài khoản, đọc URL, tổng hợp thành digest, và gửi lên Telegram khi được xác nhận."

**Link dùng thử (deploy):**

> Dán link public để team khác mở thử ngay. Cách deploy nhanh bằng Cloudflare Tunnel xem README. Nếu deploy Vercel/Streamlit Cloud thì dán link đó.
>
> URL: 

## A2. Tool agent có

> Liệt kê các tool agent đang dùng (gồm tool mới nhóm tự thêm). Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin | không |
|  |  |  |
|  |  |  |

## A3. Câu hỏi mẫu để thử

> 3–5 câu hỏi/yêu cầu mẫu để team khác tự thử agent ngay.

1.
2.
3.

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Nguồn: `artifacts/version_log.csv` và `runs/*.json`. Provider: OpenRouter, model `openai/gpt-4o-mini`, `temperature=0`. Suite: `eval_base.json` (20 case: 14 single-turn + 6 multi-turn).

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline (starter) | Đo điểm xuất phát; prompt starter cố ý bảo model đoán, gửi ngay, ép một bước | n/a | **0.70** (14/20) | `runs/v0_B_base_openrouter_20261110T102219270260.json` |
| v1 |  |  |  |  |  |
| v2 |  |  |  |  |  |
| v3 |  |  |  |  |  |

Chỉ số chi tiết v0: case_accuracy 0.70, tool_routing 0.75, argument 0.70, multiturn 1.00.

## B2. Failure Analysis

Lấy từ `results[*].result` của run v0. "Failure Type" là `failure_type` của case, "observed" là `observed_mismatch`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08_out_of_scope | out_of_scope (unexpected_tool_call) | `send(text="Nguyên hàm của x^2 là x^3/3 + C…")` | Câu toán ngoài phạm vi; model tự giải rồi dùng `send` để "trả lời" | Chưa sửa (baseline) |
| R14_out_of_scope_coding | out_of_scope (unexpected_tool_call) | `send(text="Dưới đây là một hàm Python…")` | Giống R08: gửi code qua `send` | Chưa sửa (baseline) |
| R10_missing_handle | missing_info (missing_tool_call + extra `timeline`) | `timeline(screenname="sama")` | Không nói tài khoản nào, model đoán Sam Altman, khớp chỉ dẫn "pick a well-known account" của prompt starter | Chưa sửa (baseline) |
| R11_missing_url | missing_info (missing_tool_call + extra `fetch`) | `fetch(url="https://example.com/article")` | "Bài này" không có link, model bịa URL | Chưa sửa (baseline) |
| R12_confirm_before_send | wrong_boundary (missing_tool_call + extra `send`) | `send(text="Bản tin này")` | Gửi ngay, không xác nhận | Chưa sửa (baseline) |
| R13_parallel_web_and_tweets | wrong_tool (wrong_arg_value) | `lookup(query="AI news", timeframe="day")` + `social_search(query="AI")` | Routing đúng cả hai tool nhưng `query="AI news"` (thừa "news") và thiếu `topic="news"` | Chưa sửa (baseline) |

Nhận xét: 5/6 lỗi khớp trực tiếp với chỉ dẫn xấu trong prompt starter (đoán thay vì hỏi → R10, R11; gửi không cần xác nhận → R12, R08, R14). R13 là lỗi giá trị arg. Multi-turn đạt 100%, tức việc mang ngữ cảnh qua nhiều lượt không phải điểm yếu của model này.

## B3. Team Eval Cases

List the 10 cases added to `data/eval_group.json` (5 single turn + 5 multi turn).

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
|  |  |  |  |

## B4. Live Chat Evidence

Use `transcripts/*.transcript.json`.

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Bonus Evidence

Only fill if your team did bonus.

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| send (Telegram) |  |  |  |
| arXiv/company policy |  |  |  |
| UI |  |  |  |
| Tool unit tests (`tests/`) | `pytest` output |  |  |

Tool unit tests: số test đã viết, số bug tìm được trong tool có sẵn (nếu có), và một ví dụ lỗi mà unit test bắt được nhưng eval không bắt được.

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
- Which fixes belonged in `tools.yaml`?
- Which failure needed manual review instead of automatic grading?
- What would you improve next?

## B7. Small Local Model Challenge (bonus)

Only fill if your team did the local model challenge.

| Version | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
|---|---|---|---|---|---|---|---|
| v3 | (cloud) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v4-local |  |  |  |  |  |  |  |
| v5-local |  |  |  |  |  |  |  |

Lỗi đặc thù của model nhỏ (đếm từ run JSON):

| Failure Pattern | Count | Example Case | Fix Tried | Helped? |
|---|---|---|---|---|
| wrong / hallucinated tool |  |  |  |  |
| invalid JSON args (`_invalid_json_arguments`) |  |  |  |  |
| no tool call / answered directly |  |  |  |  |
| missed `clarify` |  |  |  |  |
| repeated / unnecessary calls |  |  |  |  |

- Cái gì giúp model nhỏ gọi tool đúng hơn nhất? Bằng chứng?
- Bản prompt tối ưu cho local chạy trên model cloud thì sao?
- Khi nào nhóm sẽ chọn model local thay vì cloud cho agent này?
