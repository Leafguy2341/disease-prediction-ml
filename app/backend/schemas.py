"""Strict structured input; scores retain their original 587-class normalization."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

ModelId = Literal['lr_tuned_c2', 'lr_baseline', 'hard_tuned_lr_svc_knn']


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    model_id: ModelId = 'lr_tuned_c2'
    present_features: Annotated[list[Annotated[str, Field(min_length=1, max_length=256)]],
                                Field(min_length=1, max_length=375)]

    @field_validator("present_features")
    @classmethod
    def unique_features(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("Feature không được lặp.")
        return value


class TopResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    rank: Annotated[int, Field(ge=1, le=3)]
    class_id: Annotated[int, Field(ge=0, le=586)]
    label: str
    score_percent: Annotated[FiniteFloat, Field(ge=0, le=100)]


class PredictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    model_id: Literal["lr_tuned_c2", "lr_baseline"]
    tuning_experiment_id: str | None
    selected_checkpoint_id: str
    checkpoint_sha256: str
    schema_sha256: str
    features: Literal[375]
    classes: Literal[587]
    input_present_count: Annotated[int, Field(ge=1, le=375)]
    score_label: Literal["Điểm mô hình (%)"]
    calibrated: Literal[False]
    note: str
    top3: Annotated[list[TopResult], Field(min_length=3, max_length=3)]
    presentation: dict | None = None


class HardVoteResult(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    class_id: Annotated[int, Field(ge=0, le=586)]
    label: str
    votes: Annotated[int, Field(ge=1, le=3)]
    total_members: Literal[3]
    tie: bool
    members: list[dict]


class HardVoteResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    model_id: Literal['hard_tuned_lr_svc_knn']
    result_kind: Literal['hard_vote_result']
    ensemble_run_id: str
    ensemble_manifest_sha256: str
    member_checkpoint_sha256: dict[str, str]
    schema_sha256: str
    features: Literal[375]
    classes: Literal[587]
    input_present_count: int
    hard_vote_result: HardVoteResult
    note: str
    presentation: dict | None = None


class ValidationIssue(BaseModel):
    field: str
    type: str
    message: str


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: list[ValidationIssue] | None = None


class ErrorResponse(BaseModel):
    error: ErrorInfo


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message: Annotated[str, Field(max_length=4000)] = ""
    session_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")] | None = None
    subject_id: Literal["self", "mother", "father", "child"] | None = None
    reset: bool = False
    model_id: ModelId = 'lr_tuned_c2'
    mode: Literal['offline', 'llm'] | None = None
    batch_id: Annotated[str, Field(pattern=r'^[0-9a-f]{32}$')] | None = None
    action: Literal['message','more','preview'] = 'message'

    @field_validator("message")
    @classmethod
    def valid_characters(cls, value):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("Ký tự không hợp lệ.")
        return value


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    session_id: str | None
    turn_id: str | None
    subject_id: str
    status: str
    reason: str
    message: str
    predictions: PredictResponse | HardVoteResponse | None
    symptom_states: dict[str, Literal["present", "denied", "uncertain"]]
    usage: dict
    state_summary: dict | None = None
    pending_questions: dict | None = None
    dialogue: dict | None = None
    available_actions: list[str] | None = None
    requested_model_id: ModelId | None = None
    processed_model_id: ModelId | None = None
