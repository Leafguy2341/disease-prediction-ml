# Chạy ứng dụng local và notebooks Colab

## Layout local hiện hành — 2026-11-11

Owner đã yêu cầu gộp storage vào project. Cây đang dùng là `disease-prediction-ml-git-sync/{app,src,configs,notebooks,scripts,tests,docs,data,artifacts,reports}`. Không lồng wrapper `disease-prediction-ml-data` vào project. API `run_api.py` mặc định storage = directory chứa launcher; nếu đã đặt DISEASE_API_STORAGE_ROOT, giá trị explicit vẫn thắng. Đặt lại biến tới root hiện tại trước khi restart nếu terminal giữ đường dẫn cũ:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
$env:DISEASE_STORAGE_ROOT = (Get-Location).Path
$env:DISEASE_CHAT_MODE = 'offline'
```

Giữ đúng interpreter Windows3.13.17/dependencies đã qualify; không dùng Python3.11 để bỏ qua model guard. Dataset/weights/full reports nằm local nhưng vẫn Git-ignore. Source/config cũ trong data release không được gộp đè lên source Git. Các mô tả hai-root/ZIP ở bên dưới là lịch sử phát hành, không là default local hiện hành; SHA của release cũ không thay đổi. Colab vẫn dùng canonical Drive và shared bootstrap cũ, không truy cập ổ Windows trực tiếp.

Notebook07 viewer tự chứa saved tables/375 descriptions và4PNG đã pin checksum: chạy setup/viewer trên Colab không cần mount, ROOT hoặc upload script. RUN_RESEARCH/RUN_SEMANTIC mặc định False; khi bật research mới phải có source/dependencies và snapshot embedding phù hợp. Snapshot chỉ là saved evidence, không phải benchmark mới/semantic PASS. Notebook06 và output lịch sử không được chạy lại trong bước này.

Migration local:145 file được chuyển cùng volume,4 file cùng đường dẫn trùng byte giữ bản project. Các file non-test kiểm SHA trước/sau; locked test chỉ rename và kiểm inode/size/mtime, không mở payload. Không xóa folder legacy/source/config cũ hoặc archives. Biên nhận và snapshot notebook trước sửa được giữ ngoài repository trong thư mục maintenance. Runtime không tự fallback về folder legacy khi thiếu artifact.


## Layout bản bàn giao hai ZIP — 2026-11-05

Local code: `disease-prediction-ml/`; persistent data/model: sibling `disease-prediction-ml-data/`. Từ code root đặt `$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path` và `$env:DISEASE_CHAT_MODE='offline'`, rồi chạy smoke/Uvicorn bằng CPython3.13.17 và dependencies đã pin bên dưới. Không cần API key; không đổi loader, checkpoint hoặc scientific identity. `.venv` không nằm trong ZIP, phải cài requirements trên máy nhận. `runtime.local.example.json` cũng dùng sibling này; canonical Drive không đổi.

Inventory bên trong hai ZIP kiểm exact members/hash/bytes; release receipt bên ngoài ghi CRC và clean-extraction HTTP smoke. Quy trình kiểm sạch phải chặn đọc source/data gốc, chỉ cho dùng installed dependency environment; không được nhận PASS nhờ artifact còn nằm trong repo tác giả. Không dùng các hướng dẫn root `.`/mirror Windows cũ bên dưới cho layout hai folder mới nếu chưa chủ động bố trí artifact tương ứng.

## Handover maintenance 2026-11-05 — hai blocker CLOSED

[Notebook06 closeout và packaging allowlist](../reports/handover_blocker_fix.md) đã qua targeted verification. Production135active/240pending và LR tuned không đổi. Notebook06 chỉ đọc existing completed bundle đúngSHA; vô hiệu hóa cả diagnostics predict/copy trước đây, giữ outputs/counts. [Policy22supplements](../configs/handover_code_supplements.json) cho phép chính xác file đã duyệt với hash/size, không glob dữ liệu lớn. Code handover READY để nhận yêu cầu đóng gói riêng; chưa tạoZIP, chưa publishDrive hoặc chạyColab thật. Các trạng thái BLOCKER ngày04 dưới đây là lịch sử.

## Final release gate 2026-11-04 — freeze135active

[Kết luận và triage đủ34test](../reports/final_release_gate.md): local offline demo có actual LR/HTTP PASS, giữ135active/240pending. Kiểm mở rộng127ứng viên phát hiện288/720ca sai state về fiction/third-person; không thử activation production lần nữa. Không gọi đây là clinical false-positive rate. Synonyms vẫn SHA `036d756fb202612122a31e8a041e60e98a33cc632a7caa41df25ccfe2689d527`.

Notebook06 chỉ đổi source gate vềFalse và authorization rỗng, giữ executed outputs. Không chạy notebook; closeout-viewer contract vẫn còn blocker. Packaging allowlist hiện thiếu small terminology/evaluation fixtures mà tests yêu cầu. **Local demo RELEASE_READY; toàn project handover/ZIP BLOCKER.** Xem [manifest artifact/freeze](../reports/release_final_gate/packaging_artifact_manifest.json) cho SHA,7deploymentfiles và supplements cần bảo toàn. Không tạo ZIP/publish Drive trong vòng này. Không chạy script activation cũ để tiếp tục lô2.

## Controlled activation 2026-11-04 — ĐÃ ROLLBACK, CHƯA KÍCH HOẠT

Owner cho phép tối đa 128 feature/145 alias. Packet/source pins khớp; 375 keys/order được giữ. Kiểm thêm 735 ngữ cảnh phát hiện một false positive: “Nhân vật trong truyện bị hoang tưởng hoặc ảo giác.” bị ghi nhận `delusions or hallucinations=present` (gate `unmapped` vẫn chặn inference). Loại feature này, còn 127 feature/144 alias đủ qualification cơ học. Không sửa guard/parser hoặc diễn giải đây là thẩm định y khoa.

Chuẩn bị bốn lô 32/32/32/31. Lô 1 áp dụng thử 32 feature nhưng toàn bộ suite chưa PASS; công cụ khôi phục nguyên byte và dừng lô 2–4. **Production vẫn 135 active / 240 pending; số kích hoạt giữ lại là 0.** 262/375 chỉ là coverage dự kiến nếu 127 feature vượt toàn bộ điều kiện trong đợt sau.

Lô1 và baseline sau rollback đều có 3433PASS/21FAIL/13ERROR/5SKIP; 34test IDs lỗi trùng nhau. Nguyên nhân quan sát gồm thiếu `nbformat`, test notebook/bootstrap chưa khớp source hiện hành, expected payload count45 nhưng thực47, và Windows multiprocessing Access denied. Không có failure của extraction/activation. Chưa đạt gate toàn suite nên không chạy tiếp dù lỗi tái hiện ngoài dictionary mới; cần xử lý các blocker riêng trước đợt sau.

[Manifest, backup và test logs](../reports/terminology/activation-20261104/manifest.json) ghi checksum từng bước. SHA-256 production trước/sau rollback: `036d756fb202612122a31e8a041e60e98a33cc632a7caa41df25ccfe2689d527`. Không ghi đè evidence hoặc áp dụng tiếp lô lỗi. `scripts/activate_reviewed_symptoms.py` chặn chạy tiếp khi trạng thái FAILED.

Tests proposal cũ replay tường minh với backup BEFORE; không phải bằng chứng production đã active. Tests production kiểm exact delta và checksum manifest. Giữ nguyên 86 ca cũ; `semantic-084` có expectation sau kích hoạt khai báo riêng cho `elbow swelling` vì expectation lịch sử là alias pending không được match. Sau rollback, expectation pending cũ tiếp tục áp dụng. 821 qualification cases giữ nguyên; 5 ca của feature bị loại chỉ chạy như fixture lịch sử, không được tính là đã kích hoạt.

CSV gốc giữ APPROVE128 / REVISE73 / CLARIFY26 / HOLD148. Overlay đợt này hoãn thêm `delusions or hallucinations`, tương đương REVISE74 và 127 ứng viên còn lại. HOLD của feature đã active nghĩa là giữ nguyên, không tắt chúng. Display, question flags, parser, checkpoint, schema/mapping và Drive không đổi. Cấu hình cuối đã trở về bản cũ.

## Controlled activation proposal — LỊCH SỬ, CHƯA KÍCH HOẠT

Danh sách mới nhất: [375quyết định](../reports/terminology/symptom_activation_decisions.csv), SHA2909bd6e639736cb0c7a3b33505009a891a23e727f2722c6a55910d2d0f08c90; [bằng chứng fixture](../reports/terminology/symptom_activation_validation.json); [821ca giả định](../data/evaluation/vietnamese_symptom_activation_cases.jsonl). APPROVE trong CSV là đề xuất trình ChatGPT/chủ dự án duyệt, không phải phê duyệt cuối hoặc trạng thái runtime.

Đã đọc/đối chiếu checksum cả3packet cũ và86synthetic cases. Quyết định toàn375: APPROVE128, REVISE73, CLARIFY26, HOLD148. Trong145READYpending,13nhãn bị loại do wording/phạm vi/subject/safety còn rộng,4nhãn không qua test parser,128còn lại đạt qualification trong fixture. HOLD cho121READYđãactive chỉ có nghĩa giữ nguyên và không mở rộng variants;27AMBIGUOUS cũngHOLD. Không tắt alias đang có. CLARIFY26 giữ cơ chế hỏi rõ, không thêm alias. Các nhóm gum/breathing cần định nghĩa nguồn; speech/frequency-volume/heartburn-burning chest/neck-muscle không được gộp hoặc thêm alias rộng.

Nếu sau này duyệt đúng128feature/145alias trong đề xuất và chúng vẫn qua các kiểm tra identity, active coverage dự kiến135→263/375, pending240→112. Hiện thực tế vẫn135/240. Không suy ra từ coverage rằng model chính xác hơn; không tự mở question_eligible cho mọi feature mới. Không có công cụ apply/activate trong nhiệm vụ này và không cần restart server để nhận thay đổi hành vi, vì production chưa được sửa.

Qualification dùng bản sao dictionary ở temp với128feature bật giả định, cùng extractor/validator/offlineV2/policy hiện hành; không fit/predict LR. Có821ca cho145aliases: khẳng định/phủ định/không dấu, boundary và neighbor negatives. Tất cảPASS; đây là các mẫu câu có kiểm soát, không bao phủ mọi cách diễn đạt hoặc false-positive rate trên người thật. Bộ86ca gốc chạy riêng trên production không đổi, không đổi expected inactive thành active để ép PASS.

Sàng lọc ban đầu132feature có844ca,8ca không đạt trên4alias: excessive urination at night (bi tieu có thể bị hiểu thành bí tiểu ở prefix), fluid retention (cơ thể→co the vướng cue có thể), incontinence of stool và pupils unequal (không là thành phần nghĩa của alias nhưng bị xem như phủ định). Có1case ghi nhận sai feature retention of urine nhưng gateunmapped vẫn chặn inference. Các alias nàyREVISE, không bypass guard hoặc sửa parser trong task này. Toàn packet có50cặp feature/alias trên34feature được đánh dấu lexical/semantic risk; đây không phải50lỗi thực tế hay một tỷ lệ y khoa. Final APPROVEfixture không quan sát sai feature trong các ca đã định trước.

Script `scripts/review_symptom_activation.py` chỉ tạo lại báo cáo/cases và temp fixture, không sửa configs/runtime. Có thể kiểm bằng interpreter test Python3.11 hiện có, vì script không deserialize model. Script ghi input hashes, source/policy/qualification identity và guard counts. Dùng SHA và file decisions để ChatGPT rà soát cuối; chưa bật alias hoặc đổi bất kỳ production field nào trước khi có chấp thuận riêng.

## Semantic review375 — trạng thái mới nhất 2026-11-04

Đã rà soát bản đề xuất đủ375canonical feature theo schema order. Bảng hiện hành: [symptom_dictionary_review.csv](../reports/terminology/symptom_dictionary_review.csv); [thay đổi đề xuất](../reports/terminology/symptom_dictionary_changes.csv); [collision và overlap](../reports/terminology/symptom_dictionary_collisions.csv). CSV full có SHA40aa98c794817ad7b2eaa56e39060fecd96d5231928e3737da0f9628a65b63dc. Các SHA/count ở phần lịch sử bên dưới thuộc packet trước, không dùng để xác minh bản hiện hành.

READY266 nghĩa bản đề xuất rõ về ngôn ngữ và qua kiểm tra kỹ thuật, chưa được phép tự kích hoạt và không phải bác sĩ thẩm định. Trong đó121đã active từ trước,145pending sẵn sàng trình chủ dự án duyệt. REVIEW56 cần rà soát thêm; HIGH_RISK_COLLISION26 cần phân định từ vựng/ngữ nghĩa; AMBIGUOUS27 cần làm rõ định nghĩa nguồn. confidence HIGH/MEDIUM/LOW là độ chắc chắn tương đương ngôn ngữ, không phải score của model; needs_review=true cho cả375, nghĩa vẫn cần người duyệt. production_activation là trạng thái thực độc lập:135ACTIVE_EXISTING/240PENDING_REVIEW, không tự suy ra từ READY. Không có alias mới được bật.

proposed_display_vi/proposed_aliases_vi chứa sửa đổi mới; display_vi/aliases_vi/aliases_en/activation_status/question flags dùng runtime giữ nguyên. Có82alias bổ sung đề xuất cho76feature. Những sửa quan trọng: pimples không mặc định là nhọt; flatulence không tự thêm ý quá nhiều; infertility không suy ra từ khó có con; tách buồn nôn/nôn, đau/ngứa, cổ/cơ, tần suất tiểu/tổng lượng tiểu, triệu chứng/tên chẩn đoán. Nhãn tổng hợp và hai cặp gum pain/pain in gums, shortness of breath/difficulty breathing cần publisher định nghĩa, không tự tạo khác biệt bằng cách dịch khác nhau.

Packet collision có8nhóm bỏ dấu trong toàn bộ đề xuất và9nhóm rủi ro ngữ nghĩa. Chỉ2collision bỏ dấu đang ở production: dau co/dau mat; còn lại là cảnh báo trước kích hoạt. Một số nhóm có thể hỏi mô tả cụ thể; nhãn thực sự trùng nghĩa thì hỏi user chưa đủ giải quyết. Có2feature AMBIGUOUS và12HIGH_RISK_COLLISION đã active từ lịch sử; đây là phát hiện cần quyết định riêng, không tự tắt hoặc mở rộng alias trong vòng review này.

Nguồn hiện ghi22feature có tài liệu hỗ trợ thuật ngữ/ranh giới,1reference cũ chưa kiểm lại và352chưa đối chiếu nguồn độc lập. Không coi nguồn định nghĩa khái niệm là bằng chứng đã xác minh nghĩa cột dataset hoặc mọi cách nói khẩu ngữ. Ví dụ [MedlinePlus lượng nước tiểu](https://medlineplus.gov/ency/article/003146.htm), [tần suất tiểu](https://medlineplus.gov/ency/article/003140.htm), [NIDDK hesitancy](https://www.niddk.nih.gov/health-information/urologic-diseases/urinary-retention/symptoms-causes), [NHS breathlessness](https://www.nhs.uk/symptoms/shortness-of-breath/), [NIDCD stuttering](https://www.nidcd.nih.gov/health/stuttering), [MSD buồn nôn/nôn](https://www.msdmanuals.com/vi/professional/khoa-nhi/triệu-chứng-ở-trẻ-nhũ-nhi-và-trẻ-em/buồn-nôn-và-nôn-mửa-ở-trẻ-sơ-sinh-và-trẻ-em).

86ca [synthetic Vietnamese](../data/evaluation/vietnamese_symptom_semantic_cases.jsonl) có khẳng định/phủ định/uncertainty, không dấu, NFD, typo, collision, tên bệnh và known+unknown hỗn hợp. Tất cả pending_human_review, không phải test lâm sàng hoặc dữ liệu bệnh nhân. Không sửa typo bằng fuzzy hoặc đoán alias mơ hồ để tăng coverage. Gửi cả375row và changes/collisions cho ChatGPT/người duyệt trước quyết định kích hoạt. Review này không đổi hành vi web nên không cần chạy lại notebook hoặc model.

Accuracy được kiểm lại: metric toàn test split ở model_evaluation, xuất một lần cạnh tiêu đề; không có accuracy gắn vào mỗi dòng Top3. Raw score/ordering không đổi. Vẫn phải giữ chú thích score chưa calibration và Accuracy84,4082% không phải %đúng của từng gợi ý.

## Hội thoại tiếp tục, preview và packet thuật ngữ — hiện hành 2026-11-04

Sau khi restart server và Ctrl+F5, các lượt offline có ba lựa chọn: **Hỏi thêm triệu chứng**, **Tôi muốn bổ sung triệu chứng khác**, **Xem kết quả tham khảo hiện tại**. Nút bổ sung đưa con trỏ về ô nhập, không tạo feature hoặc gửi yêu cầu ngầm. Nút hỏi thêm tiếp tục state hiện có và giữ nguyên các mục đã trả lời. Nếu hết budget một vòng, thao tác hỏi thêm được mở vòng kế tiếp, tối đa2vòng; mỗi vòng tối đa4batch/12câu, tổng lượt user/control tối đa24 và TTL hiện có. Batch size cấu hình1–5, mặc định3. Không hỏi lại, không tự coi unanswered là denied, không tự tạo kết quả chỉ vì hết budget. Nếu không còn câu hỏi cùng ngữ cảnh hoặc nhóm tổng quát phù hợp, bot nói rõ và vẫn cho bổ sung/preview. Không bảo đảm mọi input có đủ câu hỏi liên quan.

Khi chọn preview, phải có ít nhất1present đã kiểm chứng; evidence gốc được kiểm lại, vector theo schema375. Chỉ hạ yêu cầu số lượng cho thao tác chủ động này, không hạ gate tự động hoặc bỏ urgent/ambiguity/conflict/uncertainty/unmapped/integrity. Unanswered đơn thuần có thể còn unknown trong preview; Không rõ hoặc câu trả lời mơ hồ thì cần làm rõ trước. Các mục Không rõ có thể sửa bằng lựa chọn trong nhóm; số/batch_id vẫn phải hiện hành. Preview gắn nhãn **Kết quả tham khảo với thông tin còn hạn chế**, dùng Top3 thật, không đổi score hoặc cộng ba điểm thành100%. Không có present thì không predict. Hết giới hạn cả phiên vẫn cần tạo phiên mới; không có vòng lặp hỏi vô hạn.

Caption mới: **Điểm tự tin dự đoán (%) (Accuracy trên tập test: 84,4082%)**. Accuracy xuất hiện một lần cạnh tiêu đề, là metric toàn bộ28.066 mẫu test đã được đánh giá trước đây, không phải % đúng của từng bệnh gợi ý. Điểm tự tin vẫn là score chưa calibration, không phải xác suất mắc bệnh hay độ tin cậy chẩn đoán. Presenter chỉ lấy Accuracy từ packet closeout có SHA102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131 và checkpoint đúng identity; không đọc test CSV/tạo metric mới. Packet optional tại `artifacts/metadata/final_evaluation_audit/colab_evidence.json` trong project code tree; thiếu/sai checksum hoặc checkpoint khác sẽ hiện **chưa xác minh**, không lấy metric khác bù. API raw `score_label` lịch sử vẫn giữ để tương thích; caption mới trong presentation.confidence_label/model_evaluation. Nhãn thay đổi không có nghĩa model đã được calibration.

**Packet gửi ChatGPT review:** [symptom_dictionary_review.csv](../reports/terminology/symptom_dictionary_review.csv), UTF-8 BOM,375dòng theo thứ tự schema, không chia nhiều file. Gồm canonical/display/aliases/semantic notes/confidence/collision risks/needs_review/review status/production activation/sources. Đã có375/375đề xuất, nhưng chỉ135feature giữ alias Việt production;240chờ review. Alias sổ mũi của coryza được tạm ngừng để review phạm vi nghĩa nhãn nguồn. Bản đề xuất mới không tự kích hoạt; nhãn tổng hợp và LOW không được dùng tự gán feature. Canonical English/schema giữ nguyên. READY126, REVIEW214, AMBIGUOUS17, HIGH_RISK_COLLISION18; READY không phải bác sĩ thẩm định, chỉ tình trạng sẵn sàng của bản có kiểm tra và provenance hiện có. Tất cả375vẫn needs_review=true.

Tải CSV trên lên ChatGPT để review từng dòng, ưu tiên17AMBIGUOUS/18HIGH_RISK_COLLISION và240PENDING_REVIEW; cần giữ canonical/order và phân biệt near-synonyms. Không tự bật alias bằng cách đổi flag sau khi chỉ nhìn coverage100%; cần kết quả review và phê duyệt triển khai. Script báo cáo hiện có hỗ trợ xuất lại khi có chủ đích:

```powershell
& '.\.venv-web\Scripts\python.exe' -B -m scripts.build_synonyms_report --review-csv reports/terminology/symptom_dictionary_review.csv
```

Lệnh chỉ tạo packet/report, không dịch qua API, không kích hoạt alias hoặc sửa schema. Bản hiện tại có SHA39dd92edbc910043399bacbdb46efe657e4488072351008014eae67a400a8e04. Chạy web vẫn dùng lệnh Offline V2 bên dưới; không training, notebook06 hoặc key.

## Chạy Offline V2 — 2026-11-04

Trong PowerShell tại project root, dừng server cũ bằng Ctrl+C, rồi chạy:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
$env:DISEASE_CHAT_MODE = 'offline'
& '.\.venv-web\Scripts\python.exe' -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Giữ terminal chạy; mở http://127.0.0.1:8000, Ctrl+F5 và bắt đầu hội thoại mới. Lệnh dùng môi trường Windows3.13.17 đã duyệt cùng 7 artifact tại project root; nếu artifact ở root khác, đặt DISEASE_API_STORAGE_ROOT tới root đó. Không dùng Python3.11 để load checkpoint và không nới guard khi health503. Nếu cổng8000 đang được dùng, dừng đúng server cũ hoặc chọn cổng khác và mở đúng URL.

Web mới có combobox chỉ LR tuned C=2; các ứng viên khác chưa được duyệt deployment/runtime Windows. Registry `/api/v1/models` phản ánh loader thực, không coi chỉ tồn tại file checkpoint là deployable. Sidebar cho chọn Offline hoặc xem trước Online; ở Online nút gửi bị khóa và báo LIVE NOT VERIFIED. Cài đặt provider có password input, nhưng không gửi/lưu/test key; khi đóng sẽ xóa ô. Không nhập key thật ở phiên bản này. Không có tự động chuyển provider, kết nối hoặc gửi tin nhắn online. Server legacy được cấu hình LLM riêng không chấp nhận request UI offline.

Batch hỏi mặc định3: chọn Có/Không/Không rõ, mặc định Chưa trả lời. Có thể gửi từng phần và tiếp tục nhóm cũ; không trả lời không đồng nghĩa phủ định. Có thể gõ bổ sung triệu chứng. Câu trả lời theo số qua API cần batch_id trong pending_questions; không sử dụng ID của batch/phiên trước. Dấu hiệu urgent được kiểm trước parser. Sau khi có kết quả, thêm/sửa thông tin sẽ vô hiệu vector cũ và đánh dấu card cũ là lịch sử; đây vẫn chỉ là nghiên cứu.

Các tham số V2 trong configs/phase5b.json.offline: dialogue_version2, batch_size3 (1/3/5), max_question_batches4, max_total_questions12, min_answered_questions3, min_present_for_result3. conversation.max_user_turns12 vẫn giới hạn chung; max_clarification_turns2 là V1, không phải số batch V2. Ngưỡng số triệu chứng/câu trả lời chỉ là policy tạm thời. Hết budget có thể kết thúc thiếu thông tin, không buộc phải có Top3. Không sửa config để tăng điểm model hoặc coi score là xác suất mắc bệnh.

Thuật ngữ mới: thêm cách diễn đạt cho feature rõ nghĩa, phân biệt đau/ngứa mắt và buồn nôn/nôn; không tự hiểu “khó nói chuyện” thành khó vận động lời nói hoặc nhãn tổng hợp “symptoms of infants” thành triệu chứng cụ thể. Nguồn đối chiếu: [buồn nôn/nôn](https://www.chcrr.org/vi/health-topic/nausea-and-vomiting/), [khó nói trong tài liệu SFHP](https://www.sfhp.org/wp-content/files/member_materials/health_education/fact_sheets/stroke_VIT.pdf), [thuật ngữ cúm/viêm màng não NHS](https://111.wales.nhs.uk/pdfs/Meningitis%20poster%20Languages/vietnamese1.pdf). Đây là đối chiếu từ ngữ, không thẩm định lâm sàng. Còn 239 feature không có alias Việt; báo cáo thuật ngữ hiện có liệt kê từng mục, collisions và aliases ngắn. Draft disease display vẫn theo lựa chọn đã duyệt trước, có warning và canonical English phụ.

### Cập nhật nhận diện triệu chứng — 2026-11-04

Guard sức khỏe chỉ phân loại chủ đề; không loại triệu chứng đã ánh xạ hợp lệ chỉ vì có từ khóa sức khỏe. Đã bổ sung 13 mục alias cho nhóm âm đạo/âm hộ, quan hệ tình dục, tinh hoàn/dương vật/bìu. “Tôi bị ngứa âm đạo” nhận `vaginal itching` rồi hỏi thêm; “Tôi bị ngứa âm đạo, ho và sốt” qua quality gate và được dự đoán. Phủ định/chưa chắc chắn vẫn giữ đúng trạng thái, không tính thành triệu chứng hiện diện.

Phần sức khỏe chưa ánh xạ được nhận thông báo giới hạn và không có Top 3. Không tự gán “ngứa vùng kín” cho một vị trí cụ thể, hoặc “chảy máu âm đạo” thành chảy máu sau mãn kinh khi thiếu ngữ cảnh. Thiếu alias chưa chứng minh triệu chứng không có trong dataset: từ điển hiện có alias Việt cho **58/375 feature**, chưa hiểu mọi cách diễn đạt tiếng Việt. Không fuzzy-map hoặc mở rộng schema để đoán. Alias bổ sung là bản nháp cần tiếp tục rà soát.

Dừng server đang chạy bằng Ctrl+C rồi khởi động lại theo lệnh Uvicorn ở hướng dẫn bên dưới để nạp source/config mới. Bắt đầu cuộc trò chuyện mới, tránh giữ trạng thái từ bản cũ. Không cần chạy notebook hay training. Kiểm HTTP với LR tuned thật đã PASS; chưa có kiểm trình duyệt trực quan mới.

Đọc từ project root đã giải nén, nơi có README, src, app, configs và scripts. Local source là bản phát triển chính; Drive giữ data/model; Colab là compute tạm. Không chạy lại training/final test để khởi động ứng dụng.

<a id="windows-runtime"></a>
## 1. Python và dependency

Trained identity: **Python3.13.18, scikit-learn1.6.1, NumPy2.1.3, SciPy1.16.3, joblib1.6.0**. Windows **CPython3.13.17/AMD64**, pandas2.2.3 và exact ML pins đã được duyệt riêng cho đúng LR tuned checkpoint. Python3.11.9/sklearn1.8.0 không được duyệt deserialize model; không hạ/nâng pin để bỏ environment_mismatch.

`.venv-web` hiện có đã kiểm, không cần tạo/cài lại. Trên máy mới, chọn interpreter3.13.17 thực có sẵn; chủ động tạo môi trường riêng rồi cài requirements-api.txt. Không thay Python toàn cục hoặc tự build3.13.18. Ví dụ cho máy **chưa có** `.venv-web`, sau khi kiểm `py -3.13 --version` đúng3.13.17:

```powershell
py -3.13 -m venv .venv-web
& '.\.venv-web\Scripts\python.exe' -m pip install -r requirements-api.txt
```

Kiểm môi trường dùng chung cho các lệnh local bên dưới:

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
& $ApiPython --version
& $ApiPython -m pip check
```

Qualification đã so đủ8×587 probabilities theo protocol rtol1e-10/atol1e-12, exact labels/Top3/schema/source pins. Reference SHA `5fe06a3637c471403d46cdb87b2e5cce2a742e8fff1c99aa4a6cb7caef53d0dc`; maxabs2.168404344971009e-19. [Comparison evidence](../artifacts/metadata/runtime_compatibility/windows31317-v1/reference_comparison_verified.json), [allowlist approval](../artifacts/metadata/runtime_compatibility/windows31317-v1/deployment_runtime_approval.json). Không cần sinh lại reference/chạy notebook06. [Protocol chi tiết lịch sử](archive/integration/LR_WINDOWS_COMPATIBILITY.md) được giữ để truy xuất phương pháp, không phải bước khởi động.

## 2. Bảy artifact local bắt buộc

Tải/copy chỉ đọc từ canonical Drive được cấp quyền về một artifact root Windows, giữ nguyên paths:

```text
<ARTIFACT_ROOT>/
  artifacts/metadata/phase2/dataset_manifest.json
  artifacts/metadata/phase2/feature_schema.json
  artifacts/metadata/phase2/label_mapping.json
  artifacts/metadata/tuning/tuning-v1-9c4dd013abbba14a/manifest.json
  artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/pipeline.joblib
  artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/fit.json
  artifacts/models/tuning/tuning-v1-9c4dd013abbba14a/logistic_regression/metadata.json
```

Không tải dataset/split CSV để phục vụ API. Mount Drive trên Colab không cung cấp đường dẫn Windows. Nếu file có sẵn khác SHA, dừng đối chiếu, không ghi đè manifest/checkpoint.

Phase2 manifest SHA `50308d250d874b1b653a71c31f38dece0ec9fbb4dbc9d94f68bc1461e80b8fe9`; tuning manifest SHA `4a10ddd5deba5fff7927f84ea334196a3f6d127b9777ced2b127f5b5e9389355`; pipeline SHA `4cac3bfd78dfe2849a855130d264c7bebc14d6e8d8e305b15015141663300ac6`; selected identity `tuned-v1-b8a5602679b3dc5c`. Giữ schema375/order và mapping587/order; không thay Drive manifest bằng local variant ca20a551….

Root hiện tại có sẵn bảy file trong chính project nên dùng `(Get-Location).Path`. Máy nhận bàn giao có artifacts ở nơi khác phải đặt **root thực chứa artifacts/**:

```powershell
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
& $ApiPython -B -m scripts.smoke_local_mvp --ml
```

Lệnh dùng synthetic cough+fever, không ground truth, không gọi Gemini/test CSV. Actual LR Windows TestClient/Uvicorn health200/predict200 đã PASS; [real smoke](../artifacts/metadata/runtime_compatibility/windows31317-v1/real_api_smoke_verified.json), [HTTP evidence](../artifacts/metadata/runtime_compatibility/windows31317-v1/uvicorn_http_smoke_verified.json). Máy mới vẫn phải kiểm integrity/env riêng; không dùng mock tests thay real checkpoint proof.

<a id="prediction-api"></a>
## 3a. Chạy website offline (2026-11-02)

Tại project root trên Windows, dùng `.venv-web` 3.13.17 đã duyệt và bảy artifact ở mục 2. Không cần mạng, API key hay cài thêm dependency. Dừng server cũ bằng Ctrl+C, rồi chạy:

```powershell
$ApiPython = (Resolve-Path -LiteralPath '.\.venv-web\Scripts\python.exe').Path
$env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
$env:DISEASE_CHAT_MODE = 'offline'
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Mở http://127.0.0.1:8000/. Health phải có `checkpoint_status: REAL CHECKPOINT VERIFIED`, chat.mode=offline, requests_used=0. UI hiển thị “Chế độ offline — xử lý triệu chứng bằng quy tắc, không dùng dịch vụ ngôn ngữ bên ngoài.” Không cần mở port trên router. Không chạy notebook/training để khởi động web.

Terminal demo dùng cùng LR loader và ChatRuntime (trong terminal khác với cùng các biến trên):

```powershell
& $ApiPython -B -m scripts.demo_offline_chat
```

Thử: `Tôi ho.` → câu hỏi sốt → `có`; `/reset`; `Tôi sốt nhưng không ho.`; `Tôi ho và sốt nhưng không đau đầu.`; `/reset`; `thời tiết hôm nay`; `/quit`. Không tự đặt bệnh kỳ vọng cho các ví dụ synthetic. Mỗi lượt đủ gate sẽ gọi LR thật, không lấy bệnh/score từ từ điển. Score Top3 không chuẩn hóa lại; nhãn bệnh tiếng Anh được giữ nguyên.

Từ điển draft: 375 khóa, 45 feature có alias Việt, tất cả needs_review=true. Chạy báo cáo chỉ đọc:

```powershell
& $ApiPython -B -m scripts.build_synonyms_report
```

Cần người rà soát display_vi, aliases_vi, alias collisions và 330 mục thiếu tiếng Việt trước khi mở rộng phạm vi. Không sửa feature_schema/label_mapping để thêm alias. Không fuzzy matching; chỉ có vài biến thể chính tả đã liệt kê rõ trong dictionary. Keyword không hiểu ngôn ngữ tự do: phrase lạ, ngữ cảnh phức tạp, câu hỏi kiến thức, mixed intent hoặc chủ thể chưa rõ có thể abstain. `dau co` mơ hồ không được tự ánh xạ. Sau lời sửa rõ ràng, hãy mô tả lại triệu chứng hiện tại; contract đòi fresh evidence, không giữ giả định cũ. Đây là hạn chế đã biết, không phải chất lượng trích xuất được xác thực lâm sàng.

Chế độ LLM cũ được giữ bằng `DISEASE_CHAT_MODE=llm` cùng provider/model/live opt-in hiện có; chưa có live end-to-end PASS. Mode offline luôn thắng các biến provider/key/live còn sót. Nếu không đặt mode, một DISEASE_LLM_PROVIDER đã chọn rõ ràng vẫn bảo toàn hành vi LLM cũ; terminal demo luôn ép offline.

Đã kiểm Python3.13.17 checkpoint thật và HTTP TestClient: health200, chat200 qua hai lượt, predict200; Top3 chat=structured predict, denial/urgent không predict, 0 outbound/fit/test/protected writes. Frontend HTML/JS được phục vụ qua app hiện tại; không coi đây là browser visual acceptance test. ZIP cũ giữ nguyên, chưa đóng gói lại. Allowlist code packaging đã thêm synonyms.json cho lần bàn giao sau; không thay data ZIP/Drive/bootstrap.

## 3. FastAPI và website

Dừng server cũ bằng Ctrl+C tại terminal chạy nó; không tự kill process không rõ. Khởi động một worker:

```powershell
& $ApiPython -B -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Mở **http://127.0.0.1:8000/**; OpenAPI tại `/docs`, `/openapi.json`. Không cần mở port router/firewall để truy cập cùng máy. Startup không gọi Gemini; UI mở được chưa có nghĩa chat live PASS.

| Endpoint | Hành vi |
|---|---|
| GET /health | 200 và REAL CHECKPOINT VERIFIED khi model hợp lệ; 503 khi thiếu/sai artifact/env |
| POST /api/v1/predict | JSON present_features là danh sách exact/unique/nonempty; frame uint8 1×375; Top3 LR thật |
| POST /api/v1/chat | message và session_id; guard→extraction→validator→quality gate→LR |
| POST /api/v1/chat với reset=true | Tạo phiên RAM mới, không xóa file hoặc reset provider budget |

Ví dụ predict hoàn toàn giả lập, từ terminal thứ hai:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/health'
$body = @{ present_features = @('cough', 'fever') } | ConvertTo-Json
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/predict' -Method Post -ContentType 'application/json' -Body $body
```

API trả raw predict_proba×100 trên đủ587 lớp, không chuẩn hóa riêng Top3; nhãn **Điểm mô hình (%)**, calibrated=false. Không là xác suất mắc bệnh. Predict structured chỉ yêu cầu ≥1 feature; chat vẫn phải qua min2 **provisional** và các kiểm subject/time/conflict/urgent/invalid. Chat trả session_id để dùng lượt sau; reset gửi `{"message":"","session_id":"<id>","reset":true}`. Provider/model lỗi không được trả Top3 cũ.

## 4. Provider LLM: lựa chọn rõ ràng và qualification

<a id="4-gemini-và-chẩn-đoán-live"></a>
**End-to-end live NOT VERIFIED.** Config public mặc định vẫn Gemini3.8Flash, không tự đổi model. Minimal A đã trả503high demand trong output thực được cung cấp; B chưa gửi. Schema tên dài từng400serving-state; compact wire375 chưa có live acceptance. Không gọi LLM để sinh disease labels/rankings; approved LR tuned vẫn là classifier duy nhất.

### Provider/model đã hỗ trợ trong code

| Provider | Model ID kiểm theo tài liệu | REST/response format | Key / live opt-in |
|---|---|---|---|
| gemini | gemini-3.8-flash (mặc định), gemini-3.5-flash-lite (ứng viên nhẹ) | POST /v1beta/interactions; response_format text/application-json/schema; parse completed steps/model_output | GEMINI_API_KEY / DISEASE_GEMINI_LIVE=1 |
| groq | openai/gpt-oss-20b, openai/gpt-oss-120b | POST https://api.groq.com/openai/v1/chat/completions; json_schema/strict=true; parse choices/message/content, finish_reason=stop | GROQ_API_KEY / DISEASE_GROQ_LIVE=1 |
| openrouter | google/gemma-4-26b-a4b-it:free | POST https://openrouter.ai/api/v1/chat/completions; json_object, **không strict JSON Schema**; parse choices/message/content, finish_reason=stop | OPENROUTER_API_KEY / DISEASE_OPENROUTER_LIVE=1 |
| openrouter (qualification riêng) | nvidia/nemotron-3.5-super-vl:free | Cùng endpoint; json_schema/strict=false, Python validator bắt buộc; chưa xác minh native strict | OPENROUTER_API_KEY / DISEASE_OPENROUTER_LIVE=1 |

[Gemini3.5Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite) có structured output. [Public Standard rates](https://ai.google.dev/gemini-api/docs/pricing), snapshot2026-10-30: Lite0.30/2.50USD mỗi1Minput/output tokens;3.8Flash0.75/3.75USD theo mức đến31/12/2026. Đây là giá niêm yết, không billed cost/quota của tài khoản. [Groq models](https://console.groq.com/docs/models) và [structured outputs](https://console.groq.com/docs/structured-outputs) liệt kê hai gpt-oss models cho strict mode; public rates20b0.075/0.30USD và120b0.15/0.60USD mỗi1Minput/output. Không suy model miễn phí hoặc sẵn có với project này.

**Account eligibility NOT VERIFIED** cho mọi ứng viên mới: process hiện không có Gemini/Groq key hoặc live opt-in, không truy cập authenticated model permissions. Kiểm quyền project/quota trong AI Studio hoặc Groq Console trước khi thử; [Groq permissions](https://console.groq.com/docs/model-permissions), [Groq limits](https://console.groq.com/docs/rate-limits), [Gemini limits](https://ai.google.dev/gemini-api/docs/rate-limits). Model public có trong docs không xác nhận tài khoản được dùng; không đánh giá tiếng Việt tốt hơn từ một response.

### Cấu hình và ranh giới truyền dữ liệu

ProviderSettings.from_environment đọc configs/phase5b.json rồi nhận **DISEASE_LLM_PROVIDER** và **DISEASE_LLM_MODEL**. Chuyển provider phải ghi model rõ ràng; sai provider/model/key-env pair fail closed. API key chỉ từ tên env riêng của provider. create_provider chọn đúng một adapter khi startup; nội dung người dùng/API client không chọn provider. Không routing/fallback sang dịch vụ khác, không thử model khác sau lỗi.

Có thể chỉnh riêng các trường provider/provider.model/provider.api_key_env trong file config khi chủ động quản lý source, hoặc dùng environment dưới đây để giữ config public mặc định. Conversation policy không thay đổi. Gemini named model phải có prefix gemini-; Groq hiện chỉ nhận hai model strict đã nêu. Không tích hợp Llama/third-party endpoint hoặc Groq JSON-only workaround trong bản này.

Tất cả adapter trả canonical JSON cho **validator hiện có**, không tạo mapper thứ hai. Cùng compact wire schema SHA92a02594f52192d7eaae48789c973f7902e3757d8478a140985c3b512183dd12 giữ đủ375codes/catalog/order; exact-decode trước validator/evidence/subject/time/quality gate. Riêng OpenRouter Gemma gửi wire contract trong prompt, không gửi strict schema unsupported; Nemotron có JSON Schema profile riêng bên dưới. Unknown/conflict/uncertain/urgent vẫn chặn Top3; min2present vẫn provisional. Strict JSON tại provider không chứng minh đúng ngữ nghĩa. Không đổi wire constraints theo phỏng đoán khi chưa nhận lỗi cụ thể.

### Qualification: chọn MỘT cấu hình, chạy đúng một lần

Dùng interpreter .venv-web đã chọn ở mục1 và storage root thực ở mục2. Không gửi web chat đồng thời. Mỗi provider tối đa2generation requests trong lượt qualification này; chọn một Gemini model, không chạy cả3.8vàLite để tăng số lần thử. Chạy không có --allow-live-diagnostic chỉ kiểm prerequisites/metadata, **0requests**.

Ứng viên Gemini nhẹ (chỉ thực hiện khi chủ động cho phép live và đã có quyền):

```powershell
$env:DISEASE_LLM_PROVIDER = 'gemini'; $env:DISEASE_LLM_MODEL = 'gemini-3.5-flash-lite'
$GeminiSecret = Read-Host 'Gemini API key' -AsSecureString
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new('', $GeminiSecret).Password
$env:DISEASE_GEMINI_LIVE = '1'
& $ApiPython -B -m scripts.smoke_local_mvp --provider-qualification --allow-live-diagnostic --timeout-seconds 60
```

Groq là lựa chọn riêng có chủ đích, không phải request tự động sau Gemini lỗi:

```powershell
$env:DISEASE_LLM_PROVIDER = 'groq'; $env:DISEASE_LLM_MODEL = 'openai/gpt-oss-20b'
$GroqSecret = Read-Host 'Groq API key' -AsSecureString
$env:GROQ_API_KEY = [System.Net.NetworkCredential]::new('', $GroqSecret).Password
$env:DISEASE_GROQ_LIVE = '1'
& $ApiPython -B -m scripts.smoke_local_mvp --provider-qualification --allow-live-diagnostic --timeout-seconds 60
```

Key nhập ẩn, không lưu source/.env/notebook/frontend hoặc gửi trong chat. Các biến thuộc terminal hiện tại. Endpoint cố định, no redirects để tránh chuyển credential. Đổi env/provider cần Ctrl+C và khởi động lại server theo mục3; health.chat.provider/model cho biết lựa chọn đã load. Startup/configured chưa chứng minh live readiness.

A dùng schema nhỏ `{ok:boolean}` với dữ liệu hư cấu; chỉ A completed/hợp contract mới gửi B. B dùng đúng câu **“Tôi ho và sốt từ sáng nay.”**, catalog375 và existing extraction/validator/gate, không gọi LR. Không retry, output≤2048/request, deadline60s/request. HTTP status/error đã che nhạy cảm, elapsed, response field-types/usage được báo; không raw response text/key/headers. Schema hợp lệ local không có nghĩa provider accepted.

A503/timeout/access/quota → dừng trước B, không sửa schema. A PASS/B400 → báo exact message và dừng; chỉ cân nhắc wire repair từ lỗi xác nhận. BHTTP200 nhưng parser/semantic/gate lỗi → báo stage cụ thể, không thay schema đang served. PASS qualification chỉ xác nhận extraction/vector trên một câu synthetic, **không** extraction accuracy hoặc full chat→LR Top3 live. Đánh giá ngữ nghĩa cần bộ ca cố định được người duyệt; không đổi ca theo model để làm đẹp kết quả.

Legacy --gemini-ab-diagnostic vẫn dùng Gemini đã chọn; từ chối nếu đang chọn Groq. --gemini-live có thể tối đa6calls, **không dùng trong qualification2calls**. Không chạy thêm lượt để tìm PASS; hết bước qualification thì dừng, full chat live cần scope riêng nếu đã dùng budget.

### Qualification Groq GPT-OSS 20B: ba bước, tối đa ba request

Đợt kiểm riêng này dùng `--groq-three-stage`, **không dùng lại A/B hai request ở trên**. Tài liệu [Groq API](https://console.groq.com/docs/api-reference) xác nhận endpoint Chat Completions; [Structured Outputs](https://console.groq.com/docs/structured-outputs) liệt kê `openai/gpt-oss-20b` hỗ trợ `json_schema`/`strict:true`. Điều này chưa xác minh quyền truy cập/quota của tài khoản.

A gửi đúng lời chào tiếng Việt ngắn, không schema/catalog/history/tools. A HTTP200 + completed + content không rỗng mới gửi B. B strict JSON `{intent:string,has_symptom:boolean}`, mọi field required/additionalProperties=false; parse và validate thành công mới gửi C. C dùng nguyên Groq adapter, wire schema375 và Python validator hiện tại với câu hư cấu “Tôi ho và sốt từ sáng nay.”; kiểm evidence/subject/time, gate, vector `(375,)`, đúng `cough`/`fever`, không feature thừa. Không gọi LR hoặc website trong đợt này.

Mọi lỗi, kể cả timeout, đều tính một request và dừng ngay; **retry0, tối đa3 tổng cộng**, không tự đổi schema/model/provider. Output tối đa2048 tokens/request, input JSON UTF-8 tối đa32768 bytes gồm schema/catalog; admission bound bảo thủ33792 tokens gồm phần dự phòng envelope, không phải usage/billed cost đo được. Chỉ hiển thị usage do Groq trả; billed cost để unknown nếu không được cung cấp. Deadline60s/request. Không lưu raw response, key hoặc headers.

Agent preflight hiện **BLOCKED, 0 generation requests** vì process không có key/live opt-in. Offline regression **295 PASS**, một cảnh báo TestClient deprecation. A/B/C live, strict schema acceptance và extraction validator thật đều **NOT VERIFIED**; mock PASS không thay thế live evidence.

Để owner chạy một lần: mở PowerShell tại project root, **Ctrl+C server đang chạy và không gửi web chat**. Lệnh sau tạo process con, chỉ chọn Groq trong process đó; không đổi config/default hoặc environment của terminal website. Nếu key chưa có, nhập ẩn tại terminal, không gửi vào chat:

```powershell
powershell -NoProfile -Command {
    if ([string]::IsNullOrWhiteSpace($env:GROQ_API_KEY)) {
        $GroqSecret = Read-Host 'Groq API key' -AsSecureString
        $env:GROQ_API_KEY = [System.Net.NetworkCredential]::new('', $GroqSecret).Password
    }
    $env:DISEASE_LLM_PROVIDER = 'groq'
    $env:DISEASE_LLM_MODEL = 'openai/gpt-oss-20b'
    $env:DISEASE_GROQ_LIVE = '1'
    $env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
    & '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --groq-three-stage --allow-live-diagnostic --confirm-no-web-requests --timeout-seconds 60
}
```

`--confirm-no-web-requests` là xác nhận của operator rằng website đã dừng, không phải script tự kiểm soát quota của các process khác. Chạy **đúng một lần**, gửi JSON output để đối chiếu; không chạy lại để ép PASS. Nếu A/B lỗi, các bước sau phải NOT RUN. C PASS chỉ cho phép đề xuất **KEEP AS CANDIDATE**, chưa bật Groq production, chưa chứng minh accuracy/stability/quota hoặc live chat→LR Top3.

### OpenRouter free Gemma — JSON mode, qualification riêng (2026-10-31)

**IMPLEMENTED / OFFLINE PASS / LIVE NOT VERIFIED.** [Model page](https://openrouter.ai/google/gemma-4-26b-a4b-it:free) ghi hỗ trợ response_format cho JSON, không JSON-schema enforcement. [Public endpoint metadata](https://openrouter.ai/api/v1/models/google/gemma-4-26b-a4b-it:free/endpoints) hiện quảng bá response_format trên route free; đây không phải kiểm quyền/quota/key hoặc acceptance thật của tài khoản owner. [Chat Completions](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion) dùng Bearer key, messages, max_tokens, stream=false, choices/message/content. Không dùng Groq max_completion_tokens hoặc json_schema/strict=true cho route này.

Đợt Gemma chỉ nhận model chính xác `google/gemma-4-26b-a4b-it:free`; Nemotron có qualification riêng bên dưới, không phải fallback. Không nhận paid variant bỏ suffix, router tự chọn model, hoặc danh sách fallback. Body đặt `provider.allow_fallbacks=false`, `require_parameters=true`, `max_price={prompt:0,completion:0,request:0}` theo [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection). Nếu route không hỗ trợ tham số/điều kiện này thì dừng, không âm thầm bỏ yêu cầu JSON hoặc chuyển sang paid. Không bật default, không đổi Gemini/Groq config. HTTP/JSON response được kiểm đúng model, finish_reason=stop, không refusal/tool calls/error envelope, rồi exact-decode375 codes và validator canonical hiện có.

Wire contract đầy đủ nằm trong `output_contract` của prompt. `response_format={"type":"json_object"}` chỉ yêu cầu JSON object, **không bảo đảm đúng schema hoặc ngữ nghĩa**. Unknown feature/field thừa/evidence/subject/time/conflict vẫn bị Python từ chối; denied/uncertain không chuyển thành present. LR tuned C=2 và mapping587 không đổi; OpenRouter không tạo bệnh/Top3/percentages.

Offline regression **355 PASS**, một TestClient deprecation warning. Có test HTTP transport giả lập, no retry/fallback/paid model, parse/error/size bounds, negative/uncertain/unmapped/context, session reset/expiry/stale vector và backend provider factory dùng chung. Existing Gemini/Groq/API regression PASS. Đây là cơ chế mock; chưa chứng minh khả năng extraction tiếng Việt của model. FastAPI/OpenRouter live và website→LR thật vẫn **NOT VERIFIED**; Phase6 chỉ tiếp tục sau A/B/C live PASS và authorization riêng cho web.

Agent preflight thực trên Windows Python3.13.17: key=false/live=false/opt-in=false, requests_used=0. A/B/C **NOT RUN**, HTTP và latency không có. Không đọc key từ terminal/server khác hoặc yêu cầu gửi key vào chat. Không đổi output/schema để ép PASS, không gọi LR trong qualification.

Chạy đúng một lượt trong PowerShell tại project root, sau khi **Ctrl+C server và không gửi web chat**. Lệnh process con chỉ thay provider trong process chẩn đoán, không sửa environment/default của terminal website. Nếu chưa có key trong process con, nhập ẩn:

```powershell
powershell -NoProfile -Command {
    if ([string]::IsNullOrWhiteSpace($env:OPENROUTER_API_KEY)) {
        $OpenRouterSecret = Read-Host 'OpenRouter API key' -AsSecureString
        $env:OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new('', $OpenRouterSecret).Password
    }
    $env:DISEASE_LLM_PROVIDER = 'openrouter'
    $env:DISEASE_LLM_MODEL = 'google/gemma-4-26b-a4b-it:free'
    $env:DISEASE_OPENROUTER_LIVE = '1'
    $env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
    & '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --openrouter-three-stage --allow-live-diagnostic --confirm-no-web-requests --timeout-seconds 60
}
```

Không dùng generic --provider-qualification hai bước hoặc --gemini-live cho đợt này. **Tối đa3 generation requests tổng cộng, retry0, stop-on-first-failure**; lỗi/timeout cũng trừ lượt. Không chạy lại để tìm PASS. Input JSON gồm catalog/contract tối đa32768 UTF-8 bytes, admission bound bảo thủ33792 tokens không phải usage/billing; output2048/request, deadline60s/request. Production giữ deadline20s và budget/limits cũ. Script chỉ in sanitized status/time/usage/validator results, không raw response/auth headers/key; cost unknown nếu không có bằng chứng billing.

| Bước | Điều kiện PASS trước khi đi tiếp |
|---|---|
| A text, không schema/catalog/history/tools | HTTP200, completed, content không rỗng |
| B JSON object nhỏ intent/has_symptom | HTTP200, strict JSON parser + Python schema nhỏ, không extra field; không gọi là schema enforcement từ provider |
| C nguyên adapter/extraction contract | Câu hư cấu “Tôi ho và sốt từ sáng nay, nhưng không đau đầu.”: cough/fever present, headache denied, evidence/subject/time valid, gate PASS; vector375 chỉ hai feature present=1, headache=0 |

Gửi JSON output sau lượt chạy để đối chiếu A/B/C, HTTP/latency, json_mode_acceptance/extraction_validator và feature codes. C HTTP200 hoặc JSON hợp lệ mà validator/gate fail vẫn **không PASS**. Không gọi fitted LR, không mở split CSV/test, không model-generated Top3. Sau A/B/C PASS mới chuẩn bị riêng test web với approved real LR và owner chọn provider cho server; không tự đổi default hoặc coi end-to-end live đã PASS.

Đợt này chỉ sửa adapter/orchestration/tests/guide, không tạo ZIP mới hoặc publish source lên Drive. Code ZIP ngày2026-10-30 giữ nguyên SHA và không tự nhận OpenRouter adapter mới; source local hiện hành là nơi chứa thay đổi.

### OpenRouter HTTP429 — kiểm toán bằng chứng, không gọi lại generation

**UNRESOLVED về nguồn giới hạn.** Owner cung cấp: A HTTP429 khoảng2144,83ms, message `Provider returned error`,1/3request; B/C NOT RUN. Không tìm thấy qualification packet/log tương ứng trong workspace; Getdata.ipynb hiện0bytes. Đây là evidence do owner báo, không phải phép đo live mới của agent. Metadata đã báo `is_free_tier=true`, `usage_daily=0`; không có số request còn lại. Không gọi authenticated GET hoặc generation trong nhiệm vụ diagnostic này.

Collector cũ đọc body từ HTTPError rồi chỉ giữ status/message, đóng response; không thu thập error.code/metadata/Retry-After/rate-limit headers. Message chung trên là message đã nhận, không phải client tự thay bằng nội dung mới. Các trường cũ **NOT RECORDED**, không biết upstream có gửi hay không và không được dựng lại. A chưa gửi schema nên lỗi429 này không chứng minh schema375 bị từ chối.

Theo [error contract](https://openrouter.ai/docs/api_reference/errors-and-debugging), error.code/message/metadata giúp phân loại. [Limits](https://openrouter.ai/docs/api_reference/limits) phân biệt platform429 và upstream429; provider_code là mã gốc khi có, X-RateLimit-* là manh mối platform. Provider name đơn lẻ hoặc header đơn lẻ chỉ LIKELY; thiếu/conflict thì UNRESOLVED. Không suy “hết quota” hoặc “provider quá tải” từ generic429. [GET /api/v1/key](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key): usage_daily đo credits trong ngày UTC, không số request; nếu có free_model_daily_requests thì dùng used/limit/remaining để kiểm chính sách free, không thay cho RPM/upstream counters. Không dùng deprecated rate_limit để suy quota. Key credit/budget fields cũng không phải free-request counter. Bản metadata owner cung cấp chưa đủ phân biệt account, key policy, free model hay upstream.

Instrumentation mới **chỉ OpenRouter**: bounded code/message, metadata allowlist provider_name/provider_code/error_type/limit_source/reason với giá trị machine/public-name được duyệt; Retry-After dạng số/HTTP-date, X-RateLimit-Limit/Remaining/Reset dạng số. Không đoán đơn vị reset. Raw metadata, flagged_input, request, full headers/cookie/Authorization/URLs không được giữ. Unknown provider names/codes bị bỏ thay vì log text tùy ý. CONFIRMED trong classifier chỉ nghĩa nguồn được metadata response chỉ rõ, không phải đã kiểm tài khoản độc lập. Chatbot error response an toàn, Gemini/Groq collector contract, model/default/schema/gate giữ nguyên. **376 offline tests PASS**, một cảnh báo TestClient; generation requests mới **0**, authenticated GET mới **0**.

Bước nhỏ nhất: lấy các counter an toàn từ metadata owner đã có trước; nếu vẫn thiếu bằng chứng, cần **owner chấp thuận riêng** mới chạy probe sau. **Không chạy lệnh này trong nhiệm vụ hiện tại**, không chạy lại A/B/C ba request để chữa429. Probe mới tối đa1generation request text hư cấu, timeout60s, retry0/fallbackfalse, giữ đúng model free và price cap0. Nó không gửi schema, không chạy B/C, không gọi LR; HTTP200 chỉ chứng minh availability lúc đó, không extraction/chat PASS. Key phải sẵn trong environment của terminal, không gửi key vào chat:

```powershell
powershell -NoProfile -Command {
    $env:DISEASE_LLM_PROVIDER = 'openrouter'
    $env:DISEASE_LLM_MODEL = 'google/gemma-4-26b-a4b-it:free'
    $env:DISEASE_OPENROUTER_LIVE = '1'
    $env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
    & '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --openrouter-429-diagnostic --allow-live-diagnostic --confirm-no-web-requests --timeout-seconds 60
}
```

Chỉ sau approval, Ctrl+C server trước khi chạy probe và không gửi web chat đồng thời. Không có key thì probe dừng0requests. Retry-After được ghi để operator xem, không tự sleep/retry. Không đổi model, mua credits, tăng quota hoặc relax routing chỉ dựa trên lỗi chưa rõ nguồn. Gemini/Groq/OpenRouter extraction live và chat→LR vẫn NOT VERIFIED; không tạo ZIP hoặc báo cáo Markdown mới.

### Qualification NVIDIA Nemotron 3.5 Super VL free (2026-10-31)

Owner cho phép qualification riêng, **không chọn lại production default**. [Public endpoint metadata](https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-super-vl:free/endpoints) xác nhận exact ID `nvidia/nemotron-3.5-super-vl:free`, upstream được quảng bá `Nvidia`/tag `nvidia`, giá prompt/completion0 và supported_parameters có response_format/structured_outputs/reasoning. [Model page](https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free) xác nhận JSON Schema trong response_format. Đây không phải account availability hoặc kết quả live; counter used0/limit50/remaining50 do owner báo chỉ đúng thời điểm đã kiểm, không suy quota hiện tại.

Khai báo trước B/C: `response_format.type=json_schema`, `json_schema={name,strict:false,schema}`. Metadata không xác nhận native strict guarantee riêng cho route, nên không gửi strict=true hoặc coi JSON Schema là guaranteed enforcement; [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs) nêu enforcement tùy endpoint. Không tự downgrade sang json_object/text sau lỗi. C gửi nguyên wire schema375 SHA92a02594f52192d7eaae48789c973f7902e3757d8478a140985c3b512183dd12, exact code mapping và canonical Python validator/gate cũ. Nếu schema bị từ chối, ghi lỗi và STOP, không sửa contract.

Request A dùng đúng system **“Trả lời ngắn gọn bằng tiếng Việt.”**, user **“Xin chào. Hãy trả lời bằng một câu ngắn.”**, không schema/catalog/history/tools. B schema nhỏ intent:string/has_symptom:boolean, required cả hai và additionalProperties=false; phải parse/validate Python. C cùng câu synthetic “Tôi ho và sốt từ sáng nay, nhưng không đau đầu.”: cough/fever present, headache denied/0, exact evidence/subject/time, đủ375 chiều/canonical order. Không gọi LR hoặc tạo bệnh/Top3.

Để giữ budget output nhỏ, cả ba request khai báo `reasoning.enabled=false` từ đầu, theo [reasoning controls](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens). Không coi exclude reasoning là tắt reasoning. Parser chỉ dùng message.content, không dùng reasoning/reasoning_details làm JSON, không strip think-tags để chữa output. Reasoning-only/empty content, finish_reason length/content_filter hoặc malformed JSON đều FAIL. Nếu server vẫn trả reasoning riêng, chỉ ghi boolean/counters khi có, không nội dung reasoning. max_tokens2048/request, timeout60s, input cap32768UTF-8 bytes; reasoning tokens nếu server dùng vẫn có thể chiếm output budget, không hứa latency/success.

OpenRouter adapter chỉ thêm profile fixed free Nemotron, giữ Gemma JSON mode/Gemini/Groq/default nguyên trạng. Không paid slug, fallback, plugins, model list hoặc retry. Preflight agent: **key NO, live opt-in NO; actual generation requests0; A/B/C NOT RUN**. JSON Schema acceptance/native strict, actual returned model/upstream, Python validator trên live response, feature codes/vector thực và web→LR đều **NOT VERIFIED**. Upstream Nvidia nói trên là metadata công khai, không giả là provider đã phục vụ một request của owner. Regression **406 offline tests PASS**, một TestClient warning; mock PASS không là live extraction quality. Không tạo ZIP/publish source/đổi Drive hay scientific artifact.

Chạy **đúng một lượt**, tại PowerShell project root có OPENROUTER_API_KEY trong environment. Ctrl+C server và không gửi web chat đồng thời. Process con không đổi provider của terminal website; không paste key vào code/chat:

```powershell
powershell -NoProfile -Command {
    $env:DISEASE_LLM_PROVIDER = 'openrouter'
    $env:DISEASE_LLM_MODEL = 'nvidia/nemotron-3.5-super-vl:free'
    $env:DISEASE_OPENROUTER_LIVE = '1'
    $env:DISEASE_API_STORAGE_ROOT = (Get-Location).Path
    & '.\.venv-web\Scripts\python.exe' -B -m scripts.smoke_local_mvp --nemotron-three-stage --allow-live-diagnostic --confirm-no-web-requests --timeout-seconds 60
}
```

Tối đa3generation requests tổng, một mỗi A/B/C, failed/timeout cũng trừ lượt, stop-first-failure. Không dùng mode Gemma/Groq hoặc chạy lại để tìm PASS. Gửi nguyên JSON output đã lọc sau một lượt; records có requested model, actual_response_model/upstream_provider nếu API có, status/time/usage, schema/validator và vector. Thiếu key hoặc opt-in thì dừng0requests. C PASS chỉ KEEP AS CANDIDATE trên ví dụ này; triển khai website với real LR cần quyết định/kiểm thử riêng, chưa end-to-end live PASS.

**Evidence owner gửi sau qualification:** dùng đủ3/3request, retry0. A HTTP200/PASS ~1153,09ms, B HTTP200/PASS/Python schema valid ~721,85ms; cả hai trả đúng free model và upstream Nvidia. C HTTP200 ~643,66ms nhưng FAIL unexpected_response_model, model/provider không được ghi, usage unknown, validator chưa chạy. Chỉ xác minh được basic access và small-schema request; C375/native enforcement/chat→LR vẫn NOT VERIFIED. Không chạy lại trong budget đã hết.

Kiểm source phát hiện instrumentation kiểm model trước error envelope trong qualification transport. Do đó response dạng `{error:...}` kèm HTTP200 nhưng không model có thể bị báo nhầm model mismatch; đây là bug logic được kiểm bằng fixture, **chưa chứng minh C thực tế có envelope đó**. Đã sửa orchestration để lọc error envelope trước identity guard, giữ riêng HTTP status và body error.code/message/metadata đã che, thêm presence booleans thay raw dump; không nới identity/schema hoặc đổi model. **409 offline regression tests PASS**, một TestClient warning;0request live mới. Không khôi phục được body C cũ từ output đã gửi; chỉ có thể phân tích offline nếu response gốc đã được lưu. Chưa có C375 PASS hoặc website live PASS.

### Lỗi production, usage và retry

BoundedProvider (giữ alias BoundedGemini cho caller cũ) dùng cùng budget20requests/process,6/phút,output2048,cap64000bytes và100000admission units. Production và qualification hiện **retry0**, không cross-provider fallback. Base adapter có bounded retry cùng provider; wrapper tắt để một generate tương ứng một request trong ngân sách hiện hành.

Thiết kế nếu sau này duyệt bật production retry: tối đa1retry cho503/429, backoff có jitter/Retry-After cap2s và deadline tổng; mọi attempt phải trừ request/rate/token budget. Không retry400/schema,401/403 hoặc model/permission errors; timeout không tự đổi provider. **Chưa bật chính sách retry mới** vì phải kiểm accounting theo attempt trước khi enable; qualification luôn0. Restart/new chat không phải cách vượt provider quota.

Provider unavailable/quota/auth/parse/validator lỗi → thông báo có kiểm soát, không Top3 giả hoặc stale prediction. Groq finish_reason khácstop/refusal/tool-call bị chặn; Gemini parser vẫn completed steps. Usage Groq prompt/completion/total được ánh xạ vào telemetry chung; reasoning chỉ ghi nếu provider thực trả. Thiếu counter/cost ghi unknown/null; không cộng reasoning hai lần vào billed cost hoặc biến byte reservation thành token bill.

**Kiểm mới:**272offline tests PASS (mock/synthetic, Python3.11.9 có sẵn),1TestClient warning; .venv-web3.13.17 import/config/preflight PASS nhưng thiếu pytest, không cài thêm. Bộ tests: test_provider_selection.py + test_phase5b.py + test_local_chat.py + test_prediction_api.py. Các plan Gem3.8/Lite3.5/Groq20b đều BLOCKED/A-B NOT RUN/requests0 khi key/opt-in thiếu. HTTP/validator live chưa có cho Lite/Groq; original Gemini schema vẫn NOT VERIFIED. Checkpoint Windows/API PASS là bằng chứng độc lập trước đây, không là live chatbot PASS.

<a id="colab-runtime"></a>
## 5. Colab/Drive cho notebooks

Cấu hình từ [runtime.json](../configs/runtime.json): canonical root `/content/drive/MyDrive/ML_Projects/disease-prediction-ml`, source runtime `/content/disease-prediction-ml-runtime`, cache `/content/disease-prediction-ml-cache`. Drive source là bản publish nhỏ từ Windows; không phải source phát triển chính. Không dùng Windows D: trong remote kernel.

1. [Publish toàn payload](HANDOVER_GUIDE.md#source-publish) khi code/runtime đổi; không upload .py rời hoặc code ZIP.
2. VS Code chọn Colab kernel. Chạy **Colab: Mount Google Drive to Server...** và snippet được extension hỗ trợ. Colab browser dùng cơ chế mount browser; không giả định mọi remote Jupyter hỗ trợ drive.mount.
3. Restart Kernel sau source update. Điền digest từ stage/publish **local** vào EXPECTED_RUNTIME_PAYLOAD, không tự lấy expected từ Drive đang kiểm.
4. Shared bootstrap đọc `DRIVE_ROOT/src/data/colab_runtime.py`, verify source/config/scripts rồi copy/import từ ROOT trên VM. Smoke/06 tạo session riêng qua ColabTraining.open(RUNTIME); sau reset phải setup/session lại.
5. Audit helpers dùng `ROOT/scripts/`, không upload từng script. Nếu thiếu dependency, cài có chủ đích các requirements đã cung cấp, Restart Kernel; bootstrap không tự cài/mount/download.

Chỉ chạy smoke/setup/import/integrity để kiểm hạ tầng, **không Run All03/04/06**. Historical Colab A/B/C PASS không phải clean-room PASS cho publisher/release mới. Xem [bằng chứng và giới hạn](DEVELOPMENT_LOG.md#compatibility-handover).

## 6. Kiểm thử và troubleshooting

Offline regression có mock/synthetic fixtures, không gọi Gemini, fit model hoặc mở locked test:

```powershell
py -3.11 -B -m pytest -q -p no:cacheprovider tests/test_provider_selection.py tests/test_phase5b.py tests/test_local_chat.py tests/test_prediction_api.py
```

Bộ provider/API regression hiện tại272PASS/1TestClient deprecation warning trên Python3.11.9 có pytest sẵn; tests dùng mock/synthetic, không deserialize model thật trên3.11. Production LR vẫn dùng .venv-web3.13.17. Venv này chưa có pytest, không tự cài dependency trong nhiệm vụ. Số225PASS của đợt trước là lịch sử; không chạy full legacy data suite hoặc inference để kiểm provider.

| Dấu hiệu | Phân biệt và xử lý |
|---|---|
| environment_mismatch | Sai Python/dependency/OS/checkpoint scope; dùng môi trường đã duyệt, không sửa guards |
| missing artifact hoặc checksum mismatch | Kiểm đủ7file/root/quyền/source identity; dừng, không fallback/retrain |
| health503 | Đọc JSON error; server vẫn có thể phục vụ UI, chưa có ML readiness |
| live_opt_in_or_api_key_missing, requests0 | Thiếu env trong process hiện tại; chưa gửi request, không phải provider từ chối |
| HTTP400 | Chỉ kết luận request/schema khi có message/status thực đã che nhạy cảm; không bỏ feature để tạo PASS |
| HTTP401/403/404/429 | Lần lượt kiểm authentication/access/model/quota; không suy từ UI configured |
| Provider HTTP503 high demand | Dịch vụ tạm bận theo message; không auto retry hoặc coi là schema PASS |
| timeout, không headers | Ghi timeout/trace; không tự suy overload, quota hoặc schema |
| completed nhưng invalid JSON/extraction | Parser/validator failure riêng, không chuyển vector hoặc dùng stale Top3 |
| winerror10048 | Port đã có server; Ctrl+C server cũ hoặc chủ động dùng port khác |
| favicon404 | Không có favicon, không giải thích chat503 |
| thiếu src/session trên Colab | Mount/root/publish/digest/Restart/setup; không pip install src hoặc Run All training |
| bootstrap unexpected keyword | Source Drive cũ so với notebook; publish đủ payload đã kiểm, không bỏ digest validation |

Các lỗi live được tóm lược ở [nhật ký](DEVELOPMENT_LOG.md#8-gemini-extraction-và-conversation-management); [Google troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting) là nguồn tham chiếu đã dùng trong debug, không bằng chứng live tài khoản. Không public hosting/ngrok trong workflow này.


## Offline policy và xử lý dau co — cập nhật 2026-11-02

Restart server local để nạp code/config mới; lệnh chạy ở mục3a giữ nguyên. Không cần cài dependency, gọi API ngoài, publish Drive hoặc chạy notebook. Browser tiếp tục dùng endpoint/UI cũ; score label vẫn “Điểm mô hình (%)”.

Trong configs/phase5b.json:

- `offline.ask_when_present_at_most: 2`: khi thông tin ít, còn ứng viên và còn budget thì ASK, chưa gọi LR.
- `offline.question_priority`: fever, cough, headache, nausea; fallback `fallback_to_display_catalog: true` chọn các display Việt hợp lệ chưa hỏi/chưa biết trong schema gốc. Không dùng coefficients/scores để dẫn dắt.
- `conversation.max_clarification_turns: 2`: budget chung đã có, gồm cả disambiguation; không reset budget theo từng câu trả lời.
- `conversation.min_present_features: 2`: safety gate gốc giữ nguyên. Unknown/denied/uncertain không được tính là present. Unknown collision/conflict chưa giải quyết vẫn chặn.
- `offline.debug_logging: false`: chỉ bật true khi cần structured diagnostics. Sau restart, log JSON có hash session/action/reason/count/budget/pending/selector, có scores chỉ sau prediction; không chứa nội dung chat/feature/label/key. Không dùng debug logs làm clinical evidence.

Ví dụ đã kiểm qua HTTP với LR thật, synthetic và không ground truth:

| Người dùng | Bot / quyết định |
|---|---|
| Tôi bị sốt | Bạn có bị ho không? — ASK, LR calls=0 |
| có | Bạn có bị đau đầu không? — ASK, LR calls vẫn=0 |
| không | Hai present, một denied, hết hai câu hỏi: SHOW_LIMITED_RESULT, warning thông tin hạn chế; gọi LR đúng một lần |

Kết quả limited có reason `offline_limited_question_budget` hoặc `offline_limited_no_eligible_question`. Không phải dấu hiệu bệnh đã đáng tin cậy. Nếu chỉ còn một present hoặc có ambiguity/conflict thì không có Top3, dù hết budget. Ngưỡng đếm là policy provisional, không phải cutoff calibration, không bảo đảm model score sẽ cao hơn sau vài câu hỏi.

| Người dùng | Bot / state |
|---|---|
| dau co | Bạn muốn nói đau cơ hay đau cổ? — REQUEST_CLARIFICATION; chưa gán feature |
| cái thứ hai | Chỉ neck pain=present; hỏi sốt; chưa đủ gate |
| không | fever=denied, hết budget và chỉ một present: abstain; không LR |

Có thể trả lời “đau cơ”/“đau cổ” hoặc “cái đầu”/“cái thứ hai”. Với “Tôi không dau co”, lựa chọn đau cổ giữ neck pain=denied, không gán cả hai. “Tôi bị dau co và sốt” giữ sốt nhưng chưa gán nghĩa của dau co. Câu pha dấu được xét theo từng cụm. Câu lạc đề/không rõ, thiếu display dịch hoặc không đủ budget có thể kết thúc không có dự đoán.

Báo cáo synonyms cũ nay thêm missing_display_vi, untranslated_display_placeholders, dangerous_short_aliases, coverage_percent. Hiện 45/375 feature có aliases_vi (12%), 330 thiếu; 0 display rỗng nhưng 330 display còn placeholder tiếng Anh, không dùng để hỏi bằng tiếng Việt. Một collision dau co, năm alias ngắn cần review (ho, non, oi, sot, met), 375 needs_review=true. Fuzzy matching vẫn tắt; không thêm alias không dấu hoặc tự gộp feature để giải collision. Chạy `python -B -m scripts.build_synonyms_report` bằng interpreter đã cấu hình để lấy danh sách đầy đủ.

Tính tương thích LLM/ML không đổi: chế độ llm dùng policy cũ; LR source pins/checkpoint/schema/mapping/fitted preprocessing giữ nguyên. Không tạo ZIP mới; code release cũ chưa chứa sửa đổi này.


## Câu hỏi sức khỏe chưa hỗ trợ và tên bệnh — 2026-11-02

Restart server sau cập nhật code/config, giữ DISEASE_CHAT_MODE=offline. Không cần API key, cài thêm dependency, chạy notebook hay đổi Drive.

Các câu “ngực tôi có khối u thì bị bệnh gì”, “tôi lo mình bị ung thư vú”, “tôi có bầu không” nay trả status unsupported_health, không Top3. Bot giải thích chưa xác định đầy đủ triệu chứng phù hợp, chỉ dự đoán trong 587 nhãn và không khẳng định/loại trừ bệnh khác; gợi ý mô tả triệu chứng thực hoặc tìm tư vấn y tế phù hợp khi có bất thường/triệu chứng đáng lo. Không tự chẩn đoán cancer/pregnancy. Urgent guard vẫn ưu tiên cấp cứu. “Tôi ho và lo mình bị ung thư vú” giữ cough present nhưng phần chưa hỗ trợ chặn dự đoán. “Hôm nay ngày mấy”, “quả trứng hay con gà có trước”, “asdf” vẫn out_of_scope. Keywords/patterns cấu hình tại offline.health_keywords/health_body_terms/health_question_patterns; detector không bổ sung feature.

Tên bệnh nằm trong configs/disease_names_vi.json, keyed bằng exact canonical label của label_mapping587. Hiện có 587 entry, 0 reviewed, 587 needs_review, 0 missing entry; chỉ 5 display Việt nháp, 582 entry giữ tên Anh. Không tự bật reviewed. Người có chuyên môn cần kiểm nghĩa/thuật ngữ, sửa display_vi nếu cần rồi mới chủ động đặt needs_review=false cho đúng entry đã duyệt. Không sửa class IDs, label mapping, checkpoint hay tên canonical để dịch UI. Nếu dictionary không có file/entry hoặc chưa review, ứng dụng dùng nhãn gốc và cảnh báo; model loader vẫn giữ guards riêng.

`python -B -m scripts.build_synonyms_report` bằng interpreter đã cấu hình nay có disease_translations với reviewed/needs_review/missing/draft_vi/invalid_canonical_keys. Đây là coverage file, không phải độ chính xác dịch. Bộ test kiểm ưu tiên tên Việt bằng fixture giả lập reviewer, không gán cờ review cho dữ liệu thật.

Presentation config: presentation.SCORE_DECIMALS=4. JSON top3.score_percent vẫn nguyên giá trị; field presentation.top3.score_text dùng để hiển thị nhất quán trên card, terminal và state_summary.top3_display. Label canonical vẫn có trong API. Không nhân100 hai lần/renormalize/round trước policy. Ví dụ synthetic checkpoint thật (không ground truth):

| Canonical label hiện chưa review | Raw score_percent | Text hiển thị |
|---|---:|---:|
| oral mucosal lesion | 5.12045687095984 | 5.1205% |
| conjunctivitis due to virus | 3.83870108406369 | 3.8387% |
| teething syndrome | 3.5800069472765097 | 3.5800% |

Khi entry được review thực, card thay tên hiển thị bằng display_vi; label API và score giữ nguyên. Test fixture có nhãn Việt minh họa và 40.0000%/30.0000%/10.0000%, không phải kết quả hoặc bản dịch y khoa thật. Điểm luôn là “Điểm mô hình (%)”, không phải xác suất mắc bệnh. Finite validation chặn NaN/Infinity ở backend và frontend. Không có browser visual acceptance mới; đã kiểm HTTP/static và formatter/contract offline.


## Hiển thị bản dịch tham khảo cho đồ án — quyết định hiện hành 2026-11-02

Theo phạm vi môn học, cho phép hiển thị bản dịch nháp thay vì chờ chuyên gia duyệt mọi nhãn. presentation.ALLOW_DRAFT_TRANSLATIONS=true trong configs/phase5b.json điều khiển rõ ràng việc này. Đặt false để trở lại chỉ hiển thị bản dịch đã duyệt cho dự án. Không đổi min2 gate, question budget, urgent guard, model hoặc probability.

configs/disease_names_vi.json có đủ 587 khóa canonical: 583 tên Việt, gồm 3 tên đã được phụ trách đồ án chấp thuận hiển thị và 580 bản dịch tham khảo needs_review=true. Không mục nào được tự nhận là đã được chuyên gia y tế rà soát. Bốn nhãn giữ tiếng Anh và có translation_note vì nguồn chưa rõ: benign paroxysmal positional vertical (bppv), chronic rheumatic fever, nonalcoholic liver disease (nash), threatened pregnancy. Không tự sửa vertical thành vertigo, NASH thành bệnh cụ thể hơn hoặc threatened pregnancy thành dọa sẩy thai.

Presenter trả translation_status=draft cho bản nháp đã cho phép hiển thị; frontend/terminal dùng display_label, kèm cảnh báo: “Tên tiếng Việt là bản dịch tham khảo cho đồ án, chưa được chuyên gia y tế rà soát.” Cảnh báo này cũng áp dụng ba tên được duyệt hiển thị bởi phụ trách đồ án vì đó không phải chuyên gia y tế. Tên Anh vẫn nằm trong top3.label/canonical_label và title của card; class IDs/order/score_percent giữ nguyên. Điểm hiển thị vẫn bốn chữ số, không renormalize.

Dừng server cũ bằng Ctrl+C rồi chạy lại lệnh Uvicorn ở mục3a để nạp dictionary/config. Refresh trình duyệt; nếu JS cũ còn mở, Ctrl+F5. Không cần tạo lại ZIP, tải dataset hay chạy notebook. Code ZIP cũ chưa chứa cập nhật này. Báo cáo synonyms hiện có cũng xuất danh sách draft_vi và original_label_fallback để tiếp tục rà soát nếu cần.


### Triệu chứng kèm từ mô tả và câu hỏi dự đoán

Bản sửa 2026-11-02 nhận đúng “tôi bị buồn nôn, ho và sốt nặng”: nausea/cough/fever đều present, không coi riêng “nặng” là symptom chưa hỗ trợ. Câu “tôi bị sốt và ho thì bị bệnh gì?” giữ hai feature và ASK theo budget, không trả unsupported_health do đuôi hỏi. Từ mô tả chỉ bỏ khỏi residual khi nằm ngay sau mention đã validate; không đổi schema/model, không phải đánh giá mức độ nặng nhẹ. Dấu hiệu urgent vẫn được kiểm trên toàn văn bản gốc trước đó; khối u/ung thư/mang thai/unknown symptoms vẫn không bị bỏ qua. Restart server local để nạp sửa đổi, không cần training/notebook, API ngoài hoặc cập nhật dataset.


<a id="academic-review--2026-11-11-python-entrypoint"></a>
<a id="three-model-website"></a>
## Website ba model — 2026-11-11

Hướng dẫn khởi động duy nhất nằm ở [README](../README.md#7-cài-đặt-và-chạy-thử): đặt storage root thực trong cùng terminal rồi chạy `python run_api.py` bằng `.venv-web` CPython3.13.17. Thư mục dữ liệu hiện tại là sibling `disease-prediction-ml-data`. Không tạo lại environment đang dùng, không đổi Python toàn cục và không cần Jupyter. `run_api.py` giữ localhost/1worker/no reload; dùng `--port 8001` nếu8000 đang được dùng.

| ID | Windows3.13.17 hiện tại | Output contract |
|---|---|---|
| `lr_tuned_c2` | ENABLED nếu đủ artifact; default không đổi | `top3`, nhãn/score thật từ predict_proba |
| `lr_baseline` | BLOCKED: runtime chưa có independent synthetic reference | Cùng LR Top3 khi qualify |
| `hard_tuned_lr_svc_knn` | BLOCKED: SVC/KNN thiếu independent reference | `result_kind=hard_vote_result`, nhãn và member votes; không Top3 |

`GET /api/v1/models` luôn liệt kê đủ ba IDs cùng `available`, reason, result_kind, artifact identities. Chỉ model available được chọn trên UI. `POST /api/v1/predict` nhận `model_id` tùy chọn; bỏ trường này giữ LR tuned cũ. Không fallback khi một model lỗi. `POST /api/v1/chat` nhận cùngID; reply phân biệt `requested_model_id` và `processed_model_id` (null khi chưa inference). Gửi session của model khác mà không reset trả409; reset loại context cũ và tạo phiên riêng. Mỗi model dùng dialogue store độc lập, vẫn chung extractor/validator/DecisionPolicy; không thay135aliases.

LR hiển thị “Điểm mô hình (%)”,4chữ số thập phân; raw scores giữ nguyên, không chuẩn hóa riêng Top3. Hard vote dùng engine `src.models.ensemble.hard_vote` đã khóa, uniform votes và ưu tiênLR→SVC→KNN khi ba nhãn khác nhau. UI chỉ nhãn thắng, phiếu và từng member; không hiển thị vote share như probability. Hai kiểu response tách bằng schema; hợp đồng LR cũ được giữ.

Qualification cô lập thực tế:4checkpoint hashes, identity/source pins, schema375, fitted318 và mapping587 PASS; synthetic8vectors và hardvote chạy thành công trên Windows. Tuy nhiên chỉ LR tuned có original Colab reference đã pinSHA để so toàn bộ8×587probabilities/exactlabels/Top3. Load thành công một pickle không đủ mở rộng allowlist: baseline/SVC/KNN vẫn BLOCKED trong production. Không bỏ guard hoặc tự thay model. Cần tạo reference độc lập trong môi trường gốc3.13.18 với cùng8vectors và cùng hashes, rồi đối chiếu tolerance rtol1e-10/atol1e-12 trước khi duyệt runtime thêm.

Lỗi `storage_not_configured` từ `/health`503 là thiếu biến môi trường trong serverprocess; dừng đúng server, đặt env rồi khởi động lại cùng terminal. Environment mismatch, missing artifact hoặc checksum mismatch phải dừng, không fallback. `/health` báo default model, registry báo trạng thái từng ứng viên. Offline không gọi LLM.

Kiểm thử vòng này:380targeted regressionPASS; actualChromium fixture UI1PASS ngoài sandbox (sandbox ban đầu chặn IPC); real LR tuned HTTP200 và clean extracted-data/current-source-overlay smokePASS. Không gọi hai comparator là real websitePASS khi chúng đang disabled. Không fullsuite claim, không clinical validation. Lệnh tái kiểm cơ chế:

```powershell
& 'D:\Program Files (x86)\Python\Python311\python.exe' -B -m pytest tests/test_three_model_web.py tests/test_prediction_api.py -q -p no:cacheprovider
& '.\.venv-web\Scripts\python.exe' -B -m scripts.qualify_web_models --storage-root . --output 'D:\new-output\windows-probe.json'
```

Lệnh thứ nhất dùng test interpreter hiện có, không phải môi trường loadcheckpoint; trên máy khác dùng testenv phù hợp. Đường output probe phải chưa tồn tại và nằm ngoài data. Probe không duyệt production tự động. Không gửi API key, không dùng locked test để kiểm web.


## Clean Git checkout — 2026-11-11

Clone source không có dataset/weights. Hai file schema/mapping nhỏ trong `artifacts/metadata/phase2` là fixture/identity đã khóa để unit tests hoạt động; không fallback model từ đó. Dùng [data identity manifest](../configs/external_data_release.json) và quy trình [handover Git](HANDOVER_GUIDE.md#git-migration-pc--github--laptop--2026-11-11). Sau setup Windows3.13.17/pinned requirements-api và external data, chạy `python run_api.py` bằng đúng .venv-web. `/health` và structured predict/chat kiểm synthetic, không đọc lockedCSV. Tham số DISEASE_API_STORAGE_ROOT cần cùng terminal khởi động server.

Developer tests dùng test interpreter phù hợp với requirements-dev; không cài pytest/notebook tooling vào production chỉ để chạy test. Không bật DISEASE_RUN_DATA_REGRESSION hoặc Run All notebooks khi đồng bộ máy. Publisher source hiện có vẫn có thể tạo lại `dist`; Git không ship generateddist. HaiZIP05 giữ nguyên và không được tự coi chứa commitGit mới.
