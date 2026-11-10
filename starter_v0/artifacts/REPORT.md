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

Nguồn: `artifacts/version_log.csv` và `runs/*.json`. Provider: OpenRouter, model `openai/gpt-4o-mini`, `temperature=0`. Suite: `eval_base.json` (20 case: 14 single-turn + 6 multi-turn). Mỗi version đổi **một** giả thuyết.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | baseline (starter) | Đo điểm xuất phát; prompt starter cố ý bảo model đoán, gửi ngay, ép một bước | n/a | **0.70** (14/20) | `runs/v0_B_base_openrouter_20261110T102219270260.json` |
| v1 | `system_prompt.md` | 6 FAIL đều do 3 chỉ dẫn xấu của prompt → bỏ chúng, thêm rule: hỏi lại khi thiếu info, xác nhận `yes_no` trước khi gửi, không gọi tool cho câu ngoài phạm vi, không dùng `send` để trả lời | 0.70 | **0.90** (18/20) | `runs/v1_B_base_openrouter_20261110T102332240141.json` |
| v2 | `tools.yaml` | Description tool mơ hồ → viết lại (làm gì / khi nào dùng / khi nào không) + convention args (handle không `@`, tên→handle, `topic=news`, `timeframe`, `Top`/`Latest`, `confirmed=true`) | 0.90 | **0.95** (19/20) | `runs/v2_B_base_openrouter_20261110T102459203431.json` |
| v3 | `system_prompt.md` | R12: model coi thiếu nội dung là "missing info" nên hỏi `text` → bắt buộc mọi yêu cầu gửi/đăng đi qua `clarify yes_no` trước | 0.95 | **0.95** (19/20) | `runs/v3_B_base_openrouter_20261110T102548333658.json` |
| v4 | `system_prompt.md` | v3 sửa R12 nhưng M06 sai lại: rule "gọi mọi tool request cần" làm model gọi thừa `social_search` → giới hạn theo lượt user cuối, bỏ nguồn user đã bảo bỏ | 0.95 | **0.95** (19/20) | `runs/v4_B_base_openrouter_20261110T102635402983.json` |
| v4 (chạy lại lần 1) | không đổi | Đo nhiễu của cùng một bản v4 | 0.95 | **1.00** (20/20) | `runs/v4-rerun1_B_base_openrouter_20261110T102715301660.json` |
| v4 (chạy lại lần 2) | không đổi | Đo nhiễu của cùng một bản v4 | 0.95 | **1.00** (20/20) | `runs/v4-rerun2_B_base_openrouter_20261110T102746381257.json` |

Các chỉ số chi tiết:

| Version | case_accuracy | tool_routing | argument | multiturn |
|---|---:|---:|---:|---:|
| v0 | 0.70 | 0.75 | 0.70 | 1.00 |
| v1 | 0.90 | 0.95 | 0.90 | 0.83 |
| v2 | 0.95 | 1.00 | 0.95 | 1.00 |
| v3 | 0.95 | 0.95 | 0.95 | 0.83 |
| v4 | 0.95 | 1.00 | 0.95 | 1.00 |
| v4 rerun 1 / 2 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |

**Lưu ý về nhiễu (quan trọng khi đọc bảng).** Dù `temperature=0`, cùng một bản v4 (cùng `prompt_hash`, `tools_hash`) cho 19/20, 20/20, 20/20. Lần đầu sai R06 vì model điền `timeframe="tuần này"` (ngoài enum `day|week|month|year`) trong khi R06 đã PASS ở v0–v3 và không có gì liên quan bị đổi. Vì vậy biên độ nhiễu khoảng **1 case (5 điểm %)**: mức tăng từ v0→v1 (+4 case) và v1→v2 là tín hiệu thật, còn chênh lệch 1 case giữa v2/v3/v4 thì chưa đủ để kết luận version nào tốt hơn. Cần chạy nhiều lần mỗi version nếu muốn so sánh chặt hơn.

## B2. Failure Analysis

Lấy từ `results[*].result` của các run JSON. Cột "Failure Type" là `failure_type` của case, "observed" là `observed_mismatch`.

**Baseline v0 (6 case FAIL):**

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08_out_of_scope | out_of_scope (observed: unexpected_tool_call) | `send(text="Nguyên hàm của x^2 là x^3/3 + C…")` | Câu toán ngoài phạm vi; model tự giải rồi dùng `send` để "trả lời" | v1: rule ngoài phạm vi → không gọi tool, trả lời text; cấm dùng `send` để trả lời |
| R14_out_of_scope_coding | out_of_scope (unexpected_tool_call) | `send(text="Dưới đây là một hàm Python…")` | Y hệt R08: gửi code qua `send` | v1 (cùng rule với R08); v2 thêm "DO NOT USE to deliver an answer" vào description `send` |
| R10_missing_handle | missing_info (missing_tool_call + extra `timeline`) | `timeline(screenname="sama")` | Không nói tài khoản nào, model đoán Sam Altman đúng theo chỉ dẫn "pick a well-known account" | v1: bỏ chỉ dẫn đoán, thêm "ask instead of guessing" → `clarify text` |
| R11_missing_url | missing_info (missing_tool_call + extra `fetch`) | `fetch(url="https://example.com/article")` | "Bài này" không có link, model bịa URL | v1: như R10; v2 thêm vào description `fetch` "never invent a URL" |
| R12_confirm_before_send | wrong_boundary (missing_tool_call + extra `send`) | `send(text="Bản tin này")` | Gửi ngay không xác nhận, lại còn gửi đúng chuỗi "Bản tin này" | v1: rule xác nhận trước khi gửi (nhưng chưa đủ, xem bên dưới) |
| R13_parallel_web_and_tweets | wrong_tool (wrong_arg_value) | `lookup(query="AI news", timeframe="day")` + `social_search(query="AI")` | Routing đúng cả hai tool nhưng `query="AI news"` (thừa "news") và thiếu `topic="news"` | PASS từ v1 (v1 bỏ chỉ dẫn "Pick one tool … best judgment"). Chưa tách được nguyên nhân chính xác: v1 đổi nhiều dòng một lúc. v2 vẫn thêm convention `query` chỉ chứa chủ đề + `topic=news` vào description `lookup` để không phụ thuộc may rủi |

5/6 lỗi của v0 bắt nguồn trực tiếp từ chỉ dẫn xấu trong prompt starter (đoán thay vì hỏi → R10, R11; gửi không cần xác nhận → R12, R08, R14). R13 là lỗi giá trị arg (`query`, thiếu `topic`), nhiều khả năng liên quan chỉ dẫn "ép một bước, tự điền args theo phán đoán" nhưng log không chứng minh được. Multi-turn của v0 đạt 100%, tức việc mang ngữ cảnh qua nhiều lượt không phải điểm yếu của model này.

**Lỗi còn lại / phát sinh ở các version sau:**

| Case ID | Version | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|---|
| R12_confirm_before_send | v1, v2 | wrong_boundary → wrong_arg_value (`response_type`: expected `yes_no`, got `text`) | `clarify(question="Bạn có thể cung cấp nội dung cụ thể…", response_type="text")` | Đã chịu hỏi lại, nhưng hỏi xin nội dung (`text`) thay vì xin xác nhận (`yes_no`) vì request không kèm nội dung | v3: mọi yêu cầu gửi/đăng đi qua `clarify yes_no` trước, kể cả khi chưa có nội dung |
| M06_switch_tool | v1, v3 | wrong_tool (extra_tool_call) | `lookup(query="OpenAI", topic="news")` + `social_search(query="OpenAI")` | User đã bảo "Bỏ Twitter" nhưng model vẫn gọi thêm `social_search`. Nghi do rule "gọi mọi tool request cần" và ngữ cảnh lượt 1 nhắc Twitter | v4: rule chỉ xét lượt cuối, bỏ nguồn user đã bảo bỏ. PASS ở v4 và cả 2 lần chạy lại |
| R06_timeframe_arg | v4 (lần đầu) | wrong_arg_value | `lookup(query="công nghệ", topic="news", timeframe="tuần này")` | Model điền thẳng cụm tiếng Việt vào enum `timeframe`. **Nhiễu**: không tái hiện ở 2 lần chạy lại cùng artifact | Không sửa. Nếu lặp lại thì thêm ví dụ `tuần này → week` vào prompt |

**Cần xem tay (chấm tự động chưa đủ).**
- R12: eval đòi `clarify yes_no`. Cách này đúng với ràng buộc "không tự gửi", nhưng trong thực tế hỏi xin nội dung trước rồi mới xác nhận cũng hợp lý. Chọn `yes_no`-trước là quyết định theo eval, chưa chắc là UX tốt nhất.
- R08, R09, R14 chỉ kiểm tra "không gọi tool". Eval không đọc `actual_text` nên chưa biết model từ chối/định hướng đúng hay chỉ im lặng.
- `tool_results` (dữ liệu thật từ Tavily/RapidAPI) không được chấm: chỉ có đúng tool và đúng args là được tính.

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
