# Handover blocker fix — 2026-11-05

**Hai blocker được đóng. Code handover READY; chưa tạo ZIP hoặc xác minh data ZIP/Drive. Production giữ135/375active.** Báo cáo final release gate ngày04 là lịch sử; các CSV/JSON/log evidence gốc không bị ghi đè.

Notebook06 là closeout viewer thực sự: không import/call `evaluate`, không deserialize/predict/fit hoặc copy reference lên Drive. GateFalse/authorizationrỗng; nếu tự bật gate thì dừng ngay. Sau setup và preflight hợp lệ, namespace hoàn tất được kiểm đúng manifestSHA `f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a`, rồi gọi `read_completed(completed_folder)` để kiểm mọi completed artifact trước hiển thị. Thiếu bundle không tự đánh giá; checksum sai bị chặn. STARTED/PARTIAL/ORPHANED không được resume. Các cell chẩn đoán cũ được giữ dưới dạng comment để không còn thực thi; toàn bộ executed outputs/counts giữ nguyên, không thay scientific metrics.

`configs/handover_code_supplements.json` chốt đúng22file đã duyệt,3385695bytes (~3.39MB), maxfile603400bytes. Pin SHA của policy trong `package_handover.py`; từng file có size/SHA, portable relative path và giới hạn loại/vị trí/kích thước. `code_files()` không glob thêm CSV/dataset/checkpoint. Dừng nếu policy hoặc evidence thay đổi. Secret/symlink/reparse checks hiện có giữ nguyên. Cả22file khớp nguyên byte inventory trước sửa; không thêm fixture phụ thuộc ngoài danh sách này.

Test cũ cấm mọiCSV/reportkhôngMarkdown xung đột với phê duyệt22fixture. Đã ghi rõ xung đột trước thay đổi; assertions vẫn cấm theo mặc định, chỉ miễn đúng policy đã pin và kiểm checksum. Không thay count45→47: kiểm tên/hash/bytes theo runtime publication manifest, bao gồm descriptor của runtime.json. Test bổ sung chứng minh rawCSV, checkpoint, .env và report chưa duyệt vẫn bị loại; tamper policy/file làm packaging dừng.

## Verification

- Notebook06 targeted10PASS, gồm replaycompleted synthetic, sai checkpoint/env/source/digest, gate bật lại và tampered completed evidence. Storage synthetic không đổi; lockedCSV sentinel không bị chạm. Không chạy notebook thật hoặc held-out evaluation.
- Distribution29PASS trước khi thêm ba regression cases; vòng allowlist hiện hành4PASS (ba mới và case inventory). Không rerun full suite. Các roundtrip archive tests chỉ dùng fixture tạm; không tạo project-code.zip/project-data.zip bàn giao.
- HTTP thật trên WindowsPython3.13.17: health200/predict200, offlinechat/batch/preview/negativegatesPASS. LR tuned C=2 checksum `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`; schema375/retained318/classes587. Toàn8x587proba so Colab referencePASS, labels/Top3exact, maxabs2.168404344971009e-19. Fit/test/outbound/LLM counters0.
- 56source/configfiles trước sửa,7deploymentartifacts và notebooks03/04/05 đúng SHA cũ. Chỉ bổ sung config packaging mới; synonyms giữ SHA `036d756fb202612122a31e8a041e60e98a33cc632a7caa41df25ccfe2689d527` và135active/240pending. Feature schema, mapping, checkpoint và kết quả khoa học không đổi.
- Dùng testinterpreter3.11 đã có; targeted notebook tests dùng JSON/AST và fixture, không cần nbformat. Không cài pytest/nbformat vào .venv-web hoặc thay dependency production. Smoke ML thật dùng đúng .venv-web3.13.17 đã duyệt.

Receipt/log/SHA mới ở `reports/handover_blocker_fix/` là control records của vòng này. Chúng tách khỏi22evidence được pin trong code package; bản Markdown này được source allowlist hiện có giữ lại. Frozen packaging manifest mới liệt kê nguồn/config,22supplements,7deploymentartifacts và missing-on-Windows. Các artifact dataset/checkpoint nghiên cứu vẫn thuộc data-side; không tự đưa vào codeZIP.

58đường dẫn data-side kỳ vọng ngoài lockedCSV hiện có file trên Windows (existence-only), không thiếu trong danh sách đã kiểm. `data/processed/test.csv.gz` không được stat/hash/open; trạng thái NOT INSPECTED. Không suy từ existence rằng toàn data bundle đã đúng checksum. DataZIP/Drive vẫn NOT VERIFIED trong vòng này.

Không tuyên bố full-suitePASS hoặc Colab thậtPASS. Các lỗi generator/bootstrap fixture/multiprocessing được triage từ trước không mở rộng xử lý ở vòng hai blocker này. Source thay đổi cần publish theo helper hiện có và dùng digest mới khi chạy Colab; nhiệm vụ này không publish hoặc sửa Drive.
