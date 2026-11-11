"""Run locally: python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --workers 1."""
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from .prediction import LRPredictionService, MODEL_ID, ModelLoadError, PredictionError, PROJECT_ROOT
from .schemas import ChatRequest, ChatResponse, ErrorResponse, PredictRequest, PredictResponse, HardVoteResponse
from .models import MODEL_NAMES, load_optional, registry, render_prediction
from .chat import ChatRuntime, unavailable_reply
from src.agent.conversation import Policy
from src.agent.presentation import PredictionPresenter


def _error(status, code, message, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = ([dict(field='model_id',type=details.get('code','not_ready'),message=details.get('message','Model not ready'))]
                            if isinstance(details,dict) else details)
    return JSONResponse(status_code=status, content={"error": error})


def _load_from_environment():
    root = os.environ.get("DISEASE_API_STORAGE_ROOT")
    if not root:
        raise ModelLoadError("storage_not_configured", "Đặt DISEASE_API_STORAGE_ROOT tới thư mục artifact local.")
    return LRPredictionService.load(root)


def create_app(*, service_loader=None, chat_factory=None, optional_loader=None):
    loader = service_loader or _load_from_environment

    @asynccontextmanager
    async def lifespan(application):
        application.state.predictor = None
        application.state.load_error = None
        application.state.chat = None
        application.state.presenter = None
        try:
            application.state.predictor = loader()  # Once per process, never per request.
        except ModelLoadError as exc:
            application.state.load_error = {"code": exc.code, "message": exc.message}
        except Exception:
            application.state.load_error = {"code": "checkpoint_load_failed",
                                            "message": "Không load được approved LR tuned; kiểm artifact và môi trường."}
        application.state.chat_error = None
        if application.state.predictor is not None:
            try:
                application.state.presenter = PredictionPresenter.load(PROJECT_ROOT, application.state.predictor.catalog)
                application.state.chat = (chat_factory(application.state.predictor) if chat_factory else
                    ChatRuntime.open(application.state.predictor, presenter=application.state.presenter))
            except Exception:
                application.state.chat_error = "chat_configuration_invalid"
        application.state.model_services = ({MODEL_ID:application.state.predictor} if application.state.predictor else {})
        application.state.model_errors = {MODEL_ID:application.state.load_error} if application.state.load_error else {}
        application.state.model_chats = {MODEL_ID:application.state.chat} if application.state.chat else {}
        if optional_loader is not None or service_loader is None:
            if optional_loader is not None:
                extras, errors = optional_loader(application.state.predictor)
            elif os.environ.get('DISEASE_API_STORAGE_ROOT'):
                extras, errors = load_optional(os.environ['DISEASE_API_STORAGE_ROOT'], application.state.predictor)
            else:
                extras, errors = {}, {}
            application.state.model_services.update(extras)
            application.state.model_errors.update(errors)
            for key, service in extras.items():
                try:
                    application.state.model_chats[key] = (chat_factory(service) if chat_factory else ChatRuntime.open(service))
                except Exception:
                    application.state.model_errors[key] = dict(code='chat_configuration_invalid',message='Model loaded; chat configuration failed.')
        yield
        application.state.predictor = None
        application.state.chat = None
        application.state.model_services.clear()
        application.state.model_chats.clear()

    api = FastAPI(title="Disease Prediction — Local Research Chat", version="0.2.0", lifespan=lifespan,
                  description="Offline rules hoặc LLM tùy chọn → validated features → approved LR tuned. Điểm mô hình chưa calibration; không phải chẩn đoán.")

    @api.middleware("http")
    async def local_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @api.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        details = [{"field": ".".join(map(str, e["loc"])), "type": e["type"], "message": e["msg"]}
                   for e in exc.errors()]
        return _error(422, "input_validation_error", "JSON input không đúng contract.", details)

    @api.exception_handler(HTTPException)
    async def http_error(request, exc):
        return _error(exc.status_code, "http_error", str(exc.detail))

    @api.get("/health")
    def health(request: Request):
        service = request.app.state.predictor
        chat = request.app.state.chat
        chat_info = chat.status() if chat is not None else {"status": "not_ready", "reason": request.app.state.chat_error}
        if service is None:
            return JSONResponse(status_code=503, content={"status": "not_ready", "model_id": MODEL_ID,
                "checkpoint_status": "NOT VERIFIED", "error": request.app.state.load_error, "chat": chat_info})
        return {"status": "ok", "checkpoint_status": service.verification, **service.identity(), "chat": chat_info}

    @api.get('/api/v1/models')
    def models(request: Request):
        return registry(request.app.state.model_services, request.app.state.model_errors)

    @api.post("/api/v1/predict", response_model=PredictResponse | HardVoteResponse,
              responses={422: {"model": ErrorResponse, "description": "Invalid structured input"},
                         503: {"model": ErrorResponse, "description": "Approved checkpoint not ready"},
                         500: {"model": ErrorResponse, "description": "Invalid model output or prediction failure"}})
    def predict(payload: PredictRequest, request: Request):
        service = request.app.state.model_services.get(payload.model_id)
        if service is None:
            return _error(503, "model_not_ready", "Model được chọn chưa sẵn sàng; không fallback.",
                          request.app.state.model_errors.get(payload.model_id))
        try:
            frame = service.frame_from_features(payload.present_features)
            result = service.predict(frame, schema_sha256=service.catalog.schema_id)
            presenter = request.app.state.presenter or PredictionPresenter.load(PROJECT_ROOT,service.catalog)
            return render_prediction(result, presenter)
        except PredictionError as exc:
            return _error(422, exc.code, exc.message)
        except Exception:
            return _error(500, "prediction_failed", "Không tạo được Top3 hợp lệ; chưa có kết quả dự đoán.")

    @api.post("/api/v1/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest, request: Request):
        if not payload.reset and payload.action=='message' and not payload.message.strip():
            return _error(422, "empty_message", "Hãy nhập mô tả trước khi gửi.")
        if payload.action!='message' and (payload.message.strip() or payload.reset):
            return _error(422,'control_with_message','Chọn thao tác và gửi triệu chứng là hai lượt riêng.')
        if payload.reset and payload.message.strip():
            return _error(422, "reset_with_message", "Reset phiên và gửi mô tả là hai thao tác riêng.")
        runtime = request.app.state.model_chats.get(payload.model_id)
        if payload.mode == 'llm':
            return _error(409, 'online_ui_not_supported', 'Online chưa được kết nối qua giao diện này; không có yêu cầu gửi provider.')
        if payload.mode == 'offline' and runtime is not None and runtime.status().get('mode') != 'offline':
            return _error(409, 'offline_server_required', 'Máy chủ đang ở chế độ khác; khởi động với DISEASE_CHAT_MODE=offline.')
        if runtime is None:
            if payload.model_id != MODEL_ID:
                return _error(503,'model_not_ready','Model được chọn chưa được qualify hoặc thiếu artifact; không fallback.',
                              request.app.state.model_errors.get(payload.model_id))
            try:
                reply = unavailable_reply(payload.message, Policy.from_file(PROJECT_ROOT / "configs/phase5b.json"))
            except Exception:
                return _error(503, "chat_configuration_invalid", "Thiết lập trò chuyện chưa hợp lệ; chưa có dự đoán.")
            if reply["status"] != "urgent_redirect" and request.app.state.predictor is not None:
                reply.update(status="provider_error", reason="chat_configuration_invalid",
                             message="Dịch vụ hiểu ngôn ngữ chưa khởi tạo được; chưa có gợi ý cho lượt này.")
            return JSONResponse(status_code=200 if reply["status"] == "urgent_redirect" else 503, content=reply)
        try:
            # A model switch starts fresh state; a stale session cannot be reused across models.
            for key, other in request.app.state.model_chats.items():
                if key == payload.model_id or not payload.session_id:
                    continue
                try:
                    other.engine.store.get(payload.session_id)
                except ValueError:
                    continue
                if not payload.reset:
                    return _error(409,'model_session_mismatch','Đổi model cần bắt đầu cuộc trò chuyện mới.')
                other.engine.store.discard(payload.session_id)
            reply = runtime.handle(payload.message, session_id=payload.session_id, subject_id=payload.subject_id,
                                   reset=payload.reset, batch_id=payload.batch_id, action=payload.action)
            reply['requested_model_id'] = payload.model_id
            reply['processed_model_id'] = (reply.get('predictions') or {}).get('model_id')
            ChatResponse.model_validate(reply)
        except Exception:
            return _error(500, "chat_failed", "Lượt trò chuyện chưa xử lý được; chưa có dự đoán.")
        status = 200
        if reply["status"] == "provider_error":
            status = 429 if reply["reason"] in {"rate_limited", "local_rate_limit", "local_request_budget", "local_token_budget"} else 503
        elif reply["status"] == "model_error":
            status = 503
        return JSONResponse(status_code=status, content=reply)

    frontend = PROJECT_ROOT / "app/frontend"
    api.mount("/static", StaticFiles(directory=frontend), name="static")

    @api.get("/", include_in_schema=False)
    def home():
        return FileResponse(frontend / "index.html")

    return api


app = create_app()  # No weights or filesystem access until lifespan starts.
