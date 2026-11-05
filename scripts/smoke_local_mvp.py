"""Explicit, bounded smokes. No fit, locked test, credentials output or artifact writes.

Run from the project root: python -B -m scripts.smoke_local_mvp --ml
or --gemini-live (requires DISEASE_GEMINI_LIVE=1 and GEMINI_API_KEY).
--provider-qualification selects exactly the configured provider/model. Live use
also requires --allow-live-diagnostic, that provider's key and its live flag.
"""
import argparse
import json
import os
from pathlib import Path
from contextlib import contextmanager, nullcontext


@contextmanager
def transport_trace():
    """CLI-only phase timings. Never retain request headers, body, URL or key."""
    import http.client
    import time
    import urllib.request
    from unittest.mock import patch
    events, started = [], time.perf_counter()
    def mark(event, **values):
        if len(events) < 20:
            events.append({"event": event, "elapsed_ms": (time.perf_counter() - started) * 1000, **values})
    original = http.client.HTTPSConnection
    class TimedHTTPSConnection(original):
        def connect(self):
            mark("connect_tls_started")
            super().connect()
            mark("connect_tls_completed")
        def send(self, data):
            size = len(data) if isinstance(data, (bytes, bytearray, str)) else None
            mark("send_started", bytes=size)
            super().send(data)
            mark("send_completed", bytes=size)
        def getresponse(self):
            mark("response_headers_wait_started")
            response = super().getresponse()
            mark("response_headers_received", http_status=response.status)
            return response
    original_open = urllib.request.HTTPSHandler.do_open
    def traced_open(handler, connection_class, request, **kwargs):
        return original_open(handler, TimedHTTPSConnection if connection_class is original else connection_class,
                             request, **kwargs)
    # Do not replace http.client.HTTPSConnection: Python3.11 uses that global
    # in explicit super() calls. Keep normal TLS/proxy kwargs from HTTPSHandler.
    with patch.object(urllib.request.HTTPSHandler, "do_open", traced_open):
        yield events


def ml_smoke():
    from fastapi.testclient import TestClient
    from app.backend.main import create_app
    with TestClient(create_app()) as client:
        health = client.get("/health")
        if health.status_code != 200 or health.json().get("checkpoint_status") != "REAL CHECKPOINT VERIFIED":
            return {"stage": "real_checkpoint", "status": "BLOCKED", "health": health.json(),
                    "test_payload_opened": False, "models_fitted": 0}
        result = client.post("/api/v1/predict", json={"present_features": ["cough", "fever"]})
        if result.status_code != 200:
            return {"stage": "real_checkpoint", "status": "BLOCKED", "response": result.json()}
        return {"stage": "real_checkpoint", "status": "PASS", "health": health.json(),
                "synthetic_input_without_ground_truth": True, "prediction": result.json(),
                "test_payload_opened": False, "models_fitted": 0}


def gemini_smoke(*, diagnostic=False, timeout_seconds=None):
    from dataclasses import replace
    from jsonschema import Draft202012Validator
    from app.backend.chat import BoundedGemini
    from app.backend.prediction import PROJECT_ROOT
    from src.agent.conversation import ConversationEngine, Policy
    from src.agent.extraction import Catalog, extraction_schema
    from src.agent.provider import ProviderSettings
    settings = ProviderSettings.from_environment(PROJECT_ROOT / "configs/phase5b.json")
    if settings.provider != "gemini":
        return {"stage": "gemini_live", "status": "NOT VERIFIED", "reason": "use_provider_qualification_for_selected_provider", "requests": 0}
    if timeout_seconds is not None:
        settings = replace(settings, timeout_seconds=timeout_seconds)
    if not settings.live_enabled or not os.environ.get(settings.api_key_env, "").strip():
        return {"stage": "gemini_live", "status": "NOT VERIFIED", "reason": "live_opt_in_or_api_key_missing",
                "requests": 0, "provider_reported_usage": None}
    storage = Path(os.environ["DISEASE_API_STORAGE_ROOT"]) if os.environ.get("DISEASE_API_STORAGE_ROOT") else PROJECT_ROOT
    try:
        catalog = Catalog.load(PROJECT_ROOT, storage)
        schema = extraction_schema(catalog)
        Draft202012Validator.check_schema(schema)
    except Exception:
        return {"stage": "gemini_live", "status": "NOT VERIFIED", "reason": "schema_metadata_unavailable", "requests": 0}
    provider = BoundedGemini(settings, max_requests=1 if diagnostic else 6)
    engine = ConversationEngine(catalog, provider, Policy.from_file(PROJECT_ROOT / "configs/phase5b.json"))
    cases = (["Tôi ho và sốt từ sáng nay"] if diagnostic else
             ["Tôi ho và sốt.", "Tôi sửa lại: hiện tôi ho nhưng chưa chắc có sốt.", "Không."])
    records, session = [], None
    with (transport_trace() if diagnostic else nullcontext([])) as trace:
        for text in cases:
            result = engine.handle(text, session_id=session)
            session = result.session_id
            records.append({"status": result.status, "reason": result.reason,
                            "states": (result.sidecar or {}).get("states", {}), "telemetry": result.telemetry})
            if result.status in {"provider_error", "abstained", "urgent_redirect"}:
                break
    passed = (len(records) == 3 and records[0]["status"] == "extraction_ready"
              and records[0]["states"].get("cough") == records[0]["states"].get("fever") == "present"
              and records[1]["status"] == "clarification_required" and records[1]["states"].get("fever") == "uncertain"
              and records[2]["status"] == "clarification_required" and records[2]["states"].get("fever") == "denied")
    vector_check = None
    if diagnostic:
        passed = (len(records) == 1 and records[0]["status"] == "extraction_ready"
                  and records[0]["states"].get("cough") == records[0]["states"].get("fever") == "present")
        if passed:
            frame = engine.ready_vector(result.session_id, result.turn_id)
            vector_check = (frame.shape == (1, 375) and frame.columns.tolist() == list(catalog.features)
                            and frame.isin([0, 1]).all().all())
            passed = bool(vector_check)
    return {"stage": "gemini_live", "status": "PASS" if passed else "NOT VERIFIED", "model": settings.model,
            "feature_allowlist_count": len(catalog.features), "cases": records, "budget": provider.status(),
            "diagnostic": provider.last_error if diagnostic else None,
            "timeout_seconds": settings.timeout_seconds, "validated_vector_1x375": bool(vector_check) if diagnostic else None,
            "transport_trace": trace if diagnostic else None,
            "predictions_called": False, "models_fitted": 0, "test_payload_opened": False,
            "semantic_quality_note": "Synthetic mechanics only; not extraction accuracy or clinical validation."}


def provider_qualification(*, allow_live=False, timeout_seconds=60, required_provider=None):
    """Diagnostic only: no source/schema changes, model load, prediction or disk writes.

    A/B share the existing transport and model. Each gets one attempt; any A
    failure stops B. Successful B is checked by the unchanged canonical validator.
    No automatic repair/fallback is performed, even on a serving-schema error.
    """
    from dataclasses import replace
    import hashlib
    import time
    from jsonschema import Draft202012Validator
    from src.agent import provider as provider_module
    from src.agent.provider import create_provider, provider_transport, PROVIDER_ENDPOINTS, ProviderSettings, ProviderError
    from src.agent.extraction import Catalog, ExtractionValidator, ExtractionError, Turn
    from src.agent.conversation import SYSTEM, InputGuard, Policy

    root = Path(__file__).resolve().parents[1]
    cfg = ProviderSettings.from_environment(root / "configs/phase5b.json")
    if timeout_seconds not in (20, 60):
        raise ValueError("diagnostic_timeout_must_be_20_or_60")
    cfg = replace(cfg, max_retries=0, max_output_tokens=min(cfg.max_output_tokens, 2048),
                  timeout_seconds=timeout_seconds)
    result = {"stage": "provider_qualification", "status": "BLOCKED", "provider": cfg.provider, "model": cfg.model,
              "endpoint": PROVIDER_ENDPOINTS[cfg.provider],
              "request_limit": 2, "requests_used": 0, "automatic_retries": 0,
              "live_enabled": cfg.live_enabled,
              "key_configured": bool(os.environ.get(cfg.api_key_env, "").strip()),
              "explicit_diagnostic_opt_in": allow_live is True,
              "timeout_seconds_per_request": timeout_seconds,
              "output_token_limit_per_request": cfg.max_output_tokens,
              "A": {"status": "NOT RUN"}, "B": {"status": "NOT RUN"},
              "first_failing_stage": None, "models_fitted": 0, "predictions_called": False,
              "test_payload_opened": False,
              "end_to_end_live_status": "NOT VERIFIED; no LR prediction or HTTP chat call"}
    if required_provider is not None and cfg.provider != required_provider:
        result.update(reason="use_provider_qualification_for_selected_provider", first_failing_stage="configuration")
        return result
    if cfg.schema_mode != "schema":
        result.update(reason="existing_schema_mode_is_not_schema", first_failing_stage="configuration")
        return result
    minimal = {"type": "object", "additionalProperties": False, "required": ["ok"],
               "properties": {"ok": {"type": "boolean"}}}
    try:
        storage = Path(os.environ.get("DISEASE_API_STORAGE_ROOT") or root)
        catalog = Catalog.load(root, storage)
        validator = ExtractionValidator(catalog)
        wire = provider_module._serving_schema(validator.schema, task="extraction")
        for schema in (minimal, wire):
            Draft202012Validator.check_schema(schema)
        result.update(feature_allowlist_count=len(catalog.features),
                      wire_schema_sha256=hashlib.sha256(json.dumps(
                          wire, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                      local_schema_valid=True, provider_acceptance="NOT VERIFIED")
    except Exception:
        result.update(reason="schema_metadata_unavailable", first_failing_stage="local_preflight")
        return result
    if not (allow_live is True and cfg.live_enabled and result["key_configured"]):
        result.update(reason="diagnostic_opt_in_or_live_env_or_key_missing", first_failing_stage="live_prerequisites")
        return result

    def structure(value, field=None, depth=0):
        # Keys/values from the upstream response can themselves be untrusted.
        # Show only known envelope fields and types, never text or unknown names.
        known = {"status", "steps", "content", "type", "text", "usage", "id", "choices", "message",
                 "finish_reason", "refusal", "prompt_tokens", "completion_tokens", "completion_tokens_details", "reasoning_tokens",
                 "total_input_tokens", "total_output_tokens", "total_tokens",
                 "total_thought_tokens", "total_cached_tokens", "total_tool_use_tokens"}
        if isinstance(value, dict) and depth < 5:
            return {"type": "object", "fields": {k: structure(v, k, depth + 1)
                    for k, v in value.items() if k in known},
                    "other_field_count": sum(k not in known for k in value)}
        if isinstance(value, list) and depth < 5:
            return {"type": "array", "count": len(value),
                    "sample_shapes": [structure(v, field, depth + 1) for v in value[:2]]}
        return type(value).__name__

    text = "Tôi ho và sốt từ sáng nay."
    turn = Turn("u1", "user", text, "self")
    policy = Policy.from_file(root / "configs/phase5b.json")
    guard = InputGuard(policy).check(text)
    if guard.intent != "symptom_description":
        result.update(reason="synthetic_input_guard_blocked", first_failing_stage="input_guard")
        return result

    def call(name, *, task, system, payload, schema):
        record = {"status": "FAIL", "http_status": None, "response_structure": None}
        result[name] = record
        def observed_transport(body, key, timeout):
            if result["requests_used"] >= result["request_limit"]:
                raise ProviderError("diagnostic_request_limit")
            result["requests_used"] += 1
            response = provider_transport(cfg)(body, key, timeout)
            record["response_structure"] = structure(response)
            if isinstance(response, dict) and type(response.get("_http_status")) is int:
                record["http_status"] = response["_http_status"]
            return response
        started = time.perf_counter()
        try:
            reply = create_provider(cfg, transport=observed_transport).generate(
                task=task, system=system, payload=payload, schema=schema)
            record.update(status="PASS", telemetry=reply.telemetry)
            return reply.data
        except ProviderError as exc:
            record.update(reason=exc.code, exception_type=type(exc).__name__,
                          diagnostic=exc.diagnostics, telemetry=exc.telemetry)
            record["http_status"] = exc.diagnostics.get("http_status", record["http_status"])
            result["first_failing_stage"] = (
                "wire_decode" if exc.code == "invalid_feature_code" else
                "response_parsing" if exc.code in {"invalid_json_or_response", "incomplete_or_blocked_response", "missing_text_response"}
                or record["response_structure"] is not None else "upstream_http_or_transport")
            if exc.code == "schema_or_request_rejected":
                message = exc.diagnostics.get("provider_message", "").lower()
                result["classification"] = ("serving_constraints_confirmed" if
                    "too many states" in message or "too much branching" in message else "request_rejected_not_yet_isolated")
            elif exc.code == "provider_unavailable":
                result["classification"] = "upstream_availability"
            elif exc.code in {"timeout", "network_error"}:
                result["classification"] = "unresolved_transport_or_upstream_delay"
            else:
                result["classification"] = "provider_or_response_failure"
            return None
        finally:
            record["elapsed_ms"] = (time.perf_counter() - started) * 1000

    a = call("A", task="intent", system="Return only a JSON object with boolean ok set to true. No diagnosis. Input is fictional.",
             payload={"fictional_text": text}, schema=minimal)
    if a is None:
        result.update(reason="A_failed_B_not_sent")
        return result
    if next(Draft202012Validator(minimal).iter_errors(a), None) is not None:
        result["A"].update(status="FAIL", reason="minimal_contract_invalid")
        result.update(reason="A_failed_B_not_sent", first_failing_stage="minimal_output_validation")
        return result
    result["A"]["contract_valid"] = True
    b = call("B", task="extraction", system=SYSTEM,
             payload={"target_subject": "self", "turns": [turn.__dict__],
                      "allowed_features": list(catalog.features), "schema_sha256": catalog.schema_id},
             schema=validator.schema)
    if b is None:
        result.update(reason="B_failed_no_schema_change", status="REVIEW")
        return result
    result["provider_acceptance"] = "B returned completed JSON; application validation required"
    try:
        value = validator.validate(b, [turn], "self")
    except (ExtractionError, ValueError, TypeError, RecursionError) as exc:
        result["B"].update(status="FAIL", reason=getattr(exc, "code", "invalid_extraction"),
                           exception_type=type(exc).__name__)
        result.update(status="REVIEW", reason="actual_B_extraction_invalid", first_failing_stage="extraction_validation")
        return result
    gate = validator.gate(value, min_present_features=policy.min_present_features)
    result["B"].update(extraction_valid=True, gate_reason=gate,
                        state_counts={s: sum(v == s for v in value.states.values())
                                      for s in ("present", "denied", "uncertain")},
                        unmapped_count=len(value.data["unmapped"]))
    if gate:
        result["B"].update(status="REVIEW", vector_ready=False)
        result.update(status="REVIEW", reason="quality_gate_blocked_no_prediction", first_failing_stage="quality_gate")
        return result
    frame = validator.frame(value, min_present_features=policy.min_present_features)
    result["B"]["vector_ready"] = (frame.shape == (1, 375) and
        frame.columns.tolist() == list(catalog.features) and bool(frame.isin([0, 1]).all().all()))
    result.update(status="PASS" if result["B"]["vector_ready"] else "REVIEW",
                  reason="extraction_only_checked_no_LR",
                  first_failing_stage=None if result["B"]["vector_ready"] else "vector_mapping")
    return result


def gemini_ab_diagnostic(*, allow_live=False, timeout_seconds=60):
    result = provider_qualification(allow_live=allow_live, timeout_seconds=timeout_seconds, required_provider="gemini")
    result["stage"] = "gemini_ab_diagnostic"
    return result


def _three_stage_qualification(provider, *, allow_live=False, no_web_requests=False, timeout_seconds=60, single_request=False, target_model=None):
    """A text -> B provider-supported JSON -> C unchanged validator. No LR.

    Deliberately separate from the existing two-stage A/B diagnostic. Only this
    orchestration varies; production provider, schema and configuration stay intact.
    """
    from dataclasses import replace
    import hashlib
    import socket
    import time
    from urllib.error import HTTPError, URLError
    from jsonschema import Draft202012Validator
    from src.agent import provider as pm
    from src.agent.extraction import Catalog, ExtractionValidator, ExtractionError, Turn
    from src.agent.conversation import Policy, InputGuard, SYSTEM

    is_openrouter = provider == "openrouter"
    model = (target_model or pm.OPENROUTER_FREE_MODEL) if is_openrouter else "openai/gpt-oss-20b"
    is_nemotron = is_openrouter and model == pm.OPENROUTER_NEMOTRON_MODEL
    acceptance = "json_schema_acceptance" if is_nemotron else "json_mode_acceptance" if is_openrouter else "strict_schema_acceptance"
    stage = "openrouter_429_diagnostic" if single_request else "nemotron_three_stage_qualification" if is_nemotron else f"{provider}_three_stage_qualification"
    result = dict(stage=stage, status="BLOCKED",
                  provider=provider, model=model, endpoint=pm.PROVIDER_ENDPOINTS[provider],
                  request_limit=1 if single_request else 3, requests_used=0, automatic_retries=0,
                  input_utf8_byte_limit_per_request=32768,
                  input_token_admission_upper_bound=33792,
                  token_bound_note="Conservative UTF-8 byte bound plus 1024 envelope tokens; not measured/billed usage",
                  output_token_limit_per_request=2048, timeout_seconds_per_request=timeout_seconds,
                  explicit_diagnostic_opt_in=allow_live is True,
                  no_concurrent_web_requests_confirmed=no_web_requests is True,
                  key_configured=bool(os.environ.get(pm.PROVIDER_KEYS[provider], "").strip()),
                  live_enabled=os.environ.get(pm.PROVIDER_LIVE_FLAGS[provider]) == "1",
                  A={"status": "NOT RUN"}, B={"status": "NOT RUN"}, C={"status": "NOT RUN"},
                  extraction_validator="NOT VERIFIED",
                  first_failing_stage="prerequisites", recommendation="NOT VERIFIED",
                  models_fitted=0, predictions_called=False, test_payload_opened=False,
                  end_to_end_live_status="NOT VERIFIED; no LR or website request", reported_cost=None)
    result[acceptance] = "NOT VERIFIED"
    if is_openrouter:
        result["schema_enforcement"] = "Python validator only; JSON mode is not strict JSON Schema"
    if is_nemotron:
        result.update(schema_enforcement="JSON Schema requested; Python validator mandatory; native strict NOT VERIFIED",
                      structured_output_format="json_schema", strict_requested=False, reasoning_requested_enabled=False)
    if single_request:
        if not is_openrouter:
            raise ValueError("single_request_diagnostic_is_openrouter_only")
        result["purpose"] = "one minimal availability/error observation only; no JSON/extraction qualification"
    root = Path(__file__).resolve().parents[1]
    try:
        cfg = pm.ProviderSettings.from_environment(root / "configs/phase5b.json")
        expected_mode = pm.OPENROUTER_MODEL_MODES.get(model) if is_openrouter else "schema"
        if (cfg.provider, cfg.model, cfg.schema_mode) != (provider, model, expected_mode):
            raise ValueError("wrong_selection")
        if timeout_seconds not in (20, 60):
            raise ValueError("invalid_timeout")
        cfg = replace(cfg, max_retries=0, max_output_tokens=2048, timeout_seconds=timeout_seconds)
    except ValueError:
        result["reason"] = ("explicit_openrouter_nemotron_selection_required" if is_nemotron else
                            "explicit_openrouter_free_gemma_selection_required" if is_openrouter else "explicit_groq_20b_schema_selection_required")
        return result
    if not (allow_live is True and no_web_requests is True and cfg.live_enabled and result["key_configured"]):
        result["reason"] = "live_opt_in_key_or_no_concurrent_web_confirmation_missing"
        return result

    # Metadata only. All local prerequisites checked BEFORE the first generation.
    minimal = {"type": "object", "properties": {"intent": {"type": "string"},
               "has_symptom": {"type": "boolean"}}, "required": ["intent", "has_symptom"],
               "additionalProperties": False}
    try:
        catalog = Catalog.load(root, Path(os.environ.get("DISEASE_API_STORAGE_ROOT") or root))
        validator = ExtractionValidator(catalog)
        policy = Policy.from_file(root / "configs/phase5b.json")
        wire = pm._serving_schema(validator.schema, task="extraction")
        for schema in (minimal, wire):
            Draft202012Validator.check_schema(schema)
        required_features = {"cough", "fever", "headache"} if is_openrouter else {"cough", "fever"}
        if len(catalog.features) != 375 or not required_features <= set(catalog.features):
            raise ValueError("feature_catalog_mismatch")
        text = "Tôi ho và sốt từ sáng nay, nhưng không đau đầu." if is_openrouter else "Tôi ho và sốt từ sáng nay."
        turn = Turn("u1", "user", text, "self")
        if InputGuard(policy).check(turn.text).intent != "symptom_description":
            raise ValueError("input_guard_blocked")
        result.update(feature_allowlist_count=375, local_schema_valid=True,
            wire_schema_sha256=hashlib.sha256(json.dumps(wire, ensure_ascii=False,
                sort_keys=True, separators=(",", ":")).encode()).hexdigest())
    except Exception:
        result.update(reason="local_metadata_or_guard_failure", first_failing_stage="local_preflight")
        return result

    # Bound each input including its schema/catalog at the transport boundary.
    payload = {"target_subject": "self", "turns": [turn.__dict__],
               "allowed_features": list(catalog.features), "schema_sha256": catalog.schema_id}
    adapter = pm.create_provider(cfg)
    a_body = {"model": cfg.model, "messages": [
        {"role": "system", "content": "Respond concisely in Vietnamese."},
        {"role": "user", "content": "Xin chào. Hãy trả lời đúng một câu ngắn."}],
        "max_completion_tokens": 2048, "stream": False}
    if is_openrouter:
        a_body = adapter._chat_body("Respond concisely in Vietnamese.", "Xin chào. Hãy trả lời đúng một câu ngắn.")
    if is_nemotron:
        a_body = adapter._chat_body("Trả lời ngắn gọn bằng tiếng Việt.", "Xin chào. Hãy trả lời bằng một câu ngắn.")
    b_body = adapter._request_body(system="Return only JSON describing this fictional symptom text. No diagnosis.",
        wire_payload={"fictional_text": turn.text}, payload={}, schema=minimal, task="intent")

    class StopDiagnostic(Exception):
        pass

    def fail(record, name, code, stage, diagnostics=None):
        record.update(status="FAIL", reason=code, diagnostic=diagnostics or {})
        result.update(status="BLOCKED", reason=code, first_failing_stage=f"{name}:{stage}")
        if is_openrouter and (diagnostics or {}).get("rate_limit_classification"):
            result["error_classification"] = diagnostics["rate_limit_classification"]

    def send(body, key, timeout, record):
        size = len(json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        record["input_utf8_bytes"] = size
        if size > result["input_utf8_byte_limit_per_request"] or result["requests_used"] >= result["request_limit"]:
            raise pm.ProviderError("diagnostic_budget_exceeded")
        result["requests_used"] += 1  # Failed/timeout attempts count, too.
        response = pm.provider_transport(cfg)(body, key, timeout)
        record["http_status"] = response.get("_http_status")
        record["usage"] = adapter._usage(response)
        if record["http_status"] != 200:
            raise pm.ProviderError("expected_http_200")
        if is_openrouter:
            record["error_envelope_present"] = isinstance(response.get("error"), dict)
            record["model_field_present"] = "model" in response
            record["choices_field_present"] = isinstance(response.get("choices"), list)
            if record["error_envelope_present"]:
                # OpenRouter can return a JSON error after HTTP 200 was committed.
                # Diagnose it BEFORE checking model identity. Reuse the bounded
                # redactor; never retain the raw envelope or invent an HTTP 400.
                import io
                error = HTTPError(pm.PROVIDER_ENDPOINTS[provider], record["http_status"], "provider_response_error", {},
                    io.BytesIO(json.dumps({"error": response["error"]}, ensure_ascii=False, allow_nan=False).encode("utf-8")))
                try:
                    diagnostics = pm._http_diagnostics(error, key, payload, provider=provider)
                finally:
                    error.close()
                raise pm.ProviderError("provider_response_error", diagnostics=diagnostics)
            actual = response.get("model")
            allowed = isinstance(actual, str) and actual in {model, model.removesuffix(":free")}
            record["actual_response_model"] = actual if allowed else "NOT RECORDED (unexpected/missing model)"
            upstream = response.get("provider")
            record["upstream_provider"] = upstream if isinstance(upstream, str) and upstream in pm.OPENROUTER_PUBLIC_PROVIDERS else "NOT RECORDED"
            if not allowed:
                raise pm.ProviderError("unexpected_response_model")
            choices = response.get("choices")
            if is_nemotron and isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
                message = choices[0].get("message")
                record["reasoning_fields_present"] = isinstance(message, dict) and any(k in message for k in ("reasoning", "reasoning_details"))
        return response

    # C's request is still built/sent by the EXISTING production adapter.
    # A temporary transport intercept only enforces budget and records safe metadata.
    def run(name, body=None):
        record = dict(status="FAIL", http_status=None, model=cfg.model, usage={}, reported_cost=None)
        result[name] = record
        started = time.perf_counter()
        try:
            if name == "C":
                observed = pm.create_provider(cfg, transport=lambda b, k, t: send(b, k, t, record))
                reply = observed.generate(task="extraction", system=SYSTEM, payload=payload, schema=validator.schema)
                record["telemetry"] = reply.telemetry
                record["provider_json_decoded"] = True
                return reply.data
            response = send(body, os.environ[cfg.api_key_env], cfg.timeout_seconds, record)
            choices = response.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise pm.ProviderError("invalid_response")
            choice = choices[0]
            message = choice.get("message")
            if (choice.get("finish_reason") != "stop" or not isinstance(message, dict)
                    or message.get("refusal") or message.get("tool_calls")):
                raise pm.ProviderError("incomplete_or_blocked_response")
            content = message.get("content")
            record["response_content_present"] = isinstance(content, str) and bool(content.strip())
            if not record["response_content_present"]:
                raise pm.ProviderError("missing_text_response")
            if name == "A":
                record["status"] = "PASS"
                return True
            value = pm.strict_json(content)
            if next(Draft202012Validator(minimal).iter_errors(value), None) is not None:
                raise pm.ProviderError("minimal_schema_invalid")
            record.update(status="PASS", **({"python_schema_valid": True} if is_openrouter else {"strict_schema_valid": True}))
            return value
        except HTTPError as exc:
            try:
                diagnostics = pm._http_diagnostics(exc, os.environ[cfg.api_key_env], payload, provider=cfg.provider)
                record["http_status"] = exc.code
                fail(record, name, "http_error", "provider_http", diagnostics)
            finally:
                exc.close()
        except (TimeoutError, socket.timeout):
            fail(record, name, "timeout", "transport_or_upstream")
        except URLError:
            fail(record, name, "network_error", "transport_or_upstream")
        except pm.ProviderError as exc:
            record["telemetry"] = exc.telemetry
            record["http_status"] = exc.diagnostics.get("http_status", record["http_status"])
            fail(record, name, exc.code, "provider_or_response", exc.diagnostics)
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            fail(record, name, "invalid_json_or_response", "response_validation")
        except Exception:
            # Do not expose transport exceptions/partial response bodies or retry.
            fail(record, name, "provider_failure", "transport_or_response")
        finally:
            record["elapsed_ms"] = (time.perf_counter() - started) * 1000
        raise StopDiagnostic()

    try:
        run("A", a_body)
        if single_request:
            result.update(status="PASS", first_failing_stage=None, reason="minimal_text_only; extraction_and_chat_still_NOT_VERIFIED")
            return result
        run("B", b_body)
        result[acceptance] = "B PASS; C extraction not yet verified"
        data = run("C")
        result[acceptance] = "B and C returned HTTP 200/completed JSON; C validation required"
        try:
            value = validator.validate(data, [turn], "self")
            result["extraction_validator"] = "PASS"
            result["C"].update(extraction_valid=True, state_counts={s: sum(v == s for v in value.states.values())
                for s in ("present", "denied", "uncertain")}, unmapped_count=len(value.data["unmapped"]))
            gate = validator.gate(value, min_present_features=policy.min_present_features)
            if gate:
                fail(result["C"], "C", gate, "quality_gate")
                return result
            frame = validator.frame(value, min_present_features=policy.min_present_features)
            vector = frame.iloc[0].to_numpy()
            confirmed = [f for f, state in value.states.items() if state == "present"]
            denied = [f for f, state in value.states.items() if state == "denied"]
            if (vector.shape != (375,) or frame.columns.tolist() != list(catalog.features)
                    or not frame.isin([0, 1]).all().all()
                    or set(confirmed) != {"cough", "fever"}
                    or is_openrouter and set(denied) != {"headache"}
                    or int(vector.sum()) != len(confirmed)):
                fail(result["C"], "C", "unexpected_synthetic_features_or_vector", "vector_mapping")
                return result
            result["C"].update(status="PASS", vector_shape=[375], frame_shape=[1, 375],
                confirmed_features=confirmed,
                confirmed_feature_codes=[f"f{catalog.features.index(f):03d}" for f in confirmed])
            if is_openrouter:
                result["C"].update(denied_features=denied,
                    denied_feature_codes=[f"f{catalog.features.index(f):03d}" for f in denied],
                    headache_vector_value=int(vector[catalog.features.index("headache")]))
        except (ExtractionError, ValueError, TypeError, RecursionError) as exc:
            result["extraction_validator"] = "FAIL"
            fail(result["C"], "C", getattr(exc, "code", "invalid_extraction"), "extraction_validation")
            return result
    except StopDiagnostic:
        return result
    result.update(status="PASS", first_failing_stage=None, recommendation="KEEP AS CANDIDATE",
                  reason="single_synthetic_extraction_only_not_accuracy_stability_or_quota")
    return result


def groq_three_stage_qualification(**kwargs):
    return _three_stage_qualification("groq", **kwargs)


def openrouter_three_stage_qualification(**kwargs):
    return _three_stage_qualification("openrouter", **kwargs)


def openrouter_429_diagnostic(**kwargs):
    """Future owner-authorized one-request probe, never run by offline diagnostics."""
    return _three_stage_qualification("openrouter", single_request=True, **kwargs)


def nemotron_three_stage_qualification(**kwargs):
    from src.agent.provider import OPENROUTER_NEMOTRON_MODEL
    return _three_stage_qualification("openrouter", target_model=OPENROUTER_NEMOTRON_MODEL, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ml", action="store_true")
    mode.add_argument("--gemini-live", action="store_true")
    mode.add_argument("--gemini-diagnostic", action="store_true", help="One synthetic request, no retry, redacted HTTP diagnostics")
    mode.add_argument("--gemini-ab-diagnostic", action="store_true", help="A: small schema; only if A passes, B: unchanged extraction; at most two requests")
    mode.add_argument("--provider-qualification", action="store_true", help="Qualify exactly the configured provider/model, minimal then extraction, at most two requests")
    mode.add_argument("--groq-three-stage", action="store_true", help="Groq 20B only: text, strict JSON, actual extraction; at most three requests, stop on first failure")
    mode.add_argument("--openrouter-three-stage", action="store_true", help="Free Gemma only: text, JSON object, actual extraction with denial; max three requests, no retry/fallback")
    mode.add_argument("--openrouter-429-diagnostic", action="store_true", help="Separately authorized future probe: one minimal text request only; never retries or runs B/C")
    mode.add_argument("--nemotron-three-stage", action="store_true", help="Nemotron 3.5 Super VL free only: text, JSON Schema (strict=false), extraction; max three requests, no retry/fallback")
    parser.add_argument("--confirm-no-web-requests", action="store_true", help="Owner confirms website requests are stopped during the diagnostic")
    parser.add_argument("--allow-live-diagnostic", action="store_true", help="Explicit opt-in for A/B, also requires live environment and key")
    parser.add_argument("--timeout-seconds", type=float, choices=(20, 60),
                        help="Diagnostic-only timeout override; never changes production config")
    args = parser.parse_args()
    if args.timeout_seconds is not None and not (args.gemini_diagnostic or args.gemini_ab_diagnostic or args.provider_qualification or args.groq_three_stage or args.openrouter_three_stage or args.openrouter_429_diagnostic or args.nemotron_three_stage):
        parser.error("--timeout-seconds is only supported with diagnostic modes")
    if args.allow_live_diagnostic and not (args.gemini_ab_diagnostic or args.provider_qualification or args.groq_three_stage or args.openrouter_three_stage or args.openrouter_429_diagnostic or args.nemotron_three_stage):
        parser.error("--allow-live-diagnostic requires an A/B qualification mode")
    if args.nemotron_three_stage:
        result = nemotron_three_stage_qualification(allow_live=args.allow_live_diagnostic,
            no_web_requests=args.confirm_no_web_requests, timeout_seconds=args.timeout_seconds or 60)
    elif args.openrouter_429_diagnostic:
        result = openrouter_429_diagnostic(allow_live=args.allow_live_diagnostic,
            no_web_requests=args.confirm_no_web_requests, timeout_seconds=args.timeout_seconds or 60)
    elif args.openrouter_three_stage:
        result = openrouter_three_stage_qualification(allow_live=args.allow_live_diagnostic,
            no_web_requests=args.confirm_no_web_requests, timeout_seconds=args.timeout_seconds or 60)
    elif args.groq_three_stage:
        result = groq_three_stage_qualification(allow_live=args.allow_live_diagnostic,
            no_web_requests=args.confirm_no_web_requests, timeout_seconds=args.timeout_seconds or 60)
    elif args.provider_qualification:
        result = provider_qualification(allow_live=args.allow_live_diagnostic, timeout_seconds=args.timeout_seconds or 60)
    elif args.gemini_ab_diagnostic:
        result = gemini_ab_diagnostic(allow_live=args.allow_live_diagnostic, timeout_seconds=args.timeout_seconds or 60)
    else:
        result = ml_smoke() if args.ml else gemini_smoke(diagnostic=args.gemini_diagnostic, timeout_seconds=args.timeout_seconds)
    print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
