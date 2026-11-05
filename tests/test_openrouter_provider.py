"""OpenRouter JSON-mode mechanics only: fictional/mock responses, no live or ML."""
from copy import deepcopy
from dataclasses import replace
import io
import json
from pathlib import Path
import socket
from urllib.error import HTTPError

import pytest

from src.agent import provider as pm
from src.agent.conversation import ConversationEngine, Policy, SessionStore, SYSTEM
from src.agent.extraction import Catalog, ExtractionError, ExtractionValidator, Turn
from src.models.ensemble import phase4_guard
from test_phase5b import extraction

ROOT = Path(__file__).resolve().parents[1]
TEXT = "Tôi ho và sốt từ sáng nay, nhưng không đau đầu."


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    for key in (*pm.PROVIDER_KEYS.values(), *pm.PROVIDER_LIVE_FLAGS.values(), "DISEASE_LLM_PROVIDER", "DISEASE_LLM_MODEL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("No live requests"))
    for name in ("_post", "_post_groq", "_post_openrouter"):
        monkeypatch.setattr(pm, name, lambda *a, **k: pytest.fail("Unexpected provider request"))
    with phase4_guard(ROOT) as guard:
        yield
    assert not any(guard.values())


def settings(**kwargs):
    return pm.ProviderSettings(provider="openrouter", model=pm.OPENROUTER_FREE_MODEL,
        api_key_env="OPENROUTER_API_KEY", schema_mode="json_object", live_enabled=True, max_retries=0, **kwargs)


def select(monkeypatch):
    for key, value in {"DISEASE_LLM_PROVIDER": "openrouter", "DISEASE_LLM_MODEL": pm.OPENROUTER_FREE_MODEL,
                       "OPENROUTER_API_KEY": "offline-openrouter-fixture", "DISEASE_OPENROUTER_LIVE": "1",
                       "DISEASE_API_STORAGE_ROOT": str(ROOT)}.items():
        monkeypatch.setenv(key, value)


def response(data):
    return {"model": pm.OPENROUTER_FREE_MODEL, "_http_status": 200,
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(data), "role": "assistant"}}],
            "usage": {"prompt_tokens": 25, "completion_tokens": 12, "total_tokens": 37}}


def coded_extraction(body, *, edit=None):
    payload = json.loads(body["messages"][1]["content"])
    turns = [Turn(**x) for x in payload["turns"]]
    catalog = Catalog.load(ROOT)
    tid = turns[-1].turn_id
    data = extraction(catalog, turns, [("cough", "present", "ho", tid), ("fever", "present", "sốt", tid)] +
                      ([("headache", "denied", "đau đầu", tid)] if "đau đầu" in turns[-1].text else []))
    if edit: edit(data)
    mapping = {v: k for k, v in payload["allowed_features"].items()}
    for state in ("present", "denied", "uncertain"):
        for mention in data[state]:
            mention["feature"] = mapping.get(mention["feature"], mention["feature"])
    data["clarification"]["target_features"] = [mapping.get(f, f) for f in data["clarification"]["target_features"]]
    return data


def test_explicit_config_selects_only_free_gemma_with_independent_opt_in(monkeypatch):
    original = (ROOT / "configs/phase5b.json").read_bytes()
    monkeypatch.setenv("DISEASE_LLM_PROVIDER", "openrouter")
    with pytest.raises(ValueError, match="explicit_model_required"):
        pm.ProviderSettings.from_environment(ROOT / "configs/phase5b.json")
    monkeypatch.setenv("DISEASE_LLM_MODEL", pm.OPENROUTER_FREE_MODEL)
    monkeypatch.setenv("GEMINI_API_KEY", "offline-other-provider")
    monkeypatch.setenv("DISEASE_GEMINI_LIVE", "1")
    cfg = pm.ProviderSettings.from_environment(ROOT / "configs/phase5b.json")
    assert cfg.api_key_env == "OPENROUTER_API_KEY" and cfg.schema_mode == "json_object" and not cfg.live_enabled
    assert isinstance(pm.create_provider(cfg), pm.OpenRouterProvider)
    assert (ROOT / "configs/phase5b.json").read_bytes() == original


@pytest.mark.parametrize("overrides", [
    {"model": "google/gemma-4-26b-a4b-it"}, {"model": "openrouter/free"},
    {"schema_mode": "schema"}, {"schema_mode": "json_only"}, {"api_key_env": "GEMINI_API_KEY"},
])
def test_paid_or_router_models_and_unsupported_schema_modes_fail_closed(overrides):
    values = dict(provider="openrouter", model=pm.OPENROUTER_FREE_MODEL, api_key_env="OPENROUTER_API_KEY", schema_mode="json_object")
    with pytest.raises(ValueError): pm.ProviderSettings(**{**values, **overrides})


@pytest.mark.parametrize("disabled", [True, False])
def test_missing_prerequisites_send_nothing(monkeypatch, disabled):
    adapter = pm.create_provider(replace(settings(), live_enabled=not disabled))
    with pytest.raises(pm.ProviderError, match="live_disabled" if disabled else "missing_api_key"):
        adapter.generate(task="intent", system="JSON", payload={}, schema={})


def test_actual_json_mode_contract_decodes_all_features_and_preserves_denial(monkeypatch):
    select(monkeypatch)
    catalog = Catalog.load(ROOT); validator = ExtractionValidator(catalog)
    turn = Turn("u1", "user", TEXT, "self")
    def transport(body, key, timeout):
        assert key == "offline-openrouter-fixture"
        assert body["response_format"] == {"type": "json_object"}
        assert "max_tokens" in body and "max_completion_tokens" not in body and not body["stream"]
        assert body["provider"] == {"allow_fallbacks": False, "require_parameters": True,
                                    "max_price": {"prompt": 0, "completion": 0, "request": 0}}
        assert not {"models", "route", "tools", "plugins"} & body.keys()
        payload = json.loads(body["messages"][1]["content"])
        assert list(payload["allowed_features"].values()) == list(catalog.features)
        assert payload["output_contract"] == pm._serving_schema(validator.schema, task="extraction")
        assert len(payload["output_contract"]["$defs"]["feature"]["enum"]) == 375
        return response(coded_extraction(body))
    reply = pm.create_provider(settings(), transport=transport).generate(task="extraction", system=SYSTEM,
        payload={"turns": [turn.__dict__], "allowed_features": list(catalog.features)}, schema=validator.schema)
    value = validator.validate(reply.data, [turn], "self")
    frame = validator.frame(value)
    assert frame.shape == (1, 375) and frame.columns.tolist() == list(catalog.features)
    assert value.states == {"cough": "present", "fever": "present", "headache": "denied"}
    assert int(frame.sum(axis=1).iat[0]) == 2 and frame["headache"].iat[0] == 0
    assert reply.telemetry[0]["schema_enforcement"] == "python_validator_only"
    assert reply.telemetry[0]["usage"]["total_tokens"] == 37
    assert reply.telemetry[0]["reported_cost"] is None


@pytest.mark.parametrize("bad", ["empty", "whitespace", "invalid", "fenced", "duplicate_keys", "nan", "truncated", "filtered", "refusal", "tools", "error_envelope", "wrong_model"])
def test_bad_response_never_becomes_extraction(monkeypatch, bad):
    select(monkeypatch); raw = response({"ok": True}); choice = raw["choices"][0]
    if bad in {"empty", "whitespace", "invalid", "fenced", "duplicate_keys", "nan"}:
        choice["message"]["content"] = {"empty": "", "whitespace": " ", "invalid": "{", "fenced": '```json\n{}\n```',
            "duplicate_keys": '{"ok":true,"ok":false}', "nan": '{"number":NaN}'}[bad]
    if bad in {"truncated", "filtered"}: choice["finish_reason"] = "length" if bad == "truncated" else "content_filter"
    if bad == "refusal": choice["message"]["refusal"] = "blocked"
    if bad == "tools": choice["message"]["tool_calls"] = [{}]
    if bad == "error_envelope": raw = {"error": {"code": 503}, "_http_status": 200}
    if bad == "wrong_model": raw["model"] = "unapproved-model"
    with pytest.raises(pm.ProviderError):
        pm.create_provider(settings(), transport=lambda *a: raw).generate(task="intent", system="JSON", payload={}, schema={})


@pytest.mark.parametrize("http,code", [(400,"schema_or_request_rejected"),(401,"authentication_failed"),
    (403,"access_denied"),(404,"model_unavailable"),(429,"rate_limited"),(500,"provider_internal_error"),
    (502,"provider_bad_gateway"),(503,"provider_unavailable")])
def test_http_errors_are_distinct_sanitized_and_never_retried(monkeypatch, http, code):
    select(monkeypatch); calls=[]
    def transport(*args):
        calls.append(1)
        raw=json.dumps({"error":{"message":"offline-openrouter-fixture " + "sk-or-v1-" + "x"*32}}).encode()
        raise HTTPError(pm.PROVIDER_ENDPOINTS["openrouter"],http,"fixture",{},io.BytesIO(raw))
    with pytest.raises(pm.ProviderError) as caught:
        # Direct adapter also forces retry0, not merely the production wrapper.
        pm.create_provider(replace(settings(),max_retries=2), transport=transport).generate(task="intent",system="JSON",payload={},schema={})
    assert caught.value.code == code and caught.value.diagnostics["http_status"] == http and len(calls)==1
    assert "offline-openrouter-fixture" not in json.dumps(caught.value.diagnostics)
    assert "x"*32 not in json.dumps(caught.value.diagnostics)


def test_openrouter_timeout_has_one_attempt(monkeypatch):
    select(monkeypatch); calls=[]
    def transport(*args): calls.append(1); raise TimeoutError()
    with pytest.raises(pm.ProviderError,match="timeout"):
        pm.create_provider(settings(),transport=transport).generate(task="intent",system="JSON",payload={},schema={})
    assert len(calls)==1


def test_transport_uses_fixed_bearer_endpoint_bounds_and_no_redirect(monkeypatch):
    # The autouse fixture deliberately replaces network transports; call a fresh
    # module's real transport with only its opener replaced by an offline double.
    import runpy
    api=runpy.run_path(str(ROOT/'src/agent/provider.py'))
    class Reply:
        status=200
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self,limit):
            assert limit==1024*1024+1
            return json.dumps(response({"ok":True})).encode()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url == 'https://openrouter.ai/api/v1/chat/completions'
            assert request.method=='POST' and timeout==20
            assert request.get_header('Authorization')=='Bearer offline-openrouter-fixture'
            assert request.get_header('X-goog-api-key') is None
            return Reply()
    def opener(handler):
        assert handler.redirect_request(None,None,None,None,None,None) is None
        return Opener()
    monkeypatch.setitem(api['_post_openrouter'].__globals__,'build_opener',opener)
    assert api['_post_openrouter']({'model':pm.OPENROUTER_FREE_MODEL},'offline-openrouter-fixture',20)['_http_status']==200
    with pytest.raises(Exception,match='local_request_size_limit'):
        api['_post_openrouter']({'input':'x'*64001},'offline-openrouter-fixture',20)


@pytest.mark.parametrize("bad", ["unknown", "extra", "evidence", "subject", "past", "conflict", "uncertain", "unmapped"])
def test_existing_python_validator_rejects_or_gates_unsafe_semantics(monkeypatch,bad):
    select(monkeypatch); catalog=Catalog.load(ROOT); validator=ExtractionValidator(catalog)
    text = "Mẹ tôi ho và sốt." if bad=='subject' else "Hôm qua tôi ho và sốt." if bad=='past' else TEXT
    turn=Turn('u1','user',text,'self')
    def edit(data):
        if bad=='unknown': data['present'][0]['feature']='f999'
        if bad=='extra': data['percentages']=[99]
        if bad=='evidence': data['present'][0]['evidence'][0]['start']+=1
        if bad=='conflict': data['denied'].append(deepcopy(data['present'][0]))
        if bad=='uncertain':
            data['uncertain']=[data['present'].pop()]
            data['clarification']={'needed':True,'reasons':['uncertain'],'target_features':['fever']}
        if bad=='unmapped':
            data['unmapped']=[{'phrase':'sốt','state':'present','reason':'unclear_context','evidence':deepcopy(data['present'][1]['evidence'])}]
            data['clarification']={'needed':True,'reasons':['unmapped'],'target_features':[]}
    adapter=pm.create_provider(settings(),transport=lambda body,*args:response(coded_extraction(body,edit=edit)))
    try:
        reply=adapter.generate(task='extraction',system=SYSTEM,payload={'turns':[turn.__dict__],'allowed_features':list(catalog.features)},schema=validator.schema)
        valid=validator.validate(reply.data,[turn],'self')
    except (pm.ProviderError,ExtractionError): return
    assert validator.gate(valid) is not None


@pytest.mark.parametrize("failure,requests", [(None,3),('A503',1),('Atimeout',1),('Ainvalid',1),
    ('Aconnection',1),('B400',2),('Bextra',2),('Bjson',2),('C429',3),('Cunknown',3),('Cdenial_missing',3)])
def test_three_stage_qualification_real_adapter_no_lr_stop_on_first_failure(monkeypatch,failure,requests):
    from scripts.smoke_local_mvp import openrouter_three_stage_qualification
    select(monkeypatch); calls=[]
    def transport(body,key,timeout):
        calls.append(deepcopy(body)); name='ABC'[len(calls)-1]
        assert timeout==60 and body['model']==pm.OPENROUTER_FREE_MODEL
        assert body['max_tokens']==2048 and not body['provider']['allow_fallbacks']
        assert len(json.dumps(body,ensure_ascii=False).encode())<=32768
        if failure==name+'503' or failure==name+'400' or failure==name+'429':
            raise HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],int(failure[1:]),'fixture',{},io.BytesIO(b'{"error":{"message":"fixture failure"}}'))
        if failure==name+'timeout': raise TimeoutError()
        if failure==name+'connection': raise ConnectionError('Must not echo transport exception detail')
        if name=='A':
            assert 'response_format' not in body and len(body['messages'])==2
            raw=response({});raw['choices'][0]['message']['content']='' if failure=='Ainvalid' else 'Xin chào bạn.'
            return raw
        assert body['response_format']=={'type':'json_object'}
        if name=='B':
            payload=json.loads(body['messages'][1]['content'])
            assert set(payload['output_contract']['required'])=={'intent','has_symptom'}
            raw=response({'intent':'symptom_description','has_symptom':True,**({'extra':1} if failure=='Bextra' else {})})
            if failure=='Bjson':raw['choices'][0]['message']['content']='{'
            return raw
        payload=json.loads(body['messages'][1]['content'])
        assert payload['turns'][-1]['text']==TEXT and len(payload['allowed_features'])==375
        def edit(data):
            if failure=='Cunknown':data['present'][0]['feature']='f999'
            if failure=='Cdenial_missing':data['denied']=[]
        return response(coded_extraction(body,edit=edit))
    monkeypatch.setattr(pm,'_post_openrouter',transport)
    result=openrouter_three_stage_qualification(allow_live=True,no_web_requests=True)
    assert result['requests_used']==len(calls)==requests and result['automatic_retries']==0
    assert not result['predictions_called'] and not result['models_fitted'] and not result['test_payload_opened']
    assert 'strict_schema_acceptance' not in result and 'Python' in result['schema_enforcement']
    if failure is None:
        assert result['status']=='PASS' and result['extraction_validator']=='PASS'
        assert result['C']['denied_features']==['headache'] and result['C']['headache_vector_value']==0
        assert result['C']['vector_shape']==[375] and set(result['C']['confirmed_features'])=={'cough','fever'}
    else:
        assert result['status']!='PASS' and result['first_failing_stage']
        for name in 'ABC'[requests:]: assert result[name]['status']=='NOT RUN'


@pytest.mark.parametrize('missing',['key','live','selection','opt_in','no_web'])
def test_qualification_without_prerequisites_has_zero_requests(monkeypatch,missing):
    from scripts.smoke_local_mvp import openrouter_three_stage_qualification
    select(monkeypatch)
    if missing=='key':monkeypatch.delenv('OPENROUTER_API_KEY')
    if missing=='live':monkeypatch.delenv('DISEASE_OPENROUTER_LIVE')
    if missing=='selection':monkeypatch.setenv('DISEASE_LLM_MODEL','gemini-3.8-flash')
    result=openrouter_three_stage_qualification(allow_live=missing!='opt_in',no_web_requests=missing!='no_web')
    assert result['status']=='BLOCKED' and result['requests_used']==0
    assert all(result[n]['status']=='NOT RUN' for n in 'ABC')


def test_conversation_failure_resets_previous_extraction_and_session_reset(monkeypatch):
    select(monkeypatch); catalog=Catalog.load(ROOT); calls=[]
    def transport(body,*args):
        calls.append(1)
        if len(calls)==2: raise HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],503,'fixture',{},io.BytesIO(b'{"error":{"message":"busy"}}'))
        return response(coded_extraction(body))
    engine=ConversationEngine(catalog,pm.create_provider(settings(),transport=transport),Policy())
    ready=engine.handle(TEXT)
    assert ready.status=='extraction_ready'
    failed=engine.handle('Tôi đang ho và sốt.',session_id=ready.session_id)
    assert failed.status=='provider_error'
    with pytest.raises(ValueError):engine.ready_vector(ready.session_id,ready.turn_id)
    engine.store.discard(ready.session_id)
    assert engine.handle(TEXT,session_id=ready.session_id).reason=='invalid_session'


def test_urgent_guard_makes_no_openrouter_request(monkeypatch):
    select(monkeypatch)
    engine=ConversationEngine(Catalog.load(ROOT),pm.create_provider(settings()),Policy())
    result=engine.handle('Tôi khó thở nặng, thở không nổi.')
    assert result.status=='urgent_redirect'


def test_valid_uncertainty_is_preserved_and_cannot_become_present(monkeypatch):
    select(monkeypatch); catalog=Catalog.load(ROOT); validator=ExtractionValidator(catalog)
    turn=Turn('u1','user','Tôi ho, hình như sốt.','self')
    def edit(data):
        data['uncertain']=[data['present'].pop()]
        data['clarification']={'needed':True,'reasons':['uncertain'],'target_features':['fever']}
    adapter=pm.create_provider(settings(),transport=lambda body,*args:response(coded_extraction(body,edit=edit)))
    reply=adapter.generate(task='extraction',system=SYSTEM,payload={'turns':[turn.__dict__],'allowed_features':list(catalog.features)},schema=validator.schema)
    value=validator.validate(reply.data,[turn],'self')
    assert value.states=={'cough':'present','fever':'uncertain'}
    assert validator.gate(value)=='uncertain'
    with pytest.raises(ExtractionError,match='quality_gate_blocked'):validator.frame(value)


def test_expired_session_cannot_reuse_validated_vector(monkeypatch):
    select(monkeypatch); now=[0.0]; policy=Policy(session_ttl_seconds=1)
    store=SessionStore(policy,clock=lambda:now[0])
    adapter=pm.create_provider(settings(),transport=lambda body,*args:response(coded_extraction(body)))
    engine=ConversationEngine(Catalog.load(ROOT),adapter,policy,store=store)
    ready=engine.handle(TEXT); assert ready.status=='extraction_ready'
    now[0]=2.0
    with pytest.raises(ValueError):engine.ready_vector(ready.session_id,ready.turn_id)


def test_existing_backend_provider_factory_applies_same_budget_and_json_adapter(monkeypatch):
    from app.backend.chat import production_provider
    select(monkeypatch)
    monkeypatch.setattr(pm,'_post_openrouter',lambda body,*args:response(coded_extraction(body)))
    provider=production_provider(ROOT)
    assert provider.settings.provider=='openrouter' and provider.settings.max_retries==0
    assert provider.settings.max_output_tokens==2048 and provider.settings.schema_mode=='json_object'
    turn=Turn('u1','user',TEXT,'self'); catalog=Catalog.load(ROOT)
    reply=provider.generate(task='extraction',system=SYSTEM,
        payload={'turns':[turn.__dict__],'allowed_features':list(catalog.features)},schema=ExtractionValidator(catalog).schema)
    assert reply.data['denied'][0]['feature']=='headache'
    assert provider.status()['requests_used']==1 and provider.status()['provider']=='openrouter'


@pytest.mark.parametrize('metadata,headers,source,confidence', [
    ({'error_type':'rate_limit_exceeded'}, {'X-RateLimit-Limit':'20','X-RateLimit-Remaining':'0','X-RateLimit-Reset':'1793404800000'}, 'openrouter_platform','LIKELY'),
    ({'provider_name':'Google AI Studio','provider_code':'rate_limited','error_type':'rate_limit_exceeded'}, {}, 'upstream_provider','CONFIRMED'),
    ({'provider_code':429}, {}, 'upstream_provider','CONFIRMED'),
    ({'provider_code':'429'}, {}, 'upstream_provider','CONFIRMED'),
    ({'provider_name':'Google AI Studio'}, {}, 'upstream_provider','LIKELY'),
    ({'error_type':'rate_limit_exceeded'}, {}, 'unresolved','UNRESOLVED'),
    ({}, {}, 'unresolved','UNRESOLVED'),
    ({'limit_source':'openrouter_key_limit'}, {}, 'openrouter_key_or_budget_policy','CONFIRMED'),
    ({'provider_code':'RESOURCE_EXHAUSTED'}, {'X-RateLimit-Remaining':'0'}, 'unresolved','UNRESOLVED'),
])
def test_429_source_classification_requires_recorded_evidence(metadata,headers,source,confidence):
    body=json.dumps({'error':{'code':429,'message':'Provider returned error','metadata':metadata}}).encode()
    error=HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],429,'fixture',headers,io.BytesIO(body))
    diagnostic=pm._http_diagnostics(error,'offline-openrouter-fixture',{},provider='openrouter')
    assert diagnostic['http_status']==diagnostic['provider_error_code']==429
    assert diagnostic['provider_message']=='Provider returned error'
    assert diagnostic['rate_limit_classification']['source']==source
    assert diagnostic['rate_limit_classification']['confidence']==confidence


@pytest.mark.parametrize('retry_after', [None,'60','Sat, 31 Oct 2026 00:00:00 GMT'])
def test_429_retry_hint_is_recorded_without_sleep_or_retries(monkeypatch,retry_after):
    select(monkeypatch);calls=[]
    headers={'Retry-After':retry_after} if retry_after is not None else {}
    def transport(*args):
        calls.append(1)
        raise HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],429,'fixture',headers,
                        io.BytesIO(b'{"error":{"code":429,"message":"Provider returned error"}}'))
    adapter=pm.create_provider(settings(),transport=transport,sleep=lambda *a:pytest.fail('Never retry/sleep'))
    with pytest.raises(pm.ProviderError) as caught:
        adapter.generate(task='intent',system='JSON',payload={},schema={})
    diagnostic=caught.value.diagnostics
    assert len(calls)==1 and caught.value.code=='rate_limited'
    if retry_after is None: assert 'retry_after' not in diagnostic
    else: assert diagnostic['retry_after']==retry_after
    assert diagnostic['rate_limit_classification']['source']=='unresolved'


@pytest.mark.parametrize('raw', [b'not JSON',b'{"error":null}',b'x'*16385])
def test_429_malformed_or_oversized_body_keeps_only_safe_headers(raw):
    error=HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],429,'fixture',
        {'retry-after':'30','X-RateLimit-Remaining':'0','Set-Cookie':'must-not-log'},io.BytesIO(raw))
    diagnostic=pm._http_diagnostics(error,'offline-openrouter-fixture',{},provider='openrouter')
    assert diagnostic['http_status']==429 and diagnostic['retry_after']=='30'
    assert diagnostic['rate_limit_headers']=={'X-RateLimit-Remaining':'0'}
    assert 'must-not-log' not in json.dumps(diagnostic) and 'provider_error_code' not in diagnostic


def test_429_never_keeps_credentials_raw_provider_metadata_or_health_text():
    key='offline-openrouter-fixture'; health='fictional-sensitive-health-text'
    detail={'code':429,'message':key+' '+health,'metadata':{
        'provider_name':key,'provider_code':key,'error_type':health,'limit_source':health,
        'raw':json.dumps({'Authorization':key,'flagged_input':health}),
        'request':{'turns':health},'cookie':'must-not-log','unknown_field':key}}
    headers={'Authorization':key,'Set-Cookie':key,'Cookie':key,'X-Api-Key':key,
             'Retry-After':key,'X-RateLimit-Reset':'https://example.invalid/?key='+key,
             'X-RateLimit-Limit':'20\r\nAuthorization: '+key}
    error=HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],429,'fixture',headers,io.BytesIO(json.dumps({'error':detail}).encode()))
    diagnostic=pm._http_diagnostics(error,key,{'turns':[{'text':health}]},provider='openrouter')
    encoded=json.dumps(diagnostic)
    assert key not in encoded and health not in encoded and 'Authorization' not in encoded
    assert 'cookie' not in encoded.lower() and 'raw' not in encoded and 'rate_limit_headers' not in diagnostic
    assert diagnostic['provider_message']=='[REDACTED] [REDACTED]'


def test_non_openrouter_diagnostic_contract_is_unchanged():
    for provider in ('gemini','groq'):
        error=HTTPError('https://example.invalid',429,'fixture',{'Retry-After':'60'},io.BytesIO(
            b'{"error":{"code":429,"message":"busy","metadata":{"provider_code":"rate_limited"}}}'))
        assert pm._http_diagnostics(error,'fixture',{},provider=provider)=={'http_status':429,'provider_message':'busy'}


@pytest.mark.parametrize('outcome',['429','200','timeout'])
def test_future_one_request_probe_never_runs_B_C(monkeypatch,outcome):
    from scripts.smoke_local_mvp import openrouter_429_diagnostic
    select(monkeypatch);calls=[]
    def transport(body,key,timeout):
        calls.append(1)
        assert body['model']==pm.OPENROUTER_FREE_MODEL and 'response_format' not in body
        assert not body['provider']['allow_fallbacks'] and timeout==60
        if outcome=='timeout': raise TimeoutError()
        if outcome=='429': raise HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],429,'fixture',{'Retry-After':'60'},io.BytesIO(
            b'{"error":{"code":429,"message":"Provider returned error","metadata":{"provider_code":"rate_limited"}}}'))
        raw=response({});raw['choices'][0]['message']['content']='Xin chào bạn.'
        return raw
    monkeypatch.setattr(pm,'_post_openrouter',transport)
    result=openrouter_429_diagnostic(allow_live=True,no_web_requests=True)
    assert result['request_limit']==result['requests_used']==len(calls)==1
    assert result['B']['status']==result['C']['status']=='NOT RUN'
    assert result['extraction_validator']=='NOT VERIFIED' and not result['predictions_called']
    if outcome=='429':
        assert result['A']['diagnostic']['retry_after']=='60'
        assert result['error_classification']['source']=='upstream_provider'


def test_future_one_request_probe_still_requires_separate_live_opt_in(monkeypatch):
    from scripts.smoke_local_mvp import openrouter_429_diagnostic
    select(monkeypatch)
    result=openrouter_429_diagnostic(allow_live=False,no_web_requests=True)
    assert result['requests_used']==0 and result['A']['status']=='NOT RUN'


def select_nemotron(monkeypatch):
    select(monkeypatch)
    monkeypatch.setenv('DISEASE_LLM_MODEL',pm.OPENROUTER_NEMOTRON_MODEL)
    return pm.ProviderSettings.from_environment(ROOT/'configs/phase5b.json')


def nemotron_response(data):
    raw=response(data)
    raw.update(model=pm.OPENROUTER_NEMOTRON_MODEL,provider='Nvidia')
    return raw


def test_nemotron_has_explicit_free_model_capability_without_changing_default(monkeypatch):
    original=(ROOT/'configs/phase5b.json').read_bytes()
    cfg=select_nemotron(monkeypatch)
    assert cfg.provider=='openrouter' and cfg.model=='nvidia/nemotron-3.5-super-vl:free'
    assert cfg.schema_mode=='json_schema' and cfg.api_key_env=='OPENROUTER_API_KEY'
    assert isinstance(pm.create_provider(cfg),pm.OpenRouterProvider)
    assert (ROOT/'configs/phase5b.json').read_bytes()==original
    with pytest.raises(ValueError):replace(cfg,model=cfg.model.removesuffix(':free'))
    with pytest.raises(ValueError):replace(cfg,schema_mode='json_object')
    with pytest.raises(ValueError):replace(cfg,schema_mode='schema')


@pytest.mark.parametrize('content,finish,accepted',[
    (None,'stop',False),('','stop',False),('{','stop',False),('valid','length',False),
    ('<think>internal</think>{}','stop',False),('valid','stop',True),
])
def test_nemotron_parses_only_content_not_reasoning_or_reasoning_details(monkeypatch,content,finish,accepted):
    cfg=select_nemotron(monkeypatch);catalog=Catalog.load(ROOT);validator=ExtractionValidator(catalog)
    turn=Turn('u1','user',TEXT,'self')
    def transport(body,*args):
        raw=nemotron_response(coded_extraction(body))
        message=raw['choices'][0]['message']
        message['reasoning']='must-not-log-reasoning-content'
        message['reasoning_details']=[{'text':'must-not-log-reasoning-details'}]
        if content!='valid':message['content']=content
        raw['choices'][0]['finish_reason']=finish
        return raw
    adapter=pm.create_provider(cfg,transport=transport)
    kwargs=dict(task='extraction',system=SYSTEM,payload={'turns':[turn.__dict__],'allowed_features':list(catalog.features)},schema=validator.schema)
    if not accepted:
        with pytest.raises(pm.ProviderError):adapter.generate(**kwargs)
    else:
        reply=adapter.generate(**kwargs)
        assert validator.frame(validator.validate(reply.data,[turn],'self')).shape==(1,375)
        assert 'must-not-log' not in json.dumps(reply.telemetry)


@pytest.mark.parametrize('failure,calls_expected',[
    (None,3),('A401',1),('A403',1),('A404',1),('A429',1),('A503',1),('Atimeout',1),
    ('Aempty',1),('Areasoning_only',1),('Alength',1),('Awrong_model',1),
    ('B400',2),('Bjson',2),('Bschema',2),('C429',3),('C503',3),('Cunknown',3),('Cdenial_missing',3),
])
def test_nemotron_qualification_exact_prompts_schema_and_budget_no_fallback(monkeypatch,failure,calls_expected):
    from scripts.smoke_local_mvp import nemotron_three_stage_qualification
    select_nemotron(monkeypatch);calls=[];catalog=Catalog.load(ROOT)
    def transport(body,key,timeout):
        calls.append(deepcopy(body));name='ABC'[len(calls)-1]
        assert body['model']=='nvidia/nemotron-3.5-super-vl:free'
        assert not {'models','route','plugins','tools'} & body.keys()
        assert body['stream'] is False and body['max_tokens']==2048 and timeout==60
        assert body['reasoning']=={'enabled':False}
        assert body['provider']=={'allow_fallbacks':False,'require_parameters':True,
            'max_price':{'prompt':0,'completion':0,'request':0}}
        if failure and failure.startswith(name) and failure[1:].isdigit():
            code=int(failure[1:])
            raise HTTPError(pm.PROVIDER_ENDPOINTS['openrouter'],code,'fixture',{'Retry-After':'30'},io.BytesIO(json.dumps(
                {'error':{'code':code,'message':'Provider returned error','metadata':{'provider_name':'Nvidia','provider_code':'rate_limited' if code==429 else 'server'}}}).encode()))
        if failure==name+'timeout':raise TimeoutError()
        if name=='A':
            assert 'response_format' not in body
            assert body['messages']==[{'role':'system','content':'Trả lời ngắn gọn bằng tiếng Việt.'},
                {'role':'user','content':'Xin chào. Hãy trả lời bằng một câu ngắn.'}]
            raw=nemotron_response({});message=raw['choices'][0]['message']
            message['content']=None if failure=='Areasoning_only' else '' if failure=='Aempty' else 'Xin chào bạn.'
            message['reasoning']='must-not-log-reasoning'
            if failure=='Alength':raw['choices'][0]['finish_reason']='length'
            if failure=='Awrong_model':raw['model']='unapproved-model'
            return raw
        fmt=body['response_format']
        assert fmt['type']=='json_schema' and fmt['json_schema']['strict'] is False
        if name=='B':
            assert set(fmt['json_schema']['schema']['required'])=={'intent','has_symptom'}
            raw=nemotron_response({'intent':'symptom_description','has_symptom':'true' if failure=='Bschema' else True})
            if failure=='Bjson':raw['choices'][0]['message']['content']='not JSON'
            return raw
        assert fmt['json_schema']['schema']==pm._serving_schema(ExtractionValidator(catalog).schema,task='extraction')
        payload=json.loads(body['messages'][1]['content'])
        assert payload['turns'][-1]['text']==TEXT and list(payload['allowed_features'].values())==list(catalog.features)
        def edit(data):
            if failure=='Cunknown':data['present'][0]['feature']='f999'
            if failure=='Cdenial_missing':data['denied']=[]
        raw=nemotron_response(coded_extraction(body,edit=edit))
        raw['choices'][0]['message']['reasoning_details']=[{'text':'must-not-log-reasoning'}]
        return raw
    monkeypatch.setattr(pm,'_post_openrouter',transport)
    result=nemotron_three_stage_qualification(allow_live=True,no_web_requests=True)
    assert result['request_limit']==3 and result['requests_used']==len(calls)==calls_expected
    assert result['automatic_retries']==0 and not result['strict_requested']
    assert not result['models_fitted'] and not result['predictions_called'] and not result['test_payload_opened']
    assert 'must-not-log' not in json.dumps(result) and 'offline-openrouter-fixture' not in json.dumps(result)
    if failure is None:
        assert result['status']=='PASS' and result['extraction_validator']=='PASS'
        assert result['C']['vector_shape']==[375] and result['C']['headache_vector_value']==0
        assert set(result['C']['confirmed_features'])=={'cough','fever'} and result['C']['denied_features']==['headache']
        assert result['C']['actual_response_model']==pm.OPENROUTER_NEMOTRON_MODEL
        assert result['C']['upstream_provider']=='Nvidia' and result['C']['reasoning_fields_present']
    else:
        assert result['status']!='PASS' and result['first_failing_stage']
        for name in 'ABC'[calls_expected:]:assert result[name]['status']=='NOT RUN'
        if failure.endswith('429') or failure.endswith('503'):
            assert result[failure[0]]['diagnostic']['provider_metadata']['provider_name']=='Nvidia'


@pytest.mark.parametrize('missing',['key','live','selection','opt_in','no_web'])
def test_nemotron_no_requests_without_credentials_and_explicit_selection(monkeypatch,missing):
    from scripts.smoke_local_mvp import nemotron_three_stage_qualification
    select_nemotron(monkeypatch)
    if missing=='key':monkeypatch.delenv('OPENROUTER_API_KEY')
    if missing=='live':monkeypatch.delenv('DISEASE_OPENROUTER_LIVE')
    if missing=='selection':monkeypatch.setenv('DISEASE_LLM_MODEL',pm.OPENROUTER_FREE_MODEL)
    result=nemotron_three_stage_qualification(allow_live=missing!='opt_in',no_web_requests=missing!='no_web')
    assert result['requests_used']==0 and result['status']=='BLOCKED'
    assert all(result[n]['status']=='NOT RUN' for n in 'ABC')


@pytest.mark.parametrize('stage',['A','B','C'])
def test_nemotron_HTTP200_error_without_model_is_not_masked_as_model_mismatch(monkeypatch,stage):
    from scripts.smoke_local_mvp import nemotron_three_stage_qualification
    select_nemotron(monkeypatch);calls=[]
    def transport(body,key,timeout):
        calls.append(1); name='ABC'[len(calls)-1]
        if name==stage:
            return {'_http_status':200,'error':{'code':400,
                'message':'Synthetic schema rejection offline-openrouter-fixture '+TEXT,
                'metadata':{'provider_name':'Nvidia','raw':'must-not-log-raw-envelope'}}}
        if name=='A':
            raw=nemotron_response({});raw['choices'][0]['message']['content']='Xin chào bạn.'
            return raw
        if name=='B':return nemotron_response({'intent':'symptom_description','has_symptom':True})
        pytest.fail('No further stage after provider error')
    monkeypatch.setattr(pm,'_post_openrouter',transport)
    result=nemotron_three_stage_qualification(allow_live=True,no_web_requests=True)
    failed=result[stage]
    assert result['requests_used']==len(calls)=='ABC'.index(stage)+1
    assert failed['reason']=='provider_response_error' and failed['http_status']==200
    assert failed['error_envelope_present'] and not failed['model_field_present']
    assert failed['diagnostic']['http_status']==200 and failed['diagnostic']['provider_error_code']==400
    assert failed['diagnostic']['provider_metadata']['provider_name']=='Nvidia'
    assert failed['diagnostic']['provider_message'].startswith('Synthetic schema rejection')
    encoded=json.dumps(result)
    assert 'offline-openrouter-fixture' not in encoded and TEXT not in encoded and 'must-not-log-raw-envelope' not in encoded
    assert result['extraction_validator']=='NOT VERIFIED' and not result['predictions_called']
    for later in 'ABC'['ABC'.index(stage)+1:]:assert result[later]['status']=='NOT RUN'


@pytest.mark.parametrize('case,expected_reason,validator_calls',[
    ('error_envelope','provider_response_error',0),
    ('missing_model','unexpected_response_model',0),
    ('null_model','unexpected_response_model',0),
    ('mismatched_model','unexpected_response_model',0),
    ('missing_choices','invalid_json_or_response',0),
    ('empty_choices','invalid_json_or_response',0),
    ('empty_content','invalid_json_or_response',0),
    ('reasoning_only','missing_text_response',0),
    ('length','incomplete_or_blocked_response',0),
    ('invalid_json','invalid_json_or_response',0),
    ('invalid_canonical','invalid_extraction_contract',1),
    ('valid',None,1),
])
def test_offline_stage_C_failure_boundaries_do_not_reconstruct_live_response(monkeypatch,case,expected_reason,validator_calls):
    """Entirely synthetic variants. Their results are NOT evidence of the original C body."""
    from scripts.smoke_local_mvp import nemotron_three_stage_qualification
    select_nemotron(monkeypatch); calls=[]; validation=[]
    original_validate=ExtractionValidator.validate
    def tracked_validate(self,*args,**kwargs):
        validation.append(1)
        return original_validate(self,*args,**kwargs)
    monkeypatch.setattr(ExtractionValidator,'validate',tracked_validate)
    def transport(body,*args):
        calls.append(1)
        if len(calls)==1:
            raw=nemotron_response({});raw['choices'][0]['message']['content']='Xin chào bạn.'
            return raw
        if len(calls)==2:return nemotron_response({'intent':'symptom_description','has_symptom':True})
        assert len(calls)==3
        raw=nemotron_response(coded_extraction(body))
        if case=='error_envelope':return {'_http_status':200,'error':{'code':503,'message':'Synthetic provider failure'}}
        if case=='missing_model':raw.pop('model')
        if case=='null_model':raw['model']=None
        if case=='mismatched_model':raw['model']='synthetic-unapproved-model'
        if case=='missing_choices':raw.pop('choices')
        if case=='empty_choices':raw['choices']=[]
        if case=='empty_content':raw['choices'][0]['message']['content']=''
        if case=='reasoning_only':
            raw['choices'][0]['message'].update(content=None,reasoning='must-not-log-reasoning')
        if case=='length':raw['choices'][0]['finish_reason']='length'
        if case=='invalid_json':raw['choices'][0]['message']['content']='{'
        if case=='invalid_canonical':
            value=json.loads(raw['choices'][0]['message']['content'])
            value['unsupported_field']=True
            raw['choices'][0]['message']['content']=json.dumps(value)
        return raw
    monkeypatch.setattr(pm,'_post_openrouter',transport)
    result=nemotron_three_stage_qualification(allow_live=True,no_web_requests=True)
    assert result['requests_used']==len(calls)==3 and len(validation)==validator_calls
    assert result['A']['status']==result['B']['status']=='PASS'
    assert result['C']['http_status']==200 and not result['predictions_called'] and not result['models_fitted']
    assert 'must-not-log' not in json.dumps(result)
    if expected_reason is None:
        assert result['status']=='PASS' and result['extraction_validator']=='PASS'
        assert result['C']['vector_shape']==[375] and result['C']['headache_vector_value']==0
    else:
        assert result['C']['reason']==expected_reason
        assert result['extraction_validator']==('FAIL' if validator_calls else 'NOT VERIFIED')
        if case in {'missing_model','null_model','mismatched_model'}:
            assert result['C']['actual_response_model']=='NOT RECORDED (unexpected/missing model)'
            assert result['C']['model_field_present'] is (case!='missing_model')
