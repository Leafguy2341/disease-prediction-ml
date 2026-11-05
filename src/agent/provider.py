"""Explicit stateless provider selection; no automatic routing, SDK or implicit live traffic."""
from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import re
import socket
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

PROVIDER_ENDPOINTS = {"gemini": "https://generativelanguage.googleapis.com/v1beta/interactions",
                      "groq": "https://api.groq.com/openai/v1/chat/completions",
                      "openrouter": "https://openrouter.ai/api/v1/chat/completions"}
PROVIDER_KEYS = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
PROVIDER_LIVE_FLAGS = {"gemini": "DISEASE_GEMINI_LIVE", "groq": "DISEASE_GROQ_LIVE",
                       "openrouter": "DISEASE_OPENROUTER_LIVE"}
GROQ_SCHEMA_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}
OPENROUTER_FREE_MODEL = "google/gemma-4-26b-a4b-it:free"
OPENROUTER_NEMOTRON_MODEL = "nvidia/nemotron-3.5-super-vl:free"
OPENROUTER_MODEL_MODES = {OPENROUTER_FREE_MODEL: "json_object", OPENROUTER_NEMOTRON_MODEL: "json_schema"}
OPENROUTER_PUBLIC_PROVIDERS = {"Google AI Studio", "google-ai-studio", "Google", "OpenRouter", "Nvidia", "NVIDIA", "nvidia"}


def strict_json(text: str) -> dict:
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise ValueError("duplicate_json_key")
            output[key] = value
        return output
    value = json.loads(text, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))
    if not isinstance(value, dict):
        raise ValueError("json_object_required")
    return value


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "gemini"
    model: str = "gemini-3.8-flash"
    api_key_env: str = "GEMINI_API_KEY"
    live_enabled: bool = False
    timeout_seconds: float = 20
    max_retries: int = 1
    retry_base_seconds: float = .25
    max_output_tokens: int = 8192
    schema_mode: str = "schema"

    def __post_init__(self):
        valid_model = (isinstance(self.model, str) and (
            self.provider == "gemini" and re.fullmatch(r"gemini-[a-zA-Z0-9._-]{1,80}", self.model)
            or self.provider == "groq" and self.model in GROQ_SCHEMA_MODELS
            or self.provider == "openrouter" and self.model in OPENROUTER_MODEL_MODES))
        if (self.provider not in PROVIDER_ENDPOINTS or not valid_model
                or self.api_key_env != PROVIDER_KEYS.get(self.provider)
                or type(self.live_enabled) is not bool or self.schema_mode not in {"schema", "json_only", "json_object", "json_schema"}
                or self.provider == "groq" and self.schema_mode != "schema"
                or self.provider == "openrouter" and self.schema_mode != OPENROUTER_MODEL_MODES.get(self.model)
                or self.provider == "gemini" and self.schema_mode in {"json_object", "json_schema"}
                or not 0 < self.timeout_seconds <= 60 or type(self.max_retries) is not int
                or not 0 <= self.max_retries <= 2 or not 0 <= self.retry_base_seconds <= 2
                or type(self.max_output_tokens) is not int or not 256 <= self.max_output_tokens <= 16384):
            raise ValueError("invalid_provider_configuration")

    @classmethod
    def from_file(cls, path: Path):
        return cls(**json.loads(Path(path).read_text(encoding="utf-8"))["provider"])

    @classmethod
    def from_environment(cls, path: Path):
        """A provider change requires an explicit model; keys/opt-in never cross providers."""
        values = dict(json.loads(Path(path).read_text(encoding="utf-8"))["provider"])
        selected = os.environ.get("DISEASE_LLM_PROVIDER", values["provider"])
        if selected not in PROVIDER_ENDPOINTS:
            raise ValueError("unsupported_provider_selection")
        model = os.environ.get("DISEASE_LLM_MODEL")
        if selected != values["provider"] and not model:
            raise ValueError("explicit_model_required_for_provider_change")
        if selected == "openrouter" and (selected != values["provider"] or model is not None):
            # Deliberate provider capability, NOT a retry/fallback from strict mode.
            # The on-disk Gemini/Groq configuration remains untouched.
            values["schema_mode"] = OPENROUTER_MODEL_MODES.get(model or values["model"], values["schema_mode"])
        values.update(provider=selected, model=model if model is not None else values["model"],
                      api_key_env=PROVIDER_KEYS[selected],
                      live_enabled=os.environ.get(PROVIDER_LIVE_FLAGS[selected]) == "1")
        return cls(**values)


@dataclass
class LLMReply:
    data: dict
    telemetry: list[dict] = field(default_factory=list)


class ProviderError(RuntimeError):
    """Code-only public errors; bounded redacted diagnostics stay out of chat replies."""
    def __init__(self, code: str, telemetry=(), diagnostics=None):
        self.code, self.telemetry = code, list(telemetry)
        self.diagnostics = dict(diagnostics or {})
        super().__init__(code)


def _openrouter_error_fields(error, detail, key):
    """Allowlists only: no raw metadata/headers/body, no automatic retry."""
    result = {}
    headers = getattr(error, "headers", None)
    if headers is not None:
        def header(name):
            value = headers.get(name) or headers.get(name.lower())
            return value if isinstance(value, str) and len(value) <= 64 and not any(c in value for c in "\r\n") else None
        rates = {}
        for name in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
            value = header(name)
            if value is not None and re.fullmatch(r"\d{1,16}(?:\.\d{1,6})?", value):
                rates[name] = value
        if rates:
            result["rate_limit_headers"] = rates
        value = header("Retry-After")
        if value is not None:
            if re.fullmatch(r"\d{1,10}", value):
                result["retry_after"] = value
            elif re.fullmatch(r"[A-Za-z]{3}, \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} GMT", value):
                from email.utils import parsedate_to_datetime
                try:
                    parsedate_to_datetime(value)
                    result["retry_after"] = value
                except (ValueError, TypeError, OverflowError):
                    pass
    # Typed status/machine vocabulary, never free-text health information.
    vocabulary = {"rate_limit_exceeded", "rate_limited", "too_many_requests", "RESOURCE_EXHAUSTED",
                  "insufficient_quota", "quota_exceeded", "daily_limit_exceeded", "model_rate_limit_exceeded",
                  "free_model_daily_limit_exceeded", "free_model_rpm_limit_exceeded", "server", "unavailable",
                  "openrouter_key_limit", "openrouter_guardrail_budget", "openrouter_workspace_budget",
                  "openrouter_credits", "openrouter_in_flight_budget", "in_flight_budget_exhausted",
                  "weight_exceeds_budget"}
    def machine(value):
        if type(value) is int and 100 <= value <= 599:
            return value
        if isinstance(value, str) and re.fullmatch(r"[1-5]\d\d", value) and value != key:
            return value
        if isinstance(value, str) and value in vocabulary and value != key:
            return value
        return None
    code = machine(detail.get("code"))
    if code is not None:
        result["provider_error_code"] = code
    metadata = detail.get("metadata")
    if isinstance(metadata, dict):
        safe = {}
        for name in ("provider_code", "error_type", "limit_source", "reason"):
            value = machine(metadata.get(name))
            if value is not None:
                safe[name] = value
        # Public name of this model's advertised route; don't forward arbitrary
        # provider-name text. Unknown names remain unrecorded, never guessed.
        value = metadata.get("provider_name")
        if isinstance(value, str) and value in OPENROUTER_PUBLIC_PROVIDERS and value != key:
            safe["provider_name"] = value
        if safe:
            result["provider_metadata"] = safe
    if error.code == 429:
        metadata = result.get("provider_metadata", {})
        upstream = metadata.get("provider_code") in {429, "429", "rate_limit_exceeded", "rate_limited", "too_many_requests", "RESOURCE_EXHAUSTED"}
        platform = metadata.get("limit_source") in {"openrouter_key_limit", "openrouter_guardrail_budget", "openrouter_workspace_budget"}
        headers_hint = bool(result.get("rate_limit_headers"))
        if upstream and (platform or headers_hint):
            classification = {"source": "unresolved", "confidence": "UNRESOLVED", "basis": "conflicting_attribution_hints"}
        elif upstream:
            classification = {"source": "upstream_provider", "confidence": "CONFIRMED", "basis": "reported_metadata.provider_code"}
        elif platform:
            classification = {"source": "openrouter_key_or_budget_policy", "confidence": "CONFIRMED", "basis": "reported_metadata.limit_source"}
        elif headers_hint:
            classification = {"source": "openrouter_platform", "confidence": "LIKELY", "basis": "rate_limit_headers; scope_not_proven"}
        elif metadata.get("provider_name") not in (None, "OpenRouter"):
            classification = {"source": "upstream_provider", "confidence": "LIKELY", "basis": "provider_name_only"}
        else:
            classification = {"source": "unresolved", "confidence": "UNRESOLVED", "basis": "HTTP_429_alone_does_not_identify_limit_source"}
        result["rate_limit_classification"] = classification
    return result


def _http_diagnostics(error, key, payload, *, provider=None):
    """Bounded redacted message; only OpenRouter adds validated metadata/header allowlists."""
    result = {"http_status": error.code}
    if provider == "openrouter":
        result.update(_openrouter_error_fields(error, {}, key))
    try:
        raw = error.read(16385)
        if len(raw) > 16384:
            return {**result, "error_body": "too_large"}
        detail = strict_json(raw.decode("utf-8")).get("error", {})
        if not isinstance(detail, dict):
            return result
        if provider == "openrouter":
            result.update(_openrouter_error_fields(error, detail, key))
        status = detail.get("status")
        if status in {"INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND",
                      "RESOURCE_EXHAUSTED", "FAILED_PRECONDITION", "UNAVAILABLE", "INTERNAL",
                      "DEADLINE_EXCEEDED"}:
            result["provider_status"] = status
        message = detail.get("message")
        if isinstance(message, str):
            # Diagnostics CLI uses synthetic inputs only. Also remove exact request text
            # before truncation, so an error echo cannot print a key or conversation turn.
            def strings(value):
                if isinstance(value, str):
                    yield value
                elif isinstance(value, dict):
                    for item in value.values(): yield from strings(item)
                elif isinstance(value, list):
                    for item in value: yield from strings(item)
            for secret in sorted({key, *strings(payload)}, key=len, reverse=True):
                if secret and (secret == key or len(secret) >= 4):
                    message = message.replace(secret, "[REDACTED]")
            message = re.sub(r"AIza[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
            message = re.sub(r"gsk_[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
            message = re.sub(r"sk-or-[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
            message = re.sub(r"https?://[^\s]+", "[REDACTED_URL]", message)
            message = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", message)
            result["provider_message"] = " ".join(message.split())[:1200]
    except (ValueError, TypeError, UnicodeError, OSError, RecursionError, AttributeError):
        pass  # Even a broken/non-JSON error must preserve its HTTP status.
    return result


def _feature_codes(schema, *, task):
    """A reversible wire encoding of ALL features, never an ML schema change."""
    if task != "extraction" or schema.get("properties", {}).get("contract_version", {}).get("const") != 2:
        return {}
    features = schema.get("$defs", {}).get("feature", {}).get("enum", [])
    if (len(features) != 375 or any(not isinstance(f, str) for f in features)
            or len(set(features)) != 375):
        raise ProviderError("feature_catalog_mismatch")
    return {f"f{i:03d}": name for i, name in enumerate(features)}


def _serving_schema(schema, *, task):
    """Short enum tokens reduce serving complexity; every feature remains allowed.

    The original canonical schema, bounds and Python validator stay unchanged.
    Decoded output uses canonical feature names before application validation.
    """
    wire = deepcopy(schema)
    codes = _feature_codes(schema, task=task)
    if codes:
        wire["$defs"]["feature"]["enum"] = list(codes)
    return wire


def _decode_features(data, codes):
    """Exact dictionary lookup only; unknown codes fail before inference."""
    if not codes:
        return data
    result = deepcopy(data)
    def decode(code):
        if not isinstance(code, str) or code not in codes:
            raise ProviderError("invalid_feature_code")
        return codes[code]
    for name in ("present", "denied", "uncertain"):
        if name in result:
            if not isinstance(result[name], list):
                raise ProviderError("invalid_feature_code")
            for item in result[name]:
                if not isinstance(item, dict) or "feature" not in item:
                    raise ProviderError("invalid_feature_code")
                item["feature"] = decode(item["feature"])
    clarification = result.get("clarification")
    if isinstance(clarification, dict) and "target_features" in clarification:
        if not isinstance(clarification["target_features"], list):
            raise ProviderError("invalid_feature_code")
        clarification["target_features"] = [decode(c) for c in clarification["target_features"]]
    return result


class LLMProvider(Protocol):
    def generate(self, *, task: str, system: str, payload: dict, schema: dict) -> LLMReply: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward an API-key header to a redirect target.


def _post(body: dict, key: str, timeout: float) -> dict:
    request = Request(PROVIDER_ENDPOINTS["gemini"],
                      data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"),
                      headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST")
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        raw = response.read(1024 * 1024 + 1)
        http_status = getattr(response, "status", None)
    if len(raw) > 1024 * 1024:
        raise ValueError("response_too_large")
    result = strict_json(raw.decode("utf-8"))
    if type(http_status) is int:
        result["_http_status"] = http_status  # Local transport metadata, never sent to Gemini.
    return result


def _post_groq(body: dict, key: str, timeout: float) -> dict:
    request = Request(PROVIDER_ENDPOINTS["groq"],
                      data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"),
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        raw = response.read(1024 * 1024 + 1)
        status = getattr(response, "status", None)
    if len(raw) > 1024 * 1024:
        raise ValueError("response_too_large")
    result = strict_json(raw.decode("utf-8"))
    if type(status) is int:
        result["_http_status"] = status
    return result


def provider_transport(settings):
    return {"gemini": _post, "groq": _post_groq, "openrouter": _post_openrouter}[settings.provider]


def _post_openrouter(body: dict, key: str, timeout: float) -> dict:
    """Bounded fixed-endpoint request. No SDK retry, redirect or credential logging."""
    payload = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(payload) > 64000:
        raise ProviderError("local_request_size_limit")
    request = Request(PROVIDER_ENDPOINTS["openrouter"], data=payload,
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        raw = response.read(1024 * 1024 + 1)
        status = getattr(response, "status", None)
    if len(raw) > 1024 * 1024:
        raise ProviderError("response_too_large")
    result = strict_json(raw.decode("utf-8"))
    if type(status) is int:
        result["_http_status"] = status
    return result


class GeminiProvider:
    """Transport/sleep are injectable for offline tests; JSON fallback is explicit."""
    provider_name = "gemini"

    def __init__(self, settings: ProviderSettings, *, transport=None, sleep=time.sleep, clock=time.perf_counter):
        if settings.provider != self.provider_name:
            raise ValueError("provider_adapter_mismatch")
        self.settings = settings
        self._transport, self._sleep, self._clock = transport or _post, sleep, clock

    def _request_body(self, *, system, wire_payload, payload, schema, task):
        cfg = self.settings
        body = {"model": cfg.model, "system_instruction": system, "store": False, "stream": False,
                "generation_config": {"max_output_tokens": cfg.max_output_tokens},
                "input": json.dumps(wire_payload, ensure_ascii=False, allow_nan=False),
                "response_format": {"type": "text", "mime_type": "application/json"}}
        if cfg.schema_mode == "schema":
            body["response_format"]["schema"] = _serving_schema(schema, task=task)
        else:
            body["input"] = json.dumps({**payload, "output_contract": schema}, ensure_ascii=False, allow_nan=False)
        return body

    def _usage(self, response):
        usage = response.get("usage", {})
        return {name: value for name, value in usage.items()
                if name in {"total_input_tokens", "total_output_tokens", "total_cached_tokens",
                            "total_thought_tokens", "total_tokens", "total_tool_use_tokens"}
                and type(value) is int and value >= 0}

    def _response_data(self, response, codes):
        if response.get("status") != "completed":
            raise ProviderError("incomplete_or_blocked_response")
        texts = [item["text"] for step in response.get("steps", []) if step.get("type") == "model_output"
                 for item in step.get("content", []) if item.get("type") == "text" and isinstance(item.get("text"), str)]
        if not texts:
            raise ProviderError("missing_text_response")
        return _decode_features(strict_json("".join(texts)), codes)

    def _http_error_code(self, status):
        return {400: "schema_or_request_rejected", 401: "authentication_failed", 403: "access_denied",
                404: "model_unavailable", 429: "rate_limited", 503: "provider_unavailable"}.get(status, "http_error")

    def generate(self, *, task, system, payload, schema):
        cfg = self.settings
        if task not in {"intent", "extraction"}:
            raise ProviderError("unsupported_task")
        if not cfg.live_enabled:
            raise ProviderError("live_disabled")
        key = os.environ.get(cfg.api_key_env)
        if not key or not key.strip():
            raise ProviderError("missing_api_key")
        codes = _feature_codes(schema, task=task) if cfg.schema_mode in {"schema", "json_object", "json_schema"} else {}
        wire_payload = payload
        if codes:
            if payload.get("allowed_features") != list(codes.values()):
                raise ProviderError("feature_catalog_mismatch")
            wire_payload = {**payload, "allowed_features": codes}
            system += ("\nWire encoding: allowed_features maps short IDs to the exact canonical feature names. "
                       "In feature and clarification.target_features output ONLY dictionary keys (IDs); "
                       "the Python adapter restores canonical names. All 375 features are available. "
                       "Keep evidence quotes and Unicode offsets unchanged.")
        body = self._request_body(system=system, wire_payload=wire_payload, payload=payload, schema=schema, task=task)
        telemetry = []
        for attempt in range(cfg.max_retries + 1):
            started = self._clock()
            stat = {"task": task, "provider": cfg.provider, "model": cfg.model, "attempt": attempt + 1,
                    "retry_count": attempt, "schema_mode": cfg.schema_mode, "usage_kind": "unknown",
                    "usage": {}, "reported_cost": None, "cost_kind": "unknown", "ttft_ms": None}
            stat["feature_encoding"] = "catalog_codes_v1" if codes else "canonical_names"
            if cfg.provider == "openrouter":
                stat["schema_enforcement"] = ("json_schema_requested_python_validated" if cfg.schema_mode == "json_schema" else "python_validator_only")
                if cfg.schema_mode == "json_schema":
                    stat["strict_requested"] = False
            retry = False
            diagnostics = {}
            try:
                response = self._transport(body, key, cfg.timeout_seconds)
                if type(response.get("_http_status")) is int:
                    stat["http_status"] = response["_http_status"]
                stat["usage"] = self._usage(response)
                stat["usage_kind"] = "provider_reported" if stat["usage"] else "unknown"
                data = self._response_data(response, codes)
                stat.update(outcome="ok", latency_ms=max(0, self._clock() - started) * 1000)
                telemetry.append(stat)
                return LLMReply(data, telemetry)
            except HTTPError as exc:
                retry = exc.code in {408, 429, 500, 502, 503, 504}
                code = self._http_error_code(exc.code)
                try:
                    diagnostics = _http_diagnostics(exc, key, payload, provider=cfg.provider)
                    stat.update({k: v for k, v in diagnostics.items() if k in {"http_status", "provider_status"}})
                finally:
                    exc.close()
            except (TimeoutError, socket.timeout):
                code, retry = "timeout", True
            except URLError:
                code, retry = "network_error", True
            except ProviderError as exc:
                code = exc.code
                diagnostics = exc.diagnostics
            except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
                code = "invalid_json_or_response"
            except Exception:
                code = "provider_failure"
            stat.update(outcome=code, latency_ms=max(0, self._clock() - started) * 1000)
            telemetry.append(stat)
            if not retry or attempt == cfg.max_retries:
                raise ProviderError(code, telemetry, diagnostics) from None
            self._sleep(cfg.retry_base_seconds * (2 ** attempt) + random.uniform(0, .05))
        raise AssertionError("unreachable")


class GroqProvider(GeminiProvider):
    """Groq Chat Completions; shares canonical decoding/error bounds, never falls back."""
    provider_name = "groq"

    def __init__(self, settings, *, transport=None, **kwargs):
        super().__init__(settings, transport=transport or _post_groq, **kwargs)

    def _request_body(self, *, system, wire_payload, payload, schema, task):
        cfg = self.settings
        fmt = {"type": "json_schema", "json_schema": {
            "name": "symptom_extraction" if task == "extraction" else "intent_result",
            "strict": True, "schema": _serving_schema(schema, task=task)}}
        return {"model": cfg.model, "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(wire_payload, ensure_ascii=False, allow_nan=False)}],
                "response_format": fmt, "max_completion_tokens": cfg.max_output_tokens,
                "stream": False}

    def _usage(self, response):
        usage = response.get("usage", {})
        names = {"prompt_tokens": "total_input_tokens", "completion_tokens": "total_output_tokens",
                 "total_tokens": "total_tokens"}
        result = {target: usage[source] for source, target in names.items()
                  if type(usage.get(source)) is int and usage[source] >= 0}
        details = usage.get("completion_tokens_details", {})
        if isinstance(details, dict) and type(details.get("reasoning_tokens")) is int and details["reasoning_tokens"] >= 0:
            result["total_thought_tokens"] = details["reasoning_tokens"]
        return result

    def _response_data(self, response, codes):
        choices = response.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ProviderError("invalid_json_or_response")
        choice = choices[0]
        message = choice.get("message")
        if choice.get("finish_reason") != "stop" or not isinstance(message, dict):
            raise ProviderError("incomplete_or_blocked_response")
        if message.get("refusal") or message.get("tool_calls"):
            raise ProviderError("incomplete_or_blocked_response")
        text = message.get("content")
        if not isinstance(text, str):
            raise ProviderError("missing_text_response")
        return _decode_features(strict_json(text), codes)


class OpenRouterProvider(GroqProvider):
    """Explicit free-model capabilities; native strict enforcement is never assumed."""
    provider_name = "openrouter"

    def __init__(self, settings, *, transport=None, **kwargs):
        # Even a direct caller cannot enable retries for this qualification adapter.
        if settings.max_retries:
            from dataclasses import replace
            settings = replace(settings, max_retries=0)
        super().__init__(settings, transport=transport or _post_openrouter, **kwargs)

    def _chat_body(self, system, user):
        body = {"model": self.settings.model, "messages": [
                    {"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": self.settings.max_output_tokens, "stream": False,
                "provider": {"allow_fallbacks": False, "require_parameters": True,
                             "max_price": {"prompt": 0, "completion": 0, "request": 0}}}
        if self.settings.model == OPENROUTER_NEMOTRON_MODEL:
            # Declared before qualification: do not spend the small output cap on
            # hidden reasoning. Returned reasoning is never parsed as content.
            body["reasoning"] = {"enabled": False}
        return body

    def _request_body(self, *, system, wire_payload, payload, schema, task):
        wire = _serving_schema(schema, task=task)
        if self.settings.schema_mode == "json_schema":
            body = self._chat_body(system, json.dumps(wire_payload, ensure_ascii=False, allow_nan=False))
            # Endpoint metadata advertises structured_outputs, not a native
            # strict guarantee. No retry/downgrade on schema rejection.
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "symptom_extraction" if task == "extraction" else "intent_result",
                "strict": False, "schema": wire}}
            return body
        user = json.dumps({**wire_payload, "output_contract": wire}, ensure_ascii=False, allow_nan=False)
        body = self._chat_body(system + "\nReturn exactly one JSON object matching output_contract. "
                               "No Markdown fences, extra fields, disease labels or scores. "
                               "JSON mode does not enforce the contract; Python will reject violations.", user)
        body["response_format"] = {"type": "json_object"}
        return body

    def _http_error_code(self, status):
        return {500: "provider_internal_error", 502: "provider_bad_gateway"}.get(status, super()._http_error_code(status))

    def _response_data(self, response, codes):
        if isinstance(response.get("error"), dict):
            detail = response["error"].get("code")
            diagnostics = {"http_status": response.get("_http_status")}
            if type(detail) is int and 400 <= detail <= 599:
                diagnostics["provider_error_code"] = detail
            raise ProviderError("provider_response_error", diagnostics=diagnostics)
        if response.get("model") not in {self.settings.model, self.settings.model.removesuffix(":free")}:
            raise ProviderError("unexpected_response_model")
        return super()._response_data(response, codes)


def create_provider(settings, **kwargs):
    """Select exactly one adapter from trusted configuration, never from message text."""
    return {"gemini": GeminiProvider, "groq": GroqProvider, "openrouter": OpenRouterProvider}[settings.provider](settings, **kwargs)
