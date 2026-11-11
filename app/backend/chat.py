"""Phase 5B adapter: bounded extraction, existing quality gate, fitted LR only."""
from __future__ import annotations

from collections import deque
from dataclasses import replace
import json
import os
from pathlib import Path
from threading import RLock
import time

from src.agent.conversation import ConversationEngine, InputGuard, Policy
from src.agent.provider import create_provider, ProviderError, ProviderSettings
from .prediction import PROJECT_ROOT
from .schemas import PredictResponse


def reported_usage(telemetry):
    """Provider-reported counters only; no invented billed cost or token estimate."""
    entries = [t.get("usage", {}) for t in telemetry if t.get("usage_kind") == "provider_reported"]
    fields = ("total_input_tokens", "total_output_tokens", "total_thought_tokens", "total_tokens")
    return {"kind": "provider_reported" if entries else "unknown", "requests": len(telemetry),
            "complete": bool(entries) and len(entries) == len(telemetry) and all(all(k in v for k in fields) for v in entries),
            **{k: sum(v[k] for v in entries) if entries and all(k in v for v in entries) else None for k in fields},
            "reported_cost": None}


class BoundedProvider:
    """Bound one explicitly selected adapter; no automatic routing or schema fallback.

    One generate call makes at most one HTTP request (max_retries=0). Byte-based
    admission is conservative, not a tokenizer or a billing claim. Unknown usage
    consumes its reservation; actual usage is reported separately.
    """
    def __init__(self, settings, *, max_requests=20, token_budget=100000, requests_per_minute=6,
                 max_request_bytes=64000, transport=None, clock=time.monotonic):
        if not (1 <= max_requests <= 100 and 10000 <= token_budget <= 1000000 and
                1 <= requests_per_minute <= 20 and 1000 <= max_request_bytes <= 128000):
            raise ValueError("invalid_local_provider_budget")
        self.settings = replace(settings, max_retries=0, max_output_tokens=min(settings.max_output_tokens, 2048))
        self.inner = create_provider(self.settings, transport=transport)
        self.max_requests, self.token_budget = max_requests, token_budget
        self.rpm, self.max_bytes = requests_per_minute, max_request_bytes
        self.clock, self.lock, self.times = clock, RLock(), deque()
        self.requests = self.charged = self.reserved = 0
        self.telemetry = []
        self.last_error = None

    def generate(self, **kwargs):
        if not self.settings.live_enabled:
            raise ProviderError("live_disabled")
        if not os.environ.get(self.settings.api_key_env, "").strip():
            raise ProviderError("missing_api_key")
        size = len(json.dumps(kwargs, ensure_ascii=False, allow_nan=False).encode("utf-8")) + 1024
        reservation = size + self.settings.max_output_tokens
        with self.lock:
            now = self.clock()
            while self.times and now - self.times[0] >= 60:
                self.times.popleft()
            if size > self.max_bytes:
                raise ProviderError("local_request_size_limit")
            if self.requests >= self.max_requests:
                raise ProviderError("local_request_budget")
            if len(self.times) >= self.rpm:
                raise ProviderError("local_rate_limit")
            if self.charged + self.reserved + reservation > self.token_budget:
                raise ProviderError("local_token_budget")
            self.requests += 1
            self.times.append(now)
            self.reserved += reservation
        stats = []
        try:
            reply = self.inner.generate(**kwargs)
            stats = reply.telemetry
            with self.lock:
                self.last_error = None
            return reply
        except ProviderError as exc:
            stats = exc.telemetry
            with self.lock:
                self.last_error = {"code": exc.code, **exc.diagnostics}
            raise
        finally:
            actual = []
            for item in stats:
                usage = item.get("usage", {})
                if "total_tokens" in usage:
                    actual.append(usage["total_tokens"])
                elif all(k in usage for k in ("total_input_tokens", "total_output_tokens", "total_thought_tokens")):
                    actual.append(sum(usage.get(k, 0) for k in ("total_input_tokens", "total_output_tokens", "total_thought_tokens")))
            with self.lock:
                self.reserved -= reservation
                self.charged += sum(actual) if actual else reservation
                self.telemetry.extend(stats)

    def status(self):
        with self.lock:
            last_error = dict(self.last_error) if self.last_error else None
        return {"provider": self.settings.provider, "model": self.settings.model, "live_enabled": self.settings.live_enabled,
                "key_configured": bool(os.environ.get(self.settings.api_key_env, "").strip()),
                "requests_used": self.requests, "request_limit": self.max_requests,
                "output_token_limit_per_request": self.settings.max_output_tokens,
                "token_budget": self.token_budget, "budget_units_used": self.charged,
                "usage": reported_usage(self.telemetry),
                "last_error": ({k: v for k, v in last_error.items()
                                if k in {"code", "http_status", "provider_status"}}
                               if last_error else None)}


# Preserve existing caller imports; this alias does not choose Gemini or route traffic.
BoundedGemini = BoundedProvider


def production_provider(project_root=PROJECT_ROOT):
    cfg = ProviderSettings.from_environment(Path(project_root) / "configs/phase5b.json")
    return BoundedProvider(cfg)


def unavailable_reply(message, policy):
    # Urgent guard remains useful even if a checkpoint cannot be loaded. No LLM needed.
    urgent = InputGuard(policy).check(message).intent == "urgent"
    return {"session_id": None, "turn_id": None, "subject_id": "self",
            "status": "urgent_redirect" if urgent else "model_not_ready",
            "reason": "severe_breathing_language" if urgent else "model_not_ready",
            "message": policy.urgent_message if urgent else "Mô hình gợi ý hiện chưa sẵn sàng. Chưa có Top3; hãy kiểm tra thiết lập máy chủ rồi thử lại.",
            "predictions": None, "symptom_states": {}, "usage": reported_usage([])}


class ChatRuntime:
    def __init__(self, service, provider, policy=None, *, offline_policy=None, presenter=None):
        self.service = service
        from src.agent.presentation import PredictionPresenter
        self.presenter = presenter or PredictionPresenter.load(PROJECT_ROOT, service.catalog)
        from src.agent.offline import OfflineExtractor, OfflineConversation
        engine_type = OfflineConversation if isinstance(provider, OfflineExtractor) else ConversationEngine
        self.engine = (engine_type(service.catalog, provider, policy or Policy(), offline_policy=offline_policy)
                       if engine_type is OfflineConversation else engine_type(service.catalog, provider, policy or Policy()))

    @classmethod
    def open(cls, service, *, presenter=None):
        # Preserve an explicitly selected legacy LLM; otherwise default to offline.
        mode = os.environ.get("DISEASE_CHAT_MODE", "llm" if os.environ.get("DISEASE_LLM_PROVIDER") else "offline")
        if mode == "offline":
            from src.agent.offline import OfflineExtractor, OfflinePolicy
            provider = OfflineExtractor(service.catalog, PROJECT_ROOT / "configs/synonyms.json")
            offline_policy = OfflinePolicy.from_file(PROJECT_ROOT / "configs/phase5b.json")
        elif mode == "llm":
            provider = production_provider()
            offline_policy = None
        else:
            raise ValueError("invalid_chat_mode")
        return cls(service, provider, Policy.from_file(PROJECT_ROOT / "configs/phase5b.json"), offline_policy=offline_policy, presenter=presenter)

    def status(self):
        provider = self.engine.provider
        return provider.status() if callable(getattr(provider, "status", None)) else {"model": "test-double", "live_enabled": False}

    def handle(self, message, *, session_id=None, subject_id=None, reset=False, batch_id=None, action='message'):
        # Hold the existing session lock through extraction AND forward_ready so a
        # concurrent edit/reset cannot associate old predictions with a newer turn.
        with self.engine.store.lock:
            if reset:
                if session_id:
                    self.engine.store.discard(session_id)
                key = self.engine.start(subject_id or "self")
                return {"session_id": key, "turn_id": None, "subject_id": subject_id or "self",
                        "status": "new_session", "reason": "user_reset", "message": "Đã bắt đầu cuộc trò chuyện mới. Bạn đang gặp triệu chứng gì?",
                        "predictions": None, "symptom_states": {}, "usage": reported_usage([])}
            from src.agent.offline import OfflineConversation
            if action!='message' and not isinstance(self.engine,OfflineConversation):
                return {'session_id':session_id,'turn_id':None,'subject_id':subject_id or 'self',
                    'status':'out_of_scope','reason':'offline_control_only','message':'Thao tác này dành cho hội thoại offline.',
                    'predictions':None,'symptom_states':{},'usage':reported_usage([])}
            result = (self.engine.handle(message, session_id=session_id, subject_id=subject_id, batch_id=batch_id,action=action)
                      if isinstance(self.engine, OfflineConversation) else
                      self.engine.handle(message, session_id=session_id, subject_id=subject_id))
            response = {"session_id": result.session_id, "turn_id": result.turn_id, "subject_id": result.subject_id,
                        "status": result.status, "reason": result.reason, "message": result.message,
                        "predictions": None, "symptom_states": (result.sidecar or {}).get("states", {}),
                        "usage": reported_usage(result.telemetry)}
            response['state_summary'] = {'matched_count': len(response['symptom_states']),
                                         'unmatched_count': len((result.sidecar or {}).get('unmapped', [])),
                                         'top3_display': []}
            if isinstance(self.engine, OfflineConversation) and self.engine.offline_policy.dialogue_version == 2 and result.session_id:
                session = self.engine.store.get(result.session_id)
                batch = self.engine.batch_state(session)
                response['pending_questions'] = batch['pending'] if result.status == 'clarification_required' else None
                response['dialogue'] = {'version':2,'asked_questions':session.questions,
                    'question_batches':batch['count'],'answered_questions':len(batch['answered']),
                    'present_count':sum(s=='present' for s in response['symptom_states'].values()),
                    'denied_count':sum(s=='denied' for s in response['symptom_states'].values()),
                    'uncertain_count':sum(s=='uncertain' for s in response['symptom_states'].values()),
                    'unmentioned_count':375-len(response['symptom_states']),
                    'pending_unanswered_count':sum(i['state'] is None for i in (batch['pending'] or {}).get('items',[])),
                    'question_round':batch['round'],'selector_reason':self.engine._state(session)['selector'],
                    'user_requested_preview':result.reason=='offline_requested_preview',
                    'policy_review_status':'provisional_pending_human_review'}
                if not session.stopped:
                    response['available_actions']=['more','add','preview']
            if hasattr(self.engine, 'health_detector'):
                response['state_summary']['health_intent'] = self.engine.health_detector.detect(message)
            def offline_confirmation():
                provider = self.engine.provider
                if not hasattr(provider, 'synonyms') or not response['symptom_states']:
                    return ''
                names = {'present': 'hiện diện', 'denied': 'phủ định', 'uncertain': 'chưa chắc'}
                items = list(response['symptom_states'].items())
                summary = ', '.join((provider.synonyms[f]['display_vi'] or f) + ' (' + names[s] + ')' for f, s in items[:12])
                return 'Đã ghi nhận: ' + summary + ('; còn các mục khác' if len(items) > 12 else '') + '. '
            response['message'] = offline_confirmation() + response['message']
            if result.status == "provider_error":
                response["message"] = {
                    "live_disabled": "Chức năng hiểu ngôn ngữ chưa được bật trên máy chủ; chưa có gợi ý.",
                    "missing_api_key": "Dịch vụ hiểu ngôn ngữ chưa được cấu hình trên máy chủ; chưa có gợi ý.",
                    "rate_limited": "Dịch vụ hiểu ngôn ngữ đang giới hạn lượt dùng. Hãy thử lại sau; chưa có gợi ý.",
                    "provider_unavailable": "Dịch vụ hiểu ngôn ngữ đang bận hoặc tạm thời chưa sẵn sàng. Hãy thử lại sau; chưa có gợi ý.",
                    "local_rate_limit": "Phiên máy chủ đã đạt giới hạn lượt gọi mỗi phút. Hãy thử lại sau.",
                    "local_request_budget": "Phiên máy chủ đã dùng hết ngân sách thử nghiệm; chưa có gợi ý mới.",
                    "local_token_budget": "Phiên máy chủ đã đạt giới hạn token thử nghiệm; chưa có gợi ý mới.",
                }.get(result.reason, result.message)
            if result.status != "extraction_ready":
                return response
            try:
                prediction = self.engine.forward_ready(result.session_id, result.turn_id, self.service)
                self.engine.store.get(result.session_id)  # Fail closed if inference outlives the session.
                from .models import render_prediction, HARD_ID
                response["predictions"] = render_prediction(prediction, self.presenter)
                hard = prediction.get('model_id') == HARD_ID
                response['state_summary']['top3_display'] = response['predictions']['presentation'].get('top3', [])
                response.update(status="prediction_ready", reason="validated_features_lr_tuned",
                                message="Dưới đây là 3 gợi ý từ mô hình dựa trên triệu chứng đã ghi nhận. Điểm tự tin dự đoán là score chưa calibration, không phải xác suất mắc bệnh hay độ tin cậy chẩn đoán. Đây là gợi ý từ mô hình học máy trên dữ liệu nghiên cứu, không thay thế chẩn đoán của bác sĩ.")
                response['message'] = offline_confirmation() + response['message']
                if hard:
                    response['message'] = offline_confirmation() + 'Kết quả hard voting từ ba model đã chọn. Phiếu bầu không phải xác suất mắc bệnh; không có Top3 probability. Không thay thế chẩn đoán của bác sĩ.'
                    response['reason'] = 'validated_features_hard_vote'
                elif prediction.get('model_id') == 'lr_baseline':
                    response['reason'] = 'validated_features_lr_baseline'
                if result.reason.startswith('offline_limited_'):
                    response['reason'] = result.reason
                    response['message'] = 'Thông tin còn hạn chế; đã hết câu hỏi phù hợp hoặc ngân sách hỏi. ' + response['message']
                if result.reason=='offline_requested_preview':
                    response['reason']=result.reason
                    response['message']='Kết quả tham khảo với thông tin còn hạn chế. '+response['message']
                if not hard and callable(getattr(self.engine, 'log_debug', None)):
                    entries = response['predictions']['presentation']['top3']
                    self.engine.log_debug(result, scores=[item['score_percent'] for item in response['predictions']['top3']],
                        translation_stats={s: sum(e['translation_status'] == s for e in entries) for s in ('missing','needs_review','draft')})
            except Exception:
                response.update(status="model_error", reason="prediction_unavailable", predictions=None,
                                message="Mô hình chưa trả được kết quả hợp lệ; không có Top3 cho lượt này.")
            return response
