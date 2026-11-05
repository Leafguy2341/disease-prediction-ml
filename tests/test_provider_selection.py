"""Offline provider qualification/selection. No account, network, model fit or CSV access."""
from copy import deepcopy
import io
import json
from pathlib import Path
import socket
from urllib.error import HTTPError

import pytest

from src.agent import provider as module
from src.agent.conversation import Policy, SYSTEM
from src.agent.extraction import Catalog, ExtractionValidator, Turn
from src.agent.provider import ProviderError, ProviderSettings
from src.models.ensemble import phase4_guard
from test_phase5b import extraction
from test_prediction_api import deployment, get_service

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("failure,expected_calls", [
    (None, 3), ("A503", 1), ("Atimeout", 1), ("Aempty", 1), ("Alength", 1),
    ("A401", 1), ("A403", 1), ("A404", 1), ("A429", 1), ("A400", 1),
    ("Bextra", 2), ("Bjson", 2), ("B400", 2), ("C400", 3),
    ("Cunknown", 3), ("Cevidence", 3), ("Cuncertain", 3), ("Cdenied", 3),
])
def test_groq_three_stage_exact_contract_stops_at_first_failure(monkeypatch, failure, expected_calls):
    from scripts.smoke_local_mvp import groq_three_stage_qualification
    monkeypatch.setenv("DISEASE_LLM_PROVIDER", "groq")
    monkeypatch.setenv("DISEASE_LLM_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("DISEASE_GROQ_LIVE", "1")
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    monkeypatch.setenv("DISEASE_API_STORAGE_ROOT", str(ROOT))
    monkeypatch.setattr(module, "_post", lambda *a: pytest.fail("No Gemini fallback"))
    catalog = Catalog.load(ROOT)
    calls = []
    before = (ROOT / "configs/phase5b.json").read_bytes()

    def transport(body, key, timeout):
        calls.append(deepcopy(body))
        name = "ABC"[len(calls) - 1]
        assert key == "offline-groq-fixture" and timeout == 60
        assert body["model"] == "openai/gpt-oss-20b"
        assert body["max_completion_tokens"] == 2048 and body["stream"] is False
        assert len(json.dumps(body, ensure_ascii=False).encode()) <= 32768
        if failure and failure.startswith(name):
            suffix = failure[1:]
            if suffix.isdigit():
                raise HTTPError("https://example.invalid", int(suffix), "fixture", {}, io.BytesIO(
                    b'{"error":{"message":"gsk_offline-secret-0123456789 unavailable"}}'))
            if suffix == "timeout": raise TimeoutError()
        if name == "A":
            assert set(body) == {"model", "messages", "max_completion_tokens", "stream"}
            assert body["messages"][0]["content"] == "Respond concisely in Vietnamese."
            assert body["messages"][1]["content"] == "Xin chào. Hãy trả lời đúng một câu ngắn."
            raw = response({})
            raw["choices"][0]["message"]["content"] = "" if failure == "Aempty" else "Xin chào bạn."
            if failure == "Alength": raw["choices"][0]["finish_reason"] = "length"
            return raw
        fmt = body["response_format"]
        assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
        if name == "B":
            assert fmt["json_schema"]["schema"]["required"] == ["intent", "has_symptom"]
            raw = response({"intent": "symptom_description", "has_symptom": True,
                            **({"extra": 1} if failure == "Bextra" else {})})
            if failure == "Bjson": raw["choices"][0]["message"]["content"] = "broken JSON"
            return raw
        assert fmt["json_schema"]["schema"] == module._serving_schema(ExtractionValidator(catalog).schema, task="extraction")
        payload = json.loads(body["messages"][1]["content"])
        assert list(payload["allowed_features"].values()) == list(catalog.features)
        turns = [Turn(**t) for t in payload["turns"]]
        state = {"Cuncertain": "uncertain", "Cdenied": "denied"}.get(failure, "present")
        # Denial/uncertainty not supported by the fixed affirmative text: validator must reject.
        data = extraction(catalog, turns, [("cough", "present", "ho", "u1"), ("fever", state, "sốt", "u1")])
        reverse = {v: k for k, v in payload["allowed_features"].items()}
        for group in ("present", "denied", "uncertain"):
            for item in data[group]: item["feature"] = reverse[item["feature"]]
        if failure == "Cunknown": data["present"][0]["feature"] = "f999"
        if failure == "Cevidence": data["present"][0]["evidence"][0]["text"] = "not in message"
        return response(data)

    monkeypatch.setattr(module, "_post_groq", transport)
    result = groq_three_stage_qualification(allow_live=True, no_web_requests=True)
    assert result["requests_used"] == len(calls) == expected_calls
    assert result["automatic_retries"] == 0 and result["request_limit"] == 3
    assert not result["predictions_called"] and not result["test_payload_opened"]
    assert result["models_fitted"] == 0 and result["reported_cost"] is None
    assert "offline-groq-fixture" not in json.dumps(result)
    assert "gsk_offline-secret" not in json.dumps(result)
    assert (ROOT / "configs/phase5b.json").read_bytes() == before
    if failure is None:
        assert result["status"] == "PASS" and result["recommendation"] == "KEEP AS CANDIDATE"
        assert result["C"]["vector_shape"] == [375]
        assert set(result["C"]["confirmed_features"]) == {"cough", "fever"}
        assert result["extraction_validator"] == "PASS"
    else:
        assert result["status"] != "PASS" and result["first_failing_stage"]
        for name in "ABC"[expected_calls:]: assert result[name]["status"] == "NOT RUN"


@pytest.mark.parametrize("missing", ["key", "live", "selection", "opt_in", "no_web"])
def test_groq_three_stage_missing_prerequisites_never_send(monkeypatch, missing):
    from scripts.smoke_local_mvp import groq_three_stage_qualification
    for k, v in {"GROQ_API_KEY": "fixture", "DISEASE_GROQ_LIVE": "1",
                 "DISEASE_LLM_PROVIDER": "groq", "DISEASE_LLM_MODEL": "openai/gpt-oss-20b"}.items():
        monkeypatch.setenv(k, v)
    if missing == "key": monkeypatch.delenv("GROQ_API_KEY")
    if missing == "live": monkeypatch.delenv("DISEASE_GROQ_LIVE")
    if missing == "selection": monkeypatch.setenv("DISEASE_LLM_MODEL", "openai/gpt-oss-120b")
    monkeypatch.setattr(module, "_post_groq", lambda *a: pytest.fail("Prerequisites must stop network"))
    result = groq_three_stage_qualification(allow_live=missing != "opt_in", no_web_requests=missing != "no_web")
    assert result["requests_used"] == 0 and result["status"] == "BLOCKED"
    assert all(result[n]["status"] == "NOT RUN" for n in "ABC")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("No real network"))
    for key in ("DISEASE_LLM_PROVIDER", "DISEASE_LLM_MODEL", "DISEASE_GEMINI_LIVE", "DISEASE_GROQ_LIVE",
                "GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "DISEASE_OPENROUTER_LIVE"):
        monkeypatch.delenv(key, raising=False)
    with phase4_guard(ROOT) as counts:
        yield
    assert not any(counts.values())


def groq_settings(**extra):
    return ProviderSettings(provider="groq", model="openai/gpt-oss-20b", api_key_env="GROQ_API_KEY",
                            live_enabled=True, max_retries=0, **extra)


def response(data, **extra):
    return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(data)}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 15, "total_tokens": 45},
            "_http_status": 200, **extra}


def test_selection_is_explicit_and_never_inherits_another_providers_key(monkeypatch):
    cfg = ROOT / "configs/phase5b.json"
    original = cfg.read_bytes()
    settings = ProviderSettings.from_environment(cfg)
    assert settings.provider == "gemini" and settings.model == "gemini-3.8-flash" and not settings.live_enabled
    monkeypatch.setenv("DISEASE_LLM_PROVIDER", "groq")
    with pytest.raises(ValueError): ProviderSettings.from_environment(cfg)
    monkeypatch.setenv("DISEASE_LLM_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("DISEASE_GEMINI_LIVE", "1")
    settings = ProviderSettings.from_environment(cfg)
    assert settings.api_key_env == "GROQ_API_KEY" and not settings.live_enabled
    monkeypatch.setenv("DISEASE_GROQ_LIVE", "1")
    assert ProviderSettings.from_environment(cfg).live_enabled
    assert cfg.read_bytes() == original


@pytest.mark.parametrize("provider,model,key", [
    ("gemini", "openai/gpt-oss-20b", "GEMINI_API_KEY"),
    ("groq", "gemini-3.5-flash-lite", "GROQ_API_KEY"),
    ("groq", "openai/gpt-oss-20b", "GEMINI_API_KEY"),
    ("unknown", "any", "GROQ_API_KEY"),
])
def test_invalid_provider_model_or_credential_pair_fails_closed(provider, model, key):
    with pytest.raises(ValueError): ProviderSettings(provider=provider, model=model, api_key_env=key)


def test_flash_lite_uses_existing_gemini_adapter_without_changing_default(monkeypatch):
    monkeypatch.setenv("DISEASE_LLM_MODEL", "gemini-3.5-flash-lite")
    cfg = ProviderSettings.from_environment(ROOT / "configs/phase5b.json")
    assert cfg.model == "gemini-3.5-flash-lite" and isinstance(module.create_provider(cfg), module.GeminiProvider)
    assert module.create_provider(cfg).provider_name == "gemini"


def test_groq_requires_reviewed_strict_mode_and_matching_adapter():
    with pytest.raises(ValueError): groq_settings(schema_mode="json_only")
    with pytest.raises(ValueError): module.GeminiProvider(groq_settings())


def test_groq_strict_body_canonical_result_and_usage(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    catalog = Catalog.load(ROOT); validator = ExtractionValidator(catalog)
    turn = Turn("u1", "user", "Tôi ho và sốt từ sáng nay.", "self")
    canonical = extraction(catalog, [turn], [("cough", "present", "ho", "u1"), ("fever", "present", "sốt", "u1")])
    calls = []
    def transport(body, key, timeout):
        calls.append(deepcopy(body))
        assert key == "offline-groq-fixture"
        assert body["model"] == "openai/gpt-oss-20b" and not body["stream"]
        assert "generation_config" not in body and "max_completion_tokens" in body
        contract = body["response_format"]["json_schema"]
        assert contract["strict"] is True and body["response_format"]["type"] == "json_schema"
        payload = json.loads(body["messages"][1]["content"])
        assert list(payload["allowed_features"].values()) == list(catalog.features)
        assert contract["schema"] == module._serving_schema(validator.schema, task="extraction")
        reverse = {v: k for k, v in payload["allowed_features"].items()}
        coded = deepcopy(canonical)
        for item in coded["present"]: item["feature"] = reverse[item["feature"]]
        return response(coded)
    adapter = module.create_provider(groq_settings(), transport=transport)
    reply = adapter.generate(task="extraction", system=SYSTEM,
        payload={"allowed_features": list(catalog.features), "turns": [turn.__dict__]}, schema=validator.schema)
    assert reply.data == canonical
    frame = validator.frame(validator.validate(reply.data, [turn], "self"))
    assert frame.shape == (1, 375) and list(frame.columns) == list(catalog.features)
    assert frame["cough"].iat[0] == frame["fever"].iat[0] == 1
    stat = reply.telemetry[0]
    assert stat["provider"] == "groq" and stat["usage"]["total_input_tokens"] == 30
    assert stat["usage"]["total_output_tokens"] == 15 and stat["usage"]["total_tokens"] == 45
    assert "total_thought_tokens" not in stat["usage"] and stat["reported_cost"] is None
    assert len(calls) == 1


@pytest.mark.parametrize("finish,content", [("length", "{}"), ("content_filter", "{}"), ("stop", "not JSON")])
def test_groq_parser_rejects_incomplete_or_invalid_response(monkeypatch, finish, content):
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    raw = response({});raw["choices"][0].update(finish_reason=finish)
    raw["choices"][0]["message"]["content"] = content
    with pytest.raises(ProviderError):
        module.create_provider(groq_settings(), transport=lambda *a: raw).generate(task="intent", system="JSON", payload={}, schema={})


@pytest.mark.parametrize("field,value", [("refusal", "blocked"), ("tool_calls", [{"type":"function"}])])
def test_groq_refusal_or_tool_call_cannot_be_used_as_an_extraction(monkeypatch, field, value):
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    raw=response({"ok":True});raw["choices"][0]["message"][field]=value
    with pytest.raises(ProviderError,match="incomplete_or_blocked_response"):
        module.create_provider(groq_settings(),transport=lambda *a:raw).generate(task="intent",system="JSON",payload={},schema={})


@pytest.mark.parametrize("code,expected", [(400,"schema_or_request_rejected"),(401,"authentication_failed"),
    (403,"access_denied"),(429,"rate_limited"),(503,"provider_unavailable")])
def test_groq_error_no_cross_provider_routing_or_secret_leak(monkeypatch, code, expected):
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    monkeypatch.setenv("GEMINI_API_KEY", "other-provider-fixture")
    monkeypatch.setattr(module, "_post", lambda *a: pytest.fail("must never route to Gemini"))
    calls=[]
    def transport(*args):
        calls.append(1)
        raise HTTPError("https://example.invalid", code, "private", {}, io.BytesIO(json.dumps({
            "error":{"message":"offline-groq-fixture unavailable"}}).encode()))
    with pytest.raises(ProviderError) as caught:
        module.create_provider(groq_settings(),transport=transport).generate(task="intent",system="JSON",payload={},schema={})
    assert len(calls)==1 and caught.value.code==expected
    assert "offline-groq-fixture" not in repr(caught.value.diagnostics)


@pytest.mark.parametrize("failure", ["503", "timeout", "success"])
def test_selected_provider_qualification_is_two_calls_at_most(monkeypatch, failure):
    from scripts.smoke_local_mvp import provider_qualification
    monkeypatch.setenv("DISEASE_LLM_PROVIDER", "groq")
    monkeypatch.setenv("DISEASE_LLM_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    monkeypatch.setenv("DISEASE_GROQ_LIVE", "1")
    monkeypatch.setenv("DISEASE_API_STORAGE_ROOT", str(ROOT))
    monkeypatch.setattr(module,"_post",lambda *a:pytest.fail("Gemini must not receive this text"))
    catalog=Catalog.load(ROOT);calls=[]
    def transport(body,key,timeout):
        calls.append(1)
        if failure=="timeout":raise TimeoutError()
        if failure=="503":raise HTTPError("https://example.invalid",503,"busy",{},io.BytesIO(b'{"error":{"message":"busy"}}'))
        if len(calls)==1:return response({"ok":True})
        payload=json.loads(body['messages'][1]['content']);turns=[Turn(**x) for x in payload['turns']]
        data=extraction(catalog,turns,[("cough","present","ho","u1"),("fever","present","sốt","u1")])
        reverse={v:k for k,v in payload['allowed_features'].items()}
        for x in data['present']:x['feature']=reverse[x['feature']]
        return response(data)
    monkeypatch.setattr(module,"_post_groq",transport)
    result=provider_qualification(allow_live=True)
    assert result['provider']=='groq' and result['automatic_retries']==0
    assert result['requests_used']==len(calls)==(2 if failure=='success' else 1)
    assert not result['predictions_called'] and result['end_to_end_live_status'].startswith('NOT VERIFIED')
    if failure=='success':assert result['status']=='PASS' and result['B']['vector_ready']
    else:assert result['B']['status']=='NOT RUN'


@pytest.mark.parametrize("busy", [False, True])
def test_http_chat_uses_only_explicit_groq_and_lr_scores_or_no_prediction(deployment, monkeypatch, busy):
    from fastapi.testclient import TestClient
    from app.backend.main import create_app
    service = get_service(deployment)
    monkeypatch.setenv("DISEASE_LLM_PROVIDER", "groq")
    monkeypatch.setenv("DISEASE_LLM_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("DISEASE_GROQ_LIVE", "1")
    monkeypatch.setenv("GROQ_API_KEY", "offline-groq-fixture")
    monkeypatch.setattr(module, "_post", lambda *a: pytest.fail("No cross-provider routing"))
    calls = []
    def transport(body, key, timeout):
        calls.append(1)
        if busy:raise HTTPError("https://example.invalid",503,"busy",{},io.BytesIO(b'{"error":{"message":"busy"}}'))
        payload=json.loads(body['messages'][1]['content']);turns=[Turn(**t) for t in payload['turns']]
        data=extraction(service.catalog,turns,[("cough","present","ho","u1"),("fever","present","sốt","u1")])
        reverse={v:k for k,v in payload['allowed_features'].items()}
        for x in data['present']:x['feature']=reverse[x['feature']]
        return response(data)
    monkeypatch.setattr(module,"_post_groq",transport)
    with TestClient(create_app(service_loader=lambda:service)) as client:
        health=client.get('/health').json()
        assert health['chat']['provider']=='groq' and health['chat']['output_token_limit_per_request']==2048
        reply=client.post('/api/v1/chat',json={'message':'Tôi ho và sốt từ sáng nay.'})
        assert len(calls)==1
        if busy:
            assert reply.status_code==503 and reply.json()['reason']=='provider_unavailable'
            assert reply.json()['predictions'] is None and not service._model.calls
        else:
            assert reply.status_code==200 and reply.json()['status']=='prediction_ready'
            assert [x['score_percent'] for x in reply.json()['predictions']['top3']]==[40,30,10]
            assert len(service._model.calls)==1


def test_groq_cannot_use_gemini_key_even_when_gemini_live_is_enabled(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY','offline-gemini-fixture')
    monkeypatch.setenv('DISEASE_GEMINI_LIVE','1')
    with pytest.raises(ProviderError,match='missing_api_key'):
        module.create_provider(groq_settings(),transport=lambda *a:pytest.fail('No credential for selected provider')).generate(
            task='intent',system='JSON',payload={},schema={})


def test_groq_http_transport_uses_only_fixed_endpoint_and_bearer_header(monkeypatch):
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):
            assert limit==1024*1024+1
            return json.dumps(response({'ok':True})).encode()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url==module.PROVIDER_ENDPOINTS['groq'] and request.method=='POST'
            assert request.get_header('Authorization')=='Bearer offline-groq-fixture'
            assert request.get_header('X-goog-api-key') is None
            assert b'offline-groq-fixture' not in request.data and timeout==20
            return Response()
    def opener(handler):
        assert handler.redirect_request(None,None,None,None,None,None) is None
        return Opener()
    monkeypatch.setattr(module,'build_opener',opener)
    assert module._post_groq({'model':'openai/gpt-oss-20b'},'offline-groq-fixture',20)['_http_status']==200


@pytest.mark.parametrize("case", ["denied", "uncertain", "unknown", "conflict"])
def test_groq_states_and_unknowns_still_use_original_validator(monkeypatch, case):
    from src.agent.extraction import ExtractionError
    monkeypatch.setenv('GROQ_API_KEY','offline-groq-fixture')
    catalog=Catalog.load(ROOT);validator=ExtractionValidator(catalog)
    texts={'denied':'Tôi ho nhưng không sốt.','uncertain':'Tôi ho nhưng chưa chắc có sốt.',
           'unknown':'Tôi ho và sốt.','conflict':'Tôi ho và sốt.'}
    turn=Turn('u1','user',texts[case],'self')
    state=case if case in {'denied','uncertain'} else 'present'
    quote={'denied':'không sốt','uncertain':'chưa chắc có sốt'}.get(case,'sốt')
    data=extraction(catalog,[turn],[('cough','present','ho','u1'),('fever',state,quote,'u1')])
    codes=module._feature_codes(validator.schema,task='extraction');reverse={v:k for k,v in codes.items()}
    for name in ('present','denied','uncertain'):
        for item in data[name]:item['feature']=reverse[item['feature']]
    if case=='unknown':data['present'][0]['feature']='f375'
    if case=='conflict':data['denied']=[deepcopy(data['present'][0])]
    adapter=module.create_provider(groq_settings(),transport=lambda *a:response(data))
    args=dict(task='extraction',system=SYSTEM,payload={'allowed_features':list(catalog.features)},schema=validator.schema)
    if case=='unknown':
        with pytest.raises(ProviderError,match='invalid_feature_code'):adapter.generate(**args)
    elif case=='conflict':
        with pytest.raises(ExtractionError):validator.validate(adapter.generate(**args).data,[turn],'self')
    else:
        value=validator.validate(adapter.generate(**args).data,[turn],'self')
        assert value.states['fever']==state and validator.gate(value) in {'insufficient','uncertain'}
        with pytest.raises(ExtractionError,match='quality_gate_blocked'):validator.frame(value)
