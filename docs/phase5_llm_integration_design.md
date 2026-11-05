# Đặc tả Phase 5 — extraction, quality gate và hội thoại

Đặc tả chi tiết bổ sung cho [kiến trúc](SYSTEM_ARCHITECTURE.md); không là hướng dẫn khởi động thứ hai. API/web đã triển khai; **Gemini live NOT VERIFIED**, không có semantic/clinical evaluation đã được người duyệt. [Bản thiết kế trước hợp nhất](archive/integration/phase5_llm_integration_design.md) giữ JSON minh họa/thiết kế lịch sử. [Deployment](DEPLOYMENT_GUIDE.md) ghi môi trường và lệnh; [log](DEVELOPMENT_LOG.md#8-gemini-extraction-và-conversation-management) ghi lỗi thực tế.

## 1. Contract v2 và source of truth

Catalog đọc schema375/mapping587 và checksums Phase2, không CSV/model. [extraction_schema và validator](../src/agent/extraction.py) là định nghĩa executable, không duy trì một schema375 viết tay khác trong docs. Canonical schema ID `441709695f8b878e65d848309361838fa0367b6c031ed665a1472a9aee43b734` khác **file SHA256** schema; không dùng hai hash thay nhau.

| Trường | Hợp đồng |
|---|---|
| contract_version/schema_sha256 | 2 và đúng catalog schema ID |
| present/denied/uncertain | Danh sách mention chứa exact feature và evidence, không label bệnh/score |
| evidence | Ít nhất một span turn_id/start/end/text từ user turn thật |
| unmapped | phrase/state/reason/evidence; reason: ambiguous_mapping/outside_schema/excluded_feature/unclear_context |
| clarification | needed/reasons/target_features; reasons: ambiguous/uncertain/unmapped/insufficient/conflict; targets thuộc allowlist |

additionalProperties=false cho các object contract. Feature enum đủ375, clarification arrays unique; start≥0/end≥1. Python validator bắt buộc kể cả provider bỏ qua một số decoder constraints. Không xem JSON hợp lệ là hiểu đúng lời kể.

Wire mode hiện tại catalog_codes_v1 thay enum bằng f000…f374, gửi dictionary đầy đủ375 code/name; exact decode mentions/clarification targets về tên canonical **trước validator**. Unknown/malformed code hoặc catalog ordering khác fail closed. Không giảm/đổi ML allowlist, numeric bounds giữ nguyên. Intent/json-only explicit là nhánh khác; không tự fallback khi schema bị từ chối. Full live schema từng HTTP400 state explosion; wire mitigation chưa có accepted extraction thành công.

## 2. Evidence và semantic validation

Span offset là Unicode code points theo Python string, 0-based/end-exclusive trên nguyên văn; phải có `0 <= start < end <= len(turn.text)` và `turn.text[start:end] == evidence.text`. Không normalize/sửa chính tả trước kiểm. UTF16 client offsets không được đưa thẳng làm Python offset. Assistant text/quotes/knowledge questions/hypothetical/past-other-subject không phải present evidence.

Mỗi feature có một state sau context resolution; cùng state có thể hợp evidence, contradictory states không được âm thầm chọn present. Clarification false phải có reasons/targets rỗng; true có reason liên quan. LLM báo không cần hỏi không vượt qua Python gate. Unmapped phrase cũng phải có evidence; không đoán feature từ bệnh hoặc fuzzy-map tên.

Chỉ present đã xác thực nhận1; denied/uncertain/unmentioned nhận0 theo nghĩa **chưa ghi nhận hiện diện**. Sidecar giữ khác biệt này, evidence/conflicts/unmapped, không thêm cột vào model. Classifier frame null nếu chưa ready. Output model phải match375order/587classes/fitted pipeline identity.

## 3. Guard và cập nhật nhiều lượt

[conversation.py](../src/agent/conversation.py) kiểm input → urgent riêng → injection/scope → intent khi cần → extraction → validator → gate. Phân biệt câu urgent không đại từ với câu chỉ hỏi/trích dẫn triệu chứng; mixed-topic vẫn xét phần mô tả hiện tại. Đây là heuristic/provisional chưa được chứng nhận triage.

Active state tách theo chủ thể/đợt hiện tại. Correction/negation/resolution chỉ cập nhật khi có bằng chứng đủ rõ; triệu chứng đã hết không giữ present. Đổi self/mother/father/child không gộp vectors; subject khác hoặc thời điểm mơ hồ cần hỏi rõ. Short Có/Không chỉ gắn target câu hỏi đang mở, không gán feature/chủ thể/thời điểm mới theo suy đoán. Mọi thay đổi chặn gate làm mất hiệu lực vector/prediction trước.

Session in-memory: TTL900s, tối đa128sessions/12user turns,2clarification turns. Một câu hỏi/lượt, không hỏi lặp target đã giải quyết; hết budget thì abstain. Reset tạo phiên mới, không reset provider budget. UUID không là authentication hoặc persistence/multi-worker design.

## 4. Quality gate và Top 3

**Tên feature hợp lệ không tự cho phép prediction.** Policy [phase5b.json](../configs/phase5b.json) dùng min_present_features=2, review status provisional_pending_human_review, có thể cấu hình; không gọi đây là ngưỡng y khoa đã xác thực. Không dùng confidence threshold chưa được kiểm chứng.

| Trạng thái | Hành động | Top 3 |
|---|---|---|
| JSON/schema/evidence/context invalid | Reject hoặc abstain có lý do | Không |
| Conflict/uncertainty/unmapped/clarification chưa giải quyết | Hỏi rõ trong budget, sau đó abstain | Không |
| Thiếu thông tin hoặc không đúng phạm vi/chủ thể/thời điểm | Clarify/abstain/out_of_scope | Không |
| Dấu hiệu có thể khẩn cấp | Urgent redirect local, không chờ LLM/ML | Không |
| Provider lỗi/expiry/model chưa sẵn sàng | Controlled error, vô hiệu kết quả cũ | Không |
| Tất cả gate hợp lệ, extraction_ready | forward_ready gọi approved LR, kiểm model output | Có điều kiện |

Urgent messages cần human/clinical review; không suy độ nặng từ LR score. Không dùng LLM chọn bệnh hoặc sinh Top3. LR predict_proba trên đủ587 lớp, tie stable mapping order, Top3×100 không normalize, **Điểm mô hình (%)**, calibrated=false. LinearSVC margin/hard votes không phải probability. Template Python hiện tại chỉ diễn đạt nhãn/score thật; dịch nhãn chưa được duyệt thì giữ English label.

## 5. Evaluation và ground truth

[JSONL development](../data/evaluation/vietnamese_symptom_cases.jsonl) có30ca: origin ai_generated_fiction, split development, pending_human_review; không tự coi AI annotations là gold. Ca nhiều lượt, correction, subject, negation/uncertain, unmapped, urgent, knowledge và injection; giữ family/paraphrases cùng partition. Historical static check ghi22extraction cases/42spans,8guard cases không span; đây không là extraction accuracy live hoặc kiểm mới trong nhiệm vụ docs.

Trước đánh giá chính thức: người duyệt khóa annotation từng user turn, active feature/state/subject/time, conflict và action allow_prediction/clarify/abstain/urgent_redirect/invalid_extraction. Tách evaluation mới theo family; không đổi tag dev đã dùng sửa prompt thành holdout. Chốt rubric trên dev rồi khóa trước eval, không đặt score threshold tùy ý.

| Hạng mục | Đo và mẫu số |
|---|---|
| Extraction | Micro/Macro P/R/F1 theo present/denied/uncertain và tuple(feature,state); báo universe375/zero_division0 và supported subset |
| Negation/invalid | Đúng feature+state trên gold denials; FP denial→present; invalid outputs trên mọi response đầu tiên, kể cả bị reject |
| Gate sai cho phép | Top3 trong gold-block / tổng gold-block, tách insufficient/conflict/urgent/invalid |
| Gate chặn sai | Không predict trong gold-allow / tổng gold-allow; đọc cùng coverage để tránh always-abstain |
| Conversation | Action confusion matrix, clarification đúng target/giải quyết/budget; active state agreement, subject leakage và stale Top3 |
| Fidelity | Vector375 agreement, label/rank/scores đúng Python payload; unsupported statements; không gọi là diagnostic accuracy khi thiếu gold bệnh |
| Failure | Abstain/error/timeout/urgent counts và tỷ lệ trên tất cả attempts/turns/sessions, không loại lỗi khỏi mẫu số |

Mẫu số0 ghi NA, báo theo lượt và hội thoại, error/FN trên gold mentions không biến mất vì response invalid. Clinical generalization cần dữ liệu phù hợp độc lập, không thể suy từ synthetic ML scores hoặc vài câu demo.

## 6. Token, cost, latency và telemetry

Mỗi attempt: task/model/provider/version/run-case-turn ID giả danh/schema-prompt-policy identity, retry_count/outcome/status, latency monotonic, usage provider thực trả. Không log text sức khỏe thật, key/header/body hoặc detailed error trong public health. Diagnostic chỉ giữ bounded/redacted message; transport trace chỉ timings/byte counts/status.

- Token: input/output/cached/thought/total do provider báo, tránh cộng trùng counter thành phần; thiếu ghi unknown/null, complete=false. Local byte admission units không phải tokenizer/billed tokens.
- Cost: rate snapshot/provider/model/tier/ngày/đơn vị, category không trùng nhau; `sum(billable_category * rate/unit)` cùng phí khác nếu có. Không có billed cost thì unknown, không ghi0 vì timeout/usage rỗng. Có thể giữ reservation dù request thất bại.
- Latency: load lạnh, warm-up, network/generation, validator/mapper, LR inference và formatting tách riêng. TTFT chỉ khi có streaming event thật, non-streaming NA. Báo N,p50/p95,errors/retries,cold/warm/concurrency; không dùng một timing làm SLA.
- Session: tổng token/cost gồm retries và mọi calls, thời gian xử lý tách thời gian người dùng suy nghĩ. Provider quota khác local limits; restart không bảo đảm reset quota.

[Provider](../src/agent/provider.py) dùng Interactions REST, store=false/stream=false, system_instruction và response_format text/application-json/schema; parser completed steps/model_output/content/text. Model gemini-3.8-flash; key lấy environment. Base config và bounded web/CLI có limits khác nhau: dùng [deployment](DEPLOYMENT_GUIDE.md#4-gemini-và-chẩn-đoán-live) cho caps/zero-retry của web/diagnostic, không áp max_output_tokens8192/max_retries1 trong base config cho mọi caller.

## 7. Ranh giới xác minh

Offline mocks/regression đã kiểm guard/contract/state; real LR Windows/API đã PASS riêng. **Gemini live, serving acceptance của wire schema, semantic quality, account quota/Free Tier và human-reviewed gate vẫn NOT VERIFIED**. API/web hiện là nguyên mẫu localhost, không public/production hoặc clinical deployment. Không có live call, tuning, calibration, final-test replay hoặc model change trong nhiệm vụ hợp nhất tài liệu.
