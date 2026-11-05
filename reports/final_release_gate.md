# Final release gate — 2026-11-04

**Cập nhật2026-11-05:** hai blocker notebook06 closeout và packaging supplements đã được sửa/targetedverify; xem [handover blocker fix](handover_blocker_fix.md). Nội dung dưới giữ nguyên như lịch sử gate ngày04, không phải trạng thái mới. Production vẫn135active; chưa tạoZIP hoặc xác minhDrive.

**Kết luận: BLOCKER đối với bàn giao/đóng gói toàn dự án. Local offline demo với 135/375 feature: RELEASE_READY trong phạm vi synthetic đã kiểm. Không kích hoạt alias mới, không tạo ZIP.**

## Regression triage

[Bảng đủ 34 test IDs](release_final_gate/regression_triage.csv) và [JSON bằng chứng](release_final_gate/regression_triage.json) ghi phạm vi, exception/source frames, vị trí từng traceback trong hai log, nguyên nhân, tác động website và phân loại. Cả 34 có normalized exception/source frames **và full traceback context tương đương** trước/sau rollback. Chỉ chuẩn hóa số thư mục pytest và memory address, không bỏ qua khác biệt loại exception. Hai log gốc và activation manifest được giữ nguyên.

Phân loại lịch sử: **20 ENVIRONMENT / 11 OPTIONAL / 3 BLOCKER**. Đây là nhãn theo phạm vi release, không phải cách đổi test FAIL thành PASS.

| Nhóm | Số | Bằng chứng/root cause | Tác động |
|---|---:|---|---|
| nbformat | 15 | 13 ERROR Phase2 và 2 FAIL bootstrap; import `scripts/build_notebooks.py:8` không có nbformat trên Python3.11 | Generator/test environment; không thuộc website. Không cài vào production. |
| Windows multiprocessing | 1 | RandomForest synthetic training fixture: `_winapi.CreateFile`/named pipe WinError5 | Không liên quan inference LR đã fit; không retrain để chứng minh. |
| google.colab | 4 | Harness Windows exec cell Colab trong smoke notebook nhưng không mock module | Không thuộc website Windows; Colab thật NOT VERIFIED trong vòng này. |
| Packaging count | 1 | Payload thực47, assertion cũ45; make_publication hiện được kiểm đủ47 tên/hash, không dataset/checkpoint | Assertion không theo inventory hiện hành; không sửa expected. |
| PowerShell staging fixture | 3 | `editing_project` không copy `scripts/package_handover.py` mà helper hiện gọi; subprocess exit2 | Incomplete test fixture; actual file có trong local code và packaging allowlist. Không publish Drive. |
| Notebook06 prerequisite harness | 6 | Harness exec tiếp notebook sau fail-closed preflight; RuntimeError thay vì tới assertion tổng hợp mong đợi | OPTIONAL cho website; không chứng minh Colab notebook hoàn chỉnh PASS. |
| Notebook03 teaching workflow | 1 | Test exec cả cell tuning đang được owner chủ động bật, trên fixture7feature/ít lớp; verify chặn kích thước trước tuning | Không reset switch, sửa notebook03 hoặc đụng kết quả. |
| Notebook06 gate/closeout | 3 | Gate True + authorization trong source; stub evaluate chặn execution; test closeout không tìm thấy cell bảo vệ mong đợi | BLOCKER bàn giao notebook, không phải lỗi LR/website. |

Default notebook06 đã được đưa về `False`, authorization rỗng; [receipt](release_final_gate/notebook06_gate_freeze.json) xác nhận **chỉ source cell8 đổi, outputs/execution counts nguyên vẹn**. Không chạy notebook. Follow-up test cũ vẫn FAIL ở assertion thiếu `read_completed(completed_folder)`; source chưa có closeout viewer đúng contract. Không thêm string giả, sửa test hoặc chạy lại evaluation để ép PASS.

Helper `final_evaluation.evaluate` vẫn fail closed khi authorization rỗng hoặc preflight báo slot đã started/completed. Các trường hợp này được kiểm riêng bằng sentinel synthetic, không mở model/test payload. Điều này không thay thế chứng minh notebook06 closeout end-to-end.

## Runtime release-critical

[Actual checkpoint + HTTP evidence](release_final_gate/real_runtime_smoke.json): Windows CPython3.13.17, sklearn1.6.1, NumPy2.1.3, SciPy1.16.3, joblib1.6.0. Production loader giữ toàn bộ checksum, nguồn, schema/mapping và runtime allowlist. LR tuned C=2, experiment `tuning-v1-9c4dd013abbba14a`, selected identity `tuned-v1-b8a5602679b3dc5c`.

- Pipeline SHA `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`; input375, retained318, class order587.
- Reference Colab SHA `5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc`; 4696 probabilities, 8 labels và Top3 đều khớp; max abs difference `2.168404344971009e-19`, rtol1e-10/atol1e-12.
- FastAPI TestClient và **Uvicorn TCP localhost thực**: health200, predict200. Dùng port trống hệ điều hành cấp, không chiếm/kill server8000 đang chạy của owner.
- Offline chat, batch answers, user-requested preview, reset, denial, uncertainty, ambiguous/unmapped, urgent, hypothetical và other-subject no-Top3 checks PASS. Assert trực tiếp scores API bằng fitted `predict_proba()*100`, không renormalize Top3.
- Fit/locked-test/protected-write guards0; outbound socket/LLM attempts0. Giữ nguyên source của extractor, validator, policy, prediction loader và fitted model. Credential scan chỉ có phạm vi allowlist/pattern, không phải bằng chứng absence tuyệt đối mọi secret trên toàn ổ đĩa.

## Quyết định alias cuối

[720 ca ngữ cảnh mở rộng](release_final_gate/candidate_contexts.json): **432 PASS, 288 FAIL** trên dictionary fixture chứa127feature/144alias. Mỗi alias có5ca: fiction, third-person, friend, conditional, knowledge question. Tất cả144alias ghi nhận state sai trong fiction “Nhân vật trong truyện bị…” và third-person “Anh ấy bị…”. Có127feature bị ảnh hưởng. Gate thường chặn inference vì unmapped, nhưng state sai vẫn không đạt activation condition.

Đây là lỗi cơ học trên các câu đã định trước, không phải tỷ lệ false positive lâm sàng. `delusions or hallucinations` vẫn bị loại. Không nới guard/validator, không sửa alias active và **không có lần activation production mới**. Chốt **135active/240pending, 0feature/0alias mới**. SHA dictionary giữ `036d756fb202612122a31e8a041e60e98a33cc632a7caa41df25ccfe2689d527`.

86 ca semantic cũ PASS trên dictionary thật không đổi. Qualification/regression chọn lọc: **2471PASS/1deprecation warning**. Release checks mới8PASS; follow-up notebook closeout cũ1FAIL. Full suite không chạy lại và **không được gọi là PASS**: bằng chứng full-suite gần nhất vẫn3433PASS/21FAIL/13ERROR/5SKIP,4subtestsPASS. Các suite chọn lọc không fit model; real HTTP dùng checkpoint đã fit. `.venv-web` không có pytest và có hạn chế temp ACL; dùng interpreter test3.11 có sẵn cho fixtures/static tests, không cài hoặc sửa environment production.

## Packaging/freeze và giới hạn bàn giao

[Packaging artifact manifest](release_final_gate/packaging_artifact_manifest.json) chốt SHA/bytes từng source/config, toàn code allowlist,7file deployment thật và supplemental test/evidence files. Data-side list lấy từ pinned handover requirements; **không hash/open locked test hoặc tự xác minh Drive**. Giữ nguyên canonical root `/content/drive/MyDrive/ML_Projects/disease-prediction-ml`. Không tạo ZIP, staging/publish mới hoặc đổi layout.

**Blocker đóng gói thứ hai:** tool `code_files()` hiện bỏ sót packet terminology và JSONL/manifest/snapshot mà các tests được ship phụ thuộc. Manifest release liệt kê chính xác required supplements; không được coi code ZIP tạo bởi allowlist hiện tại là test-complete. Không thay packaging tool trong nhiệm vụ kiểm toán này.

Chấp nhận cho local demo: 135active, rule matching hạn chế với câu kể chuyện/chủ thể phức tạp; unmapped/uncertainty phải chặn Top3; không claim clinical validation, calibrated probability hoặc extraction375/375. Môi trường ML vẫn phải đúng allowlist, giữ7artifact đúng hash. Không dùng các ca qualification để sửa ML, chọn model hay suy ra accuracy thực tế. Không có LLM live qualification trong vòng này.

**STOP:** giữ bản135active, không thử lại activation; không đóng gói toàn dự án khi notebook06 closeout và required packaging supplements còn chưa đạt contract.
