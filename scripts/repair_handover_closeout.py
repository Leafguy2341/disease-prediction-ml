"""Source-only maintenance of notebook06; never execute notebook or ML code."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def repair():
    path=ROOT/'notebooks/06_final_model_evaluation.ipynb'
    raw=path.read_bytes();notebook=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()=='f59a2d72b84c0051b4e7d972d4a23289611d76b04b80789018c499975bc9e948', 'Maintenance already applied or source differs; do not overwrite notebook'
    old=json.loads(raw)
    def source(index,text):notebook['cells'][index]['source']=text.splitlines(keepends=True)
    source(0,''.join(notebook['cells'][0]['source']).replace(
        '# 06 — Final locked-test evaluation (CHƯA THỰC THI)',
        '# 06 — Final evaluation closeout viewer (chỉ đọc kết quả đã hoàn tất)').replace(
        'Việc triển khai/default trong code chưa thay đổi.',
        'LR tuned C=2 là model ứng dụng đã được duyệt trước test.'))
    source(1,''.join(notebook['cells'][1]['source']).replace(
        'Default Run All là preparation only. Không thay `RUN_FINAL_LOCKED_TEST=False` hoặc authorization trống.',
        'Run All chỉ kiểm preflight và đọc completed evidence. Không đánh giá lại; gate luôn False và authorization rỗng.'))
    source(3,''.join(notebook['cells'][3]['source']).replace(
        'protocol, digest, preflight, evaluate, show_result, versions',
        'protocol, digest, preflight, namespace, read_completed, sha256_file, show_result, versions'))
    source(5,''.join(notebook['cells'][5]['source']).replace(
        'if prepared["execution_status"] != "NOT STARTED":',
        'if prepared["execution_status"] != "NOT STARTED" and not prepared["execution_status"].startswith("COMPLETED"):'))
    source(6,'''## 4. Closeout chỉ đọc — KHÔNG THỰC THI LẠI

Gate mặc định False, authorization rỗng. Nếu bật gate, notebook dừng ngay.
Chỉ đọc namespace đã khóa sau preflight PASS và xác minh SHA completed manifest.
Run chưa hoàn tất hoặc thiếu evidence không được tự resume/evaluate.
Không xóa execution marker; không deserialize, fit, predict hoặc mở CSV test.
''')
    source(7,'print("Closeout viewer: chỉ đọc completed evidence; không cấp hoặc in authorization thực thi.")\n')
    source(8,'''RUN_FINAL_LOCKED_TEST = False
OWNER_AUTHORIZATION = ""
if RUN_FINAL_LOCKED_TEST:
    raise RuntimeError("Closeout viewer only reads completed results; evaluation is disabled.")

EXPECTED_COMPLETED_MANIFEST_SHA256 = "f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a"
final_result = None
if globals().get("evaluation_api_ready", False) and prepared is not None and not any(r["status"] == "FAIL" for r in checks):
    try:
        completed_folder = namespace(session.paths.storage_root)
        completed_manifest = completed_folder / "manifest.json"
        if not completed_manifest.is_file():
            print("CHƯA CÓ completed results; chỉ preflight, không đánh giá hoặc tạo output.")
        else:
            completed_sha256 = sha256_file(completed_manifest)
            if completed_sha256 != EXPECTED_COMPLETED_MANIFEST_SHA256:
                raise ValueError("Completed manifest SHA-256 differs from approved closeout identity.")
            completed = read_completed(completed_folder)
            final_result = {**completed, "folder": str(completed_folder), "manifest_sha256": completed_sha256}
            checks.append(dict(check="Completed evidence replay", status="PASS", detail="Manifest và file checksums hợp lệ; không mở CSV test."))
    except Exception as exc:
        final_result = None
        checks.append(dict(check="Completed evidence replay", status="FAIL", detail=f"{type(exc).__name__}: {exc}"))
        print("BLOCKED completed evidence:", type(exc).__name__, str(exc))
else:
    print("SKIPPED completed replay: cần setup/preflight PASS; không dùng session hoặc result cũ.")
''')
    source(9,'''## 5. Metrics đã lưu và validation–test

Chỉ hiển thị completed evidence đúng checksum; không tính lại metrics hoặc chọn model.
Khi chưa có bundle hoàn tất, dừng ở preflight. Không tạo kết quả thay thế.
''')
    source(14,''.join(notebook['cells'][14]['source']).replace(
        'STOP: cần owner ủy quyền riêng cho protocol đã khóa; chưa có điểm test.',
        'STOP: closeout chỉ đọc; không tự đánh giá, cấp authorization hoặc tạo kết quả.'))
    # Preserve the historical diagnostic source as comments and every output/count.
    # These old cells used to deserialize/predict and copy a reference to Drive.
    for index in (15,16):
        source(index,'# Historical diagnostic source; disabled in the read-only closeout viewer.\n'+
            ''.join('# '+line for line in notebook['cells'][index]['source'])+
            '\nprint("Historical diagnostic cell disabled; no prediction, output write or Drive copy.")\n')
    assert [(c.get('outputs'),c.get('execution_count')) for c in old['cells']]==[(c.get('outputs'),c.get('execution_count')) for c in notebook['cells']]
    import ast
    tree=ast.parse('\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code'))
    forbidden={'evaluate','fit','predict','predict_proba','load_fitted_checkpoint','copy2','load_final_split'}
    assert not any(isinstance(n,ast.Call) and getattr(n.func,'attr',getattr(n.func,'id','')) in forbidden for n in ast.walk(tree))
    path.write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    receipt=dict(before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        outputs_and_counts_unchanged=True,notebook_executed=False,source_only=True,
        changed_cells=[i for i,(a,b) in enumerate(zip(old['cells'],notebook['cells'])) if a!=b])
    out=ROOT/'reports/handover_blocker_fix'
    out.mkdir(exist_ok=True)
    (out/'notebook06_closeout_source.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':repair()
