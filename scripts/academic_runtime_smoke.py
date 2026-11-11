"""Local-only real-checkpoint launcher verification on fictional inputs."""
import json
import os
from pathlib import Path
import runpy
import socket
import sys
import threading
import time
from contextlib import ExitStack
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def main():
    from src.models.ensemble import phase4_guard
    from src.agent import provider
    from scripts.academic_review import save
    import uvicorn
    import http.client
    from app.backend.prediction import LRPredictionService, _runtime_compatible
    from src.models.final_evaluation import protocol, versions
    from src.data.loader import sha256_file
    data = Path(os.environ.get('DISEASE_API_STORAGE_ROOT', ROOT.parent / 'disease-prediction-ml-data')).resolve()
    counters = dict(outbound_network=0, llm=0)
    holder = {}
    real_connect = socket.socket.connect
    def safe_connect(sock, address):
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1'}:
            counters['outbound_network'] += 1
            raise AssertionError('Outbound access forbidden')
        return real_connect(sock, address)
    def forbidden(*args, **kwargs):
        counters['llm'] += 1
        raise AssertionError('LLM forbidden')
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(32)
    port = listener.getsockname()[1]
    def serve(app, **kwargs):
        assert kwargs == dict(host='127.0.0.1', port=port, workers=1, reload=False), kwargs
        holder['server'] = uvicorn.Server(uvicorn.Config(app, **kwargs, log_level='error', access_log=False))
        holder['server'].run(sockets=[listener])
    failures = []
    def entry():
        try:
            runpy.run_path(str(ROOT/'run_api.py'), run_name='__main__')
        except BaseException as exc:
            failures.append(type(exc).__name__ + ': ' + str(exc))
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, DISEASE_API_STORAGE_ROOT=str(data), DISEASE_CHAT_MODE='offline'))
        stack.enter_context(patch.object(socket.socket, 'connect', safe_connect))
        for name in ('_post', '_post_groq', '_post_openrouter', 'create_provider'):
            stack.enter_context(patch.object(provider, name, forbidden))
        stack.enter_context(patch.object(sys, 'argv', ['run_api.py', '--port', str(port)]))
        stack.enter_context(patch.object(uvicorn, 'run', serve))
        # Guard both code and actual data storage. Predict is allowed, fit and test reads are forbidden.
        code_guard = stack.enter_context(phase4_guard(ROOT))
        data_guard = stack.enter_context(phase4_guard(data))
        thread = threading.Thread(target=entry, daemon=True)
        try:
            thread.start()
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if failures:
                    raise AssertionError(failures)
                if holder.get('server') and holder['server'].started:
                    break
                time.sleep(.05)
            assert holder.get('server') and holder['server'].started, 'Launcher did not start'
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=20)
            def request(method, path, body=None):
                payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
                conn.request(method, path, body=payload, headers={'Content-Type':'application/json'} if payload else {})
                response = conn.getresponse()
                raw = response.read()
                assert response.status == 200, (path, response.status, raw[:300])
                return json.loads(raw) if 'json' in response.getheader('Content-Type', '') else None
            health = request('GET', '/health')
            assert health['checkpoint_status'] == 'REAL CHECKPOINT VERIFIED'
            model_registry = request('GET','/api/v1/models')
            assert {r['model_id'] for r in model_registry['models']} == {'lr_tuned_c2','lr_baseline','hard_tuned_lr_svc_knn'}
            assert [r['model_id'] for r in model_registry['models'] if r['available']] == ['lr_tuned_c2']
            result = request('POST', '/api/v1/predict', {'present_features':['cough','fever']})
            assert len(result['top3']) == 3 and result['calibrated'] is False
            first = request('POST', '/api/v1/chat', {'message':'Tôi bị ngứa âm đạo.'})
            assert first['predictions'] is None and len(first['pending_questions']['items']) == 3
            followup = request('POST', '/api/v1/chat', dict(message='1 có, 2 có, 3 không',
                session_id=first['session_id'], batch_id=first['pending_questions']['batch_id']))
            assert followup['status'] == 'prediction_ready'
            another = request('POST', '/api/v1/chat', {'message':'Tôi bị ngứa âm đạo.'})
            preview = request('POST', '/api/v1/chat', dict(session_id=another['session_id'], action='preview'))
            assert preview['status'] == 'prediction_ready'
            for text in ['Tôi không ho.', 'Tôi chưa chắc có ho.', 'Khó thở nặng, thở không nổi.', 'Giả sử tôi ho và sốt thì sao?']:
                assert request('POST','/api/v1/chat',{'message':text})['predictions'] is None
            request('GET','/docs'); openapi=request('GET','/openapi.json')
            request('GET','/'); request('GET','/static/app.js')
            conn.close()
            # Qualify provenance only for other candidates; do NOT deserialize unsupported Windows checkpoints.
            frozen = protocol()
            candidates = {}
            for name, cp in frozen['checkpoints'].items():
                for file, expected in cp['files'].items():
                    p = data / cp['folder'] / file
                    assert sha256_file(p) == expected['sha256'] and p.stat().st_size == expected['bytes']
                candidates[name] = dict(checksum='PASS', versions=cp['identity']['versions'],
                    runtime_compatible=_runtime_compatible(cp, versions()),
                    checkpoint_sha256=cp['files']['pipeline.joblib']['sha256'])
            assert not any(code_guard.values()) and not any(data_guard.values()) and not any(counters.values())
            report = dict(status='PASS', versions=versions(), health=health, launcher='run_api.py main via runpy; real Uvicorn TCP',
                http={'health':200,'predict':200,'chat':200,'docs':200,'openapi':200,'website':200},
                routes=sorted(openapi['paths']), top3_count=len(result['top3']),
                batch_questions='PASS', user_requested_preview='PASS', denied_uncertain_urgent_fiction='PASS',
                candidates=candidates, code_guard=dict(code_guard),data_guard=dict(data_guard),counters=counters,
                model_registry=model_registry,
                dataset_payload_opened=False, models_fitted=0,
                limitations='Synthetic mechanical smoke, not clinical validation. Extra model Windows runtime qualification remains BLOCKED.')
        finally:
            if holder.get('server'):
                holder['server'].should_exit = True
            thread.join(timeout=15)
            listener.close()
            assert not thread.is_alive(), 'Server did not stop'
    destination=Path(os.environ.get('DISEASE_SMOKE_OUTPUT',ROOT/'reports/academic_review_20261111/runtime_smoke.json'))
    save(destination, report)
    print(json.dumps({'status':report['status'],'http':report['http'],'candidates':candidates}, indent=2))


if __name__ == '__main__':
    main()
