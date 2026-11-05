# Chỉ mục tài liệu và inventory

Cập nhật 2026-10-30. Sáu trang chính để đọc/bàn giao; giữ thêm đặc tả Phase5 vì hợp đồng evidence/context/gate cần chi tiết. Archive giữ nội dung lịch sử, không là hướng dẫn vận hành hiện hành.

| Thứ tự | Tài liệu | Mục đích |
|---|---|---|
| 1 | [SYSTEM_ARCHITECTURE](SYSTEM_ARCHITECTURE.md) | Luồng thực tế, trách nhiệm, 375feature/587classes, state và score |
| 2 | [ML_EXPERIMENTS](ML_EXPERIMENTS.md) | Dataset/split, 5baseline/5tuned, 3hard/2soft trước/sau, uncertainty/benchmark/final test |
| 3 | [DEVELOPMENT_LOG](DEVELOPMENT_LOG.md) | 11 giai đoạn kỹ thuật, thành phần, phương pháp, kết quả và hạn chế |
| 4 | [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE.md) | Windows/pins/7artifacts, local API/web/Gemini, Colab và lỗi thường gặp |
| 5 | [HANDOVER_GUIDE](HANDOVER_GUIDE.md) | Hai ZIP, source publish, notebook safety, kiểm chứng/rollback |
| 6 | [Phase5 specification](phase5_llm_integration_design.md) | Contract v2/evidence/context, provisional gate và kế hoạch đánh giá/telemetry |

Nhật ký là tài liệu tham khảo theo tiến trình, không cần đọc toàn bộ trước khi chạy ứng dụng. Bắt đầu kỹ thuật: architecture → ML → deployment → handover.

## Trạng thái hiện hành

- LR tuned C=2 đã chọn **trước final test**, actual Windows3.13.17 checkpoint/API PASS. Test Macro F1 0.808163486172862 là kết quả mô tả, không lý do chọn lại model.
- Hard tuned LR+SVC+KNN là best observed validation Macro F1; CI bootstrap delta với LR chứa0, không tuyên bố ưu thế thống kê/clinical.
- Gemini live **NOT VERIFIED**: có actual HTTP400 schema-state rejection,503high-demand và timeout; wire375 mitigation chưa có accepted extraction. Live opt-in/key configured không có nghĩa provider ready.
- Code ZIP lịch sử117files VERIFIED offline; data ZIP, cloud sync/fresh-VM workflow release hiện hành **NOT VERIFIED**. Không suy clean-room PASS từ fixtures hoặc smoke Colab revision cũ.
- Final evaluation đã hoàn tất. Working copy06 vẫn gateTrue từ execution; không Run All. Tài liệu cũ ghi gateFalse hoặc chưa có API/test là lịch sử; notebook/output không sửa trong đợt này.

## Inventory trước và sau hợp nhất

Trước:16Markdown trực tiếp trong docs, nhiều cập nhật nối tiếp/lặp trạng thái, chưa có index. Sau:7tài liệu đọc chính (index + architecture/ML/log/deployment/handover/spec),7stubs để giữ caller contracts, archive theo bốn nhóm. Status ở bảng là **xử lý tài liệu**, không phải trạng thái model.

| Tài liệu trước | Phân loại / nơi hiện hành | Nội dung trùng đã hợp nhất | Nội dung riêng giữ trong archive | Tham chiếu ngoài docs cần bảo toàn |
|---|---|---|---|---|
| SYSTEM_ARCHITECTURE.md | ACTIVE, viết hiện trạng | State/model/phase status → ML/log | [Thiết kế v1/interface/score-null](archive/integration/SYSTEM_ARCHITECTURE.md) | Root README nay trỏ trang active |
| MODEL_SELECTION_RATIONALE.md | MERGE → ML_EXPERIMENTS, stub | Decision updates/CV/model tables | [Phân tích học thuật đầy đủ, CV/figures/frozen protocol](archive/ml/MODEL_SELECTION_RATIONALE.md) | Notebook03/06, Phase3 report; giữ old anchors |
| PROJECT_DEVELOPMENT_LOG.md | MERGE → DEVELOPMENT_LOG, stub | Các status update và hội thoại → technical progression | [39 mục gốc bất biến](archive/planning/PROJECT_DEVELOPMENT_LOG.md) | notebooks/README, Phase3 report/anchors |
| LOCAL_PREDICTION_API.md | MERGE → DEPLOYMENT_GUIDE, stub | Python/7artifacts/API/commands | [Contract HTTP và giới hạn lúc triển khai](archive/integration/LOCAL_PREDICTION_API.md) | Final closeout report |
| LOCAL_WEB_MVP.md | MERGE → DEPLOYMENT_GUIDE | Env/API/UI/commands/debug | [Regression phạm vi, browser và timeline Gemini diagnostics](archive/integration/LOCAL_WEB_MVP.md) | Không caller source/notebook bắt buộc; old docs links đã chuyển archive |
| LR_WINDOWS_COMPATIBILITY.md | MERGE → DEPLOYMENT_GUIDE | Pins/approval/start server | [Full frozen synthetic reference/probe procedure](archive/integration/LR_WINDOWS_COMPATIBILITY.md) | Không caller code/notebook; evidence JSON giữ nguyên |
| HANDOVER_GUIDE.md | ACTIVE, viết gọn | Setup/API/runtime → deployment | [Workflow và snapshot trước hợp nhất](archive/planning/HANDOVER_GUIDE.md) | Smoke/06 dùng anchor không-có-drive-for-desktop, được giữ |
| phase3_colab.md | MERGE → deployment/handover, stub | Runtime paths/source/mount/session | [Revision95b01d6e và workflow cũ](archive/runtime/phase3_colab.md) | Notebook00–03, notebooks/README, package_colab/update_colab_notebooks |
| phase3_preflight.md | ARCHIVE | Resource/checkpoint/pipeline explanation → ML/log | [42tests, no-fit local preflight và giới hạn khi chưa train](archive/ml/phase3_preflight.md) | Không caller ngoài docs |
| phase4_ensemble.md | MERGE → ML_EXPERIMENTS, stub | Ensemble policy/metrics/rationale | [Reports/output/inference và bổ sung tuning](archive/ml/phase4_ensemble.md) | Notebook04, notebooks/README, build_ensemble_notebook |
| phase5_llm_integration_design.md | ACTIVE, spec viết gọn | Setup/model/phase status → deployment/ML | [Schema minh họa v2 và kế hoạch trước tích hợp](archive/integration/phase5_llm_integration_design.md) | Không external caller bắt buộc; giữ source/schema thay vì JSON viết tay |
| portability_validation.md | ARCHIVE + stub | Runtime workflow → deployment | [Bằng chứng Phase1/local/Colab, các revision và giới hạn](archive/runtime/portability_validation.md) | notebooks/README |
| portable_runtime.md | MERGE → deployment, stub | Chuyển hướng runtime | [Trang chuyển hướng cũ](archive/runtime/portable_runtime.md) | build_preprocessing_notebook string contract |
| bootstrap_order_fix.md | ARCHIVE | Chuyển hướng startup ZIP cũ | [Deprecated bootstrap note](archive/runtime/bootstrap_order_fix.md) | Không caller ngoài docs |
| RUNTIME_DISTRIBUTION_PLAN.md | MERGE → handover/deployment | HaiZIP/publisher/setup/status | [Audit nguyên nhân script upload, ownership, acceptance/rollback](archive/planning/RUNTIME_DISTRIBUTION_PLAN.md) | Không caller code/notebook; không thay bootstrap |
| WORKSPACE_HANDOVER_PLAN.md | ARCHIVE, inventory historical REVIEW | ML_GAPS → ML, workflow → handover | [Size/duplicates/dependencies/actions/snapshot Drive/local](archive/planning/WORKSPACE_HANDOVER_PLAN.md) | Snapshot cũ không chứng minh copies/cloud hôm nay |

Root README cũ được giữ tại [archive](archive/planning/PROJECT_README_before_consolidation.md); README mới chỉ điều hướng và trạng thái hiện hành. Bảy stubs không là nguồn hướng dẫn thứ hai; giữ anchors để không sửa nguồn, notebook hoặc report gốc. Các báo cáo [audit](../reports/dataset_audit.md), [EDA](../reports/eda_summary.md), [Phase2](../reports/preprocessing_decision_review.md), [Phase3](../reports/phase3_post_training_audit.md), [closeout](../reports/final_model_evaluation_closeout.md), [validation](../reports/validation.md) và hai reports/runs Phase1 đã được đưa vào rà soát, giữ nguyên bytes. Phase1 run reports trùng flat report nhưng không xóa; đường dẫn có tooling sử dụng.

```text
docs/
  README.md
  SYSTEM_ARCHITECTURE.md
  ML_EXPERIMENTS.md
  DEVELOPMENT_LOG.md
  DEPLOYMENT_GUIDE.md
  HANDOVER_GUIDE.md
  phase5_llm_integration_design.md
  <7 compatibility stubs cho callers cũ>
  archive/
    ml/             rationale, preflight, ensemble
    runtime/        Colab, portability, deprecated redirects
    integration/    API, MVP, Windows qualification, Phase5/v1 design
    planning/       immutable original log, plans, old handover/README
```

<a id="archive-integrity"></a>
## Archive và bất biến lịch sử

Nhật ký gốc ở archive/planning/PROJECT_DEVELOPMENT_LOG.md giữ **nguyên byte**, SHA256 **f02cea9208ada0e86d0cd3ef20188b507e54859e08406568db9a3e5275a9b702**. Không thêm banner hoặc sửa relative links bên trong file đó. Nhật ký mới ghi cả thất bại kỹ thuật/đính chính và quyết định hiện tại, không viết lại khoa học theo kết quả test.

**Ngoại lệ link có chủ đích:** link trong immutable log vẫn tính từ vị trí gốc docs/, không từ archive/planning/. Khi đọc, dùng mapping inventory ở trên hoặc path gốc/compatibility stub. Validator kiểm log với original docs base và relocation map, tách khỏi direct rendered archive links. Không tuyên bố mọi link click trong nguyên bản immutable đã được chuyển địa chỉ.

Các archive Markdown khác được gắn banner lịch sử và đổi đường dẫn Markdown tương đối theo vị trí mới; không đổi prose/metrics. Code blocks/bare artifact paths lịch sử vẫn tính từ project/storage root như tại thời điểm ghi. Link Drive-only là **logical artifact reference**, không bằng chứng file tồn tại local hay cloud mới được kiểm. External URLs không được gọi trong nhiệm vụ offline này.

<a id="documentation-validation"></a>
## Kiểm chứng đợt hợp nhất

**PASS:**497 local link destinations và76anchor references trên41Markdown (31trong docs, root README, notebooks/README,8reports) cùng Markdown cells của8notebooks;0missing path/anchor. Trong497 có396direct destinations và101links trong immutable log kiểm theo original-base/relocation map.71external URLs chỉ kiểm phân loại, không fetch. Đây là ngoại lệ render đã nêu ở trên, không gọi101historical links là direct-click PASS.

**PASS:**103assertions đối chiếu metric/identity/split/CV/development-case status,1Python setup example và13PowerShell examples parse cú pháp, không thực thi lệnh. SHA256 của12.528file ngoài docs/README giữ nguyên, kể cả source/notebooks/data/checkpoints/reports/dist và environment/cache;0file ngoài phạm vi bị thêm/mất/thay. Ngoài docs chỉ root README thay đổi có chủ đích. Nhật ký archive khớp SHA gốc. Các số225unit tests và browser/Colab PASS trong nội dung là bằng chứng lịch sử, không phải tests vừa chạy lại.

Phạm vi: docs hiện hành/archive, root README, report links, notebook Markdown cells và doc paths trong scripts/source/tests. Không gọi Gemini, không fit/predict, không parse locked-test CSV, không tạo ZIP/publish/cleanup. SHA byte-only trước/sau kiểm file bất biến, không xem nội dung CSV để phân tích ML.

Các dữ kiện được đối chiếu từ JSON/config/source đã có:375features/587classes, step/split counts, SGKF holdout586/586/587, validation baseline/tuned/ensemble, bootstrap/benchmark, final scores/manifest, LR identity/pins và Windows qualification. Không dùng notebook output làm checksum verification mới hoặc dùng fixture làm real evidence.

Chưa nghiệm thu: Gemini live acceptance/quality, human-reviewed gate/evaluation, data ZIP đầy đủ, cloud sync/fresh-VM release. Không đổi model mặc định, deployment policy hoặc nội dung artifact. Chỉ cần duyệt nội dung/tổ chức tài liệu; không có cleanup/source/runtime change chờ thực hiện trong nhiệm vụ này.
