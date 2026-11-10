# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
>
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ dựa trên log thật (`version_log.csv` + `runs/*.json`).

## Team

- Team: Bùi Ngọc Vũ
- Members: Bùi Ngọc Vũ
- Provider/model: OpenRouter, model `openai/gpt-4o-mini`, `temperature=0`

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent này thực hiện các bước: tìm tin tức / chủ đề trên web, tìm các bài đăng xã hội trên X/Twitter, đọc URL đầy đủ khi có link, loại trùng item, tổng hợp thành digest markdown, và chỉ gửi lên kênh khi người dùng xác nhận rõ ràng. Nói cách khác, agent này tập trung vào workflow nghiên cứu thị giác: tìm → chọn → đọc → tổng hợp → báo cáo/ gửi.

**Link dùng thử (deploy):**

> Chưa có link public được deploy trong workspace hiện tại. Nếu cần demo, có thể chạy local bằng Streamlit / chat UI trong project.
>
> URL: chưa có

## A2. Tool agent có

| Tên tool      | Làm được gì                                                 | Tool mới nhóm thêm? |
| ------------- | ----------------------------------------------------------- | ------------------- |
| clarify       | hỏi lại khi thiếu thông tin hoặc cần xác nhận trước khi gửi | không               |
| timeline      | lấy bài đăng gần đây của một tài khoản X/Twitter cụ thể     | không               |
| social_search | tìm tweet/posts theo từ khóa hoặc chủ đề                    | không               |
| lookup        | tìm tin tức / thông tin web theo topic + timeframe          | không               |
| fetch         | đọc nội dung đầy đủ của một URL đã có                       | không               |
| dedupe        | loại bỏ item trùng theo URL hoặc title                      | có                  |
| format        | chuyển các item thu thập được thành digest markdown         | không               |
| send          | gửi lên Telegram chỉ khi `confirmed=true`                   | không               |
| policy        | tra cứu chính sách nội bộ của công ty                       | không               |
| papers        | tìm paper trên arXiv theo từ khóa                           | không               |
| paper_text    | tải và trích text từ PDF arXiv                              | không               |

## A3. Câu hỏi mẫu để thử

1. "Hôm nay có những tin AI nào đáng chú ý? Hãy tổng hợp 5 item và trình bày theo dạng bản tin ngắn."
2. "Cho tôi 5 tweet mới nhất của @sama và tóm tắt xu hướng trong đó."
3. "Tìm các bài về OpenAI trong 1 tuần qua, bỏ trùng và cho tôi digest ngắn."
4. "Bài viết này có URL không? Nếu có, đọc và tóm tắt cho tôi."
5. "Đưa cho tôi một bản tin AI tiếng Việt gồm 3 phần: tin nóng, tin xã hội, và tóm tắt cuối ngày."

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Nguồn: `starter_v0/artifacts/version_log.csv`, `starter_v0/runs/*.json`.

| Version   | Changed Artifact                                                        | Hypothesis                                                                                                                                          |                                              Metric Before |                                                         Metric After | Run File                                                                                                                                                                     |
| --------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------: | -------------------------------------------------------------------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v0        | baseline (starter prompt + tools)                                       | Đo điểm xuất phát; prompt starter cố ý khuyến khích đoán, gửi ngay, ép một bước                                                                     |                                                        n/a |                                                         0.70 (14/20) | `runs/v0_B_base_openrouter_20261110T102219270260.json`                                                                                                                       |
| v1        | `system_prompt.md`                                                      | Bỏ các mệnh lệnh xấu, bắt buộc `clarify` khi thiếu thông tin và không gửi mà không xác nhận                                                         |                                               0.70 (14/20) |                                                         0.85 (17/20) | `runs/v1_B_base_openrouter_20261110T111517268942.json`                                                                                                                       |
| v1-dedupe | `tools.yaml` + tool mới `dedupe`                                        | Thêm tool mới nhưng không làm lệch routing cũ; kiểm tra tính không làm tăng lỗi mới                                                                 |                                               0.85 (17/20) |                                                         0.85 (17/20) | `runs/v1-dedupe_B_base_openrouter_20261110T112046375242.json`                                                                                                                |
| v2        | `tools.yaml`                                                            | Viết lại description, quy tắc routing & arg conventions rõ hơn, đặc biệt `send` chỉ khi `confirmed=true` và `topic/timeframe/search_type` chuẩn hóa |                                               0.85 (17/20) |                                                         1.00 (20/20) | `runs/v2_B_base_openrouter_20261110T112601133398.json`                                                                                                                       |
| v2-rerun1 | không đổi                                                               | Kiểm tra độ ổn định / không phải may mắn một lần                                                                                                    |                                               1.00 (20/20) |                                                         1.00 (20/20) | `runs/v2-rerun1_B_base_openrouter_20261110T112803492832.json`                                                                                                                |
| v2-rerun2 | không đổi                                                               | Kiểm tra độ ổn định / không phải may mắn một lần                                                                                                    |                                               1.00 (20/20) |                                                         1.00 (20/20) | `runs/v2-rerun2_B_base_openrouter_20261110T112901298083.json`                                                                                                                |
| v0        | baseline (starter)                                                      | Đo điểm xuất phát; prompt starter cố ý bảo model đoán, gửi ngay, ép một bước                                                                        |                                                        n/a |                                                     **0.70** (14/20) | `runs/v0_B_base_openrouter_20261110T102219270260.json`                                                                                                                       |
| v1        | `system_prompt.md`                                                      | Bỏ chỉ dẫn đoán/gửi ngay/ép một bước; thêm routing và clarify                                                                                       |                                               0.70 (14/20) |                                                     **0.85 (17/20)** | `runs/v1_B_base_openrouter_20261110T111517268942.json`                                                                                                                       |
| v2        | `tools.yaml`                                                            | Mô tả rõ tool boundary và args để xử lý lỗi còn lại từ v1                                                                                           |                                               0.85 (17/20) |                                                     **1.00 (20/20)** | `runs/v2_B_base_openrouter_20261110T112601133398.json`                                                                                                                       |
| v3        | `system_prompt.md` + `eval_group.json` + comparator trong `run_eval.py` | Bổ sung routing cụ thể cho policy, yêu cầu kết hợp và quy tắc không gọi tool lặp sau refinement                                                     | Lượt trước: base 1.00 (20/20), group/extension 0.80 (8/10) | **Base: 1.00 (20/20); group: 1.00 (10/10); extension: 1.00 (10/10)** | `runs/v3_B_base_openrouter_20261110T141234753297.json`; `runs/v3_B_group_openrouter_20261110T141117853106.json`; `runs/v3_B_extension_openrouter_20261110T141142406985.json` |

Chỉ số chi tiết v0: `case_accuracy=0.70`, `tool_routing_accuracy=0.75`, `argument_accuracy=0.70`, `multiturn_accuracy=1.00`.

Kết luận: hiệu suất tăng rõ rệt khi chỉnh rule trong prompt + description tool. Điểm mấu chốt không nằm ở model mạnh yếu mà nằm ở việc định nghĩa rõ ranh giới tool và cách hỏi khi thiếu thông tin.

## B2. Failure Analysis

Lấy từ `results[*].result` của run v0. Đây là các lỗi căn bản vốn xuất hiện do prompt starter có chỉ dẫn xấu.

| Case ID                     | Failure Type                                        | Actual Tool Calls                                                        | What Failed                                                                                                        | Fix                                                                            |
| --------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| R08_out_of_scope            | out_of_scope (unexpected_tool_call)                 | `send(text="Nguyên hàm của x^2 là x^3/3 + C…")`                          | Model tự giải toán ngoài phạm vi và dùng `send` để “gửi” trả lời                                                   | Không còn đúng với prompt tích cực; phải cấm gửi khi không phải research task  |
| R14_out_of_scope_coding     | out_of_scope (unexpected_tool_call)                 | `send(text="Dưới đây là một hàm Python…")`                               | Giống R08: gửi code trực tiếp thay vì trả lời bình thường hoặc hỏi rõ                                              | Cần ràng buộc tool boundary: `send` chỉ dùng cho kênh Telegram đã xác nhận     |
| R10_missing_handle          | missing_info (missing_tool_call + extra `timeline`) | `timeline(screenname="sama")`                                            | Không có handle / không có tài khoản nào được nêu rõ; model đoán thay vì hỏi                                       | Dùng `clarify` để hỏi tài khoản hoặc handle                                    |
| R11_missing_url             | missing_info (missing_tool_call + extra `fetch`)    | `fetch(url="https://example.com/article")`                               | Không có URL; model bịa URL và giả định “bài này”                                                                  | Bắt buộc phải có URL thật; nếu thiếu thì hỏi lại                               |
| R12_confirm_before_send     | wrong_boundary (missing_tool_call + extra `send`)   | `send(text="Bản tin này")`                                               | Gửi ngay mà không xác nhận từ user                                                                                 | Dùng `clarify` với `response_type=yes_no`, rồi mới `send` với `confirmed=true` |
| R13_parallel_web_and_tweets | wrong_tool (wrong_arg_value)                        | `lookup(query="AI news", timeframe="day")` + `social_search(query="AI")` | Routing đúng cả hai tool nhưng `query` sai dạng, thiếu `topic="news"`, thiếu chốt về khi nào dùng social vs lookup | Chuẩn hóa description và arg convention trong `tools.yaml`                     |

Nhận xét: 5/6 lỗi tương ứng trực tiếp với chỉ dẫn xấu trong prompt starter: đoán thay vì hỏi, gửi không xác nhận, ép một bước. Vấn đề `R13` cho thấy model còn lẫn lộn giữa dust search và web search nếu không có quy tắc rõ ràng.

## B3. Team Eval Cases

File `starter_v0/data/eval_group.json` hiện tại đang rỗng. Tức là nhóm chưa thêm các case do mình tự viết vào dataset này.

| Case ID                                   | What It Tests                                    | Expected Tool/Behavior                          | Result                                              |
| ----------------------------------------- | ------------------------------------------------ | ----------------------------------------------- | --------------------------------------------------- |
| (chưa có)                                 | (chưa có)                                        | (chưa có)                                       | file rỗng                                           |
| G01_internal_policy_privacy               | Policy nội bộ, không tra web                     | `policy(policy_area=data_privacy)`              | PASS                                                |
| G02_find_academic_papers                  | Paper mới nhất, giữ số lượng/sort                | `papers(max_results=3, sort_by=submittedDate)`  | PASS                                                |
| G03_read_arxiv_paper                      | Đọc paper bằng arXiv ID                          | `paper_text(arxiv_url=1706.03762, max_pages=2)` | PASS                                                |
| G04_non_arxiv_url                         | URL không phải arXiv                             | `fetch(url=...)`                                | PASS                                                |
| G05_dedupe_user_supplied_items            | Bỏ trùng danh sách có sẵn                        | `dedupe(items=..., by=url)`                     | PASS sau khi sửa comparator eval hỗ trợ list object |
| G06_multiturn_policy_area                 | Giữ policy context, chọn area ở lượt mới         | `policy(policy_area=source_citation)`           | PASS                                                |
| G07_multiturn_paper_limit_correction      | Giữ chủ đề paper, sửa số lượng/sort              | `papers(max_results=2, sort_by=submittedDate)`  | PASS                                                |
| G08_multiturn_read_paper_id               | Mang arXiv ID qua lượt                           | `paper_text(arxiv_url=1706.03762, max_pages=3)` | PASS                                                |
| G09_multiturn_switch_to_internal_policy   | Chuyển từ web sang policy, không gọi lookup thừa | `policy(policy_area=source_citation)`           | PASS                                                |
| G10_multiturn_arxiv_read_limit_correction | Giữ ID, cập nhật giới hạn trang                  | `paper_text(arxiv_url=1706.03762, max_pages=1)` | PASS                                                |

Extension eval sau khi sửa prompt: **10/10**. Các lỗi E01 (policy area quá rộng) và E06 (bỏ sót một tool trong request kết hợp) đều đã pass.

## B4. Live Chat Evidence

Các transcript UI được lưu trong `starter_v0/transcripts/*.transcript.json` và có nhiều phiên bản `v0`, `v1`, `v2` tương ứng với từng vòng chạy. Trong bản report hiện tại, dữ liệu live chat được lưu dưới dạng transcript JSON chứ chưa được tách thành bảng ngắn trong file này.

| Turn | User Request                 | Tool Calls                           | Version Evidence                | Outcome                                           |
| ---- | ---------------------------- | ------------------------------------ | ------------------------------- | ------------------------------------------------- |
| 1    | sample research request/demo | lookup / timeline / format / clarify | `transcripts/*.transcript.json` | agent phản hồi đúng hướng khi tool declaration rõ |
| 2    | confirm-before-send          | clarify -> send                      | `transcripts/*.transcript.json` | đúng khi `confirmed=true`                         |
| 3    | missing account/URL          | clarify                              | `transcripts/*.transcript.json` | model hỏi lại thay vì đoán                        |

## B5. Bonus Evidence

| Bonus                      | Evidence File                               | What Worked                                                                     | Risk / Guardrail                                           |
| -------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| send (Telegram)            | chưa có run/ transcript chứng minh          | có boundary hợp lệ trong `tools.yaml`                                           | vẫn cần xác nhận `confirmed=true` trước khi gửi            |
| arXiv / company policy     | chưa triển khai đầy đủ                      | code đã có các tool tương ứng                                                   | cần đảm bảo đúng scope để tránh misuse                     |
| UI                         | chưa có link public deploy                  | project có code UI, nhưng chưa được chạy demo thực tế                           | cần kiểm tra rõ ràng trước khi nộp                         |
| Tool unit tests (`tests/`) | chưa có evidence đầy đủ trong repo hiện tại | project có test scaffold                                                        | cần run `pytest` để xác nhận xanh                          |
| send (Telegram)            |                                             |                                                                                 |                                                            |
| arXiv/company policy       |                                             |                                                                                 |                                                            |
| UI                         |                                             |                                                                                 |                                                            |
| Tool unit tests (`tests/`) | `pytest -q`: 103 passed, 0 skipped          | Hoàn tất test challenge cho tool; eval comparator được kiểm tra với list object | Live eval dùng API cần credentials; unit test chạy offline |

Tool unit tests: số test đã viết, số bug tìm được trong tool có sẵn (nếu có), và một ví dụ lỗi mà unit test bắt được nhưng eval không bắt được.

## B6. Reflection

- Which fixes belonged in `system_prompt.md`?
  - Cấm đoán thay vì hỏi.
  - Cấm gửi không xác nhận.
  - Cấm tool call ngoài scope.
  - Quản lý `clarify` khi thiếu thông tin.

- Which fixes belonged in `tools.yaml`?
  - Mô tả rõ `when to use / when not to use` cho từng tool.
  - Quy ước arg: `handle` không có `@`, `topic=news`, `timeframe` enum, `search_type=Top|Latest`.
  - Rõ ràng `send` phải cần `confirmed=true`.
  - `dedupe` được mô tả là tool bổ trợ, không phải tool tìm kiếm.

- Which failure needed manual review instead of automatic grading?
  - Những trường hợp thiếu URL, thiếu handle, hoặc user chưa xác nhận: cần có câu hỏi lại. Nếu không có câu hỏi lại thì model suy đoán và sai.
  - Những case liên quan đến “bài này” hoặc “tin tức ngày hôm nay” khi không có data đầu vào cần manual review để quyết định có clarify hay không.

- What would you improve next?
  - Thêm `eval_group.json` thật với 10 case để cover thêm edge cases.
  - Cài đặt UI demo rõ ràng và ghi transcript dài hơn.
  - Chạy lại `pytest` để đảm bảo tính nhất quán giữa tool declaration và code.
  - Tạo case về out-of-scope, missing info, multi-turn, và confirm-before-send như bộ eval hữu ích cho model.

## B7. Small Local Model Challenge (bonus)

Hiện tại challenge này chưa thực hiện trong repo hiện có. Vì thế không có dữ liệu run local model để so sánh.

| Version  | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
| -------- | ---------------- | ------------ | ------------: | -----------: | -------: | --------: | -------- |
| v3       | n/a              | n/a          |           n/a |          n/a |      n/a |       n/a | n/a      |
| v3-local | n/a              | n/a          |           n/a |          n/a |      n/a |       n/a | n/a      |

---

## Kết luận ngắn

Vòng lặp cải thiện thực sự của lab này không nằm ở việc “mở rộng tool” mà ở việc sửa các rule đóng khung hành vi của model. Trong baseline, lỗi tập trung vào 3 điểm chính: (1) đoán thay vì hỏi, (2) gửi mà không xác nhận, (3) không phân biệt rõ scope giữa web search, social search và tool read URL. Khi `system_prompt.md` và `tools.yaml` được viết lại rõ ràng, agent nhanh chóng chuyển từ 0.70 lên 1.00 trên suite base. Đây là bằng chứng trực tiếp rằng prompt/tool contract là yếu tố quyết định chất lượng của research agent, không chỉ là model cho sẵn.
