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
from .schemas import ChatRequest, ChatResponse, ErrorResponse, PredictRequest, PredictResponse
from .chat import ChatRuntime, unavailable_reply
from src.agent.conversation import Policy
from src.agent.presentation import PredictionPresenter


def _error(status, code, message, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(status_code=status, content={"error": error})


def _load_from_environment():
    root = os.environ.get("DISEASE_API_STORAGE_ROOT")
    if not root:
        raise ModelLoadError("storage_not_configured", "Đặt DISEASE_API_STORAGE_ROOT tới thư mục artifact local.")
    return LRPredictionService.load(root)


def create_app(*, service_loader=None, chat_factory=None):
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
        yield
        application.state.predictor = None
        application.state.chat = None

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
        service = request.app.state.predictor
        from src.models.final_evaluation import protocol
        frozen = protocol()
        cp = frozen['checkpoints']['lr_tuned_c2']
        return {'default_model_id':MODEL_ID, 'models':[{
            'model_id':MODEL_ID, 'display_name':'LR tuned C=2 — Mặc định',
            'checkpoint_sha256':cp['files']['pipeline.joblib']['sha256'],
            'artifact_path':cp['folder'], 'schema_sha256':frozen['processed']['schema_sha256'],
            'features':375, 'classes':587, 'label_mapping':'Phase 2 fixed class order',
            'label_mapping_sha256':frozen['phase2_files']['artifacts/metadata/phase2/label_mapping.json']['sha256'],
            'checkpoint_identity':cp['identity']['experiment_id'],
            'trained_versions':cp['identity']['versions'],
            'deployment_approval':'approved_before_final_test',
            'evaluation_provenance':'tuning-v1-9c4dd013abbba14a; frozen final evaluation',
            'runtime_compatibility':'PASS' if service else 'NOT VERIFIED',
            'available':service is not None}],
            'other_candidates':'Baseline/tuned khác và ensembles chưa được duyệt/tương thích Windows để phục vụ web; không thể chọn.',
            'online_settings_supported':False}

    @api.post("/api/v1/predict", response_model=PredictResponse,
              responses={422: {"model": ErrorResponse, "description": "Invalid structured input"},
                         503: {"model": ErrorResponse, "description": "Approved checkpoint not ready"},
                         500: {"model": ErrorResponse, "description": "Invalid model output or prediction failure"}})
    def predict(payload: PredictRequest, request: Request):
        service = request.app.state.predictor
        if service is None:
            return _error(503, "model_not_ready", "Approved LR tuned chưa sẵn sàng; không có model fallback.")
        try:
            frame = service.frame_from_features(payload.present_features)
            result = service.predict(frame, schema_sha256=service.catalog.schema_id)
            return PredictResponse.model_validate(request.app.state.presenter.render(result))
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
        runtime = request.app.state.chat
        if payload.mode == 'llm':
            return _error(409, 'online_ui_not_supported', 'Online chưa được kết nối qua giao diện này; không có yêu cầu gửi provider.')
        if payload.mode == 'offline' and runtime is not None and runtime.status().get('mode') != 'offline':
            return _error(409, 'offline_server_required', 'Máy chủ đang ở chế độ khác; khởi động với DISEASE_CHAT_MODE=offline.')
        if runtime is None:
            try:
                reply = unavailable_reply(payload.message, Policy.from_file(PROJECT_ROOT / "configs/phase5b.json"))
            except Exception:
                return _error(503, "chat_configuration_invalid", "Thiết lập trò chuyện chưa hợp lệ; chưa có dự đoán.")
            if reply["status"] != "urgent_redirect" and request.app.state.predictor is not None:
                reply.update(status="provider_error", reason="chat_configuration_invalid",
                             message="Dịch vụ hiểu ngôn ngữ chưa khởi tạo được; chưa có gợi ý cho lượt này.")
            return JSONResponse(status_code=200 if reply["status"] == "urgent_redirect" else 503, content=reply)
        try:
            reply = runtime.handle(payload.message, session_id=payload.session_id, subject_id=payload.subject_id,
                                   reset=payload.reset, batch_id=payload.batch_id, action=payload.action)
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
