"""Contract v2, pinned Phase 2 metadata, evidence/context checks and ordered mapping."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
from jsonschema import Draft202012Validator

from src.data.integrity import read_baseline
from src.data.loader import sha256_file

STATES = ("present", "denied", "uncertain")
SUBJECTS = {"self", "mother", "father", "child"}
ANCHOR = re.compile(r"\bmẹ(?:\s+tôi)?\b|\bmá(?:\s+tôi)?\b|\bbố(?:\s+tôi)?\b|\bba\s+tôi\b|\bcha\s+tôi\b|\bcon\s+tôi\b|"
                    r"\b(?:anh|chị|em|bạn|ông|bà|vợ|chồng)\s+(?:tôi|mình)\b|\b(?:tôi|mình|tớ|em|cháu|con)\b", re.I)
NEGATIVE = re.compile(r"\b(?:không|ko|chẳng|chưa bị|không còn|hết|đã khỏi)\b", re.I)
UNCERTAIN = re.compile(r"\b(?:hình như|có lẽ|chưa rõ|chưa chắc|không rõ|không chắc|chưa biết|có thể)\b", re.I)
UPDATE = re.compile(r"\b(?:nói nhầm|dùng nhầm|sửa lại|đính chính|hiện tại|bây giờ|giờ tôi|đã hết|không còn|xác nhận)\b", re.I)
PAST = re.compile(r"\b(?:trước đây|trước đó|hôm qua|đã từng|từng bị|câu trước|ban đầu|trong quá khứ|hồi nhỏ|ngày trước)\b", re.I)
CURRENT = re.compile(r"\b(?:hiện tại|bây giờ|ngay lúc này|giờ tôi|đang)\b", re.I)
NONPATIENT = re.compile(r"\b(?:nếu|giả sử|ví dụ|theo sách|người ta|triệu chứng của)\b", re.I)
SEPARATOR = re.compile(r"[.,;!?\n]|\b(?:và|nhưng|còn|mà)\b", re.I)
PATIENT_ASSERTION = re.compile(r"\b(?:tôi|mình|tớ|em|cháu|con|mẹ(?:\s+tôi)?|bố(?:\s+tôi)?)\s+"
                               r"(?:(?:đang|vẫn|chỉ|có|bị|không|chưa|thấy|đã|hết|từng|mới|lại|rất|hay|còn)\s+){0,4}"
                               r"(?:ho+|sốt|đau|buồn nôn|nôn|nghẹt mũi|dị cảm|hồi hộp|choáng|chóng mặt|khó thở|thở không nổi|ngạt thở|không (?:thể )?nói (?:thành|trọn) câu)\b", re.I)


# Accent-insensitive cue alternatives preserve original spans and all context checks.
# Exact phrase matching only; no fuzzy feature mapping.
import unicodedata as _unicode

def _cue_fold(value):
    return ''.join(c for c in _unicode.normalize('NFD', value.replace('đ', 'd'))
                   if not _unicode.combining(c))

for _name in ('ANCHOR', 'NEGATIVE', 'UNCERTAIN', 'UPDATE', 'PAST', 'CURRENT',
              'NONPATIENT', 'SEPARATOR', 'PATIENT_ASSERTION'):
    _pattern = globals()[_name]
    globals()[_name] = re.compile('(?:' + _pattern.pattern + ')|(?:' + _cue_fold(_pattern.pattern) + ')', _pattern.flags)
NEGATIVE = re.compile(NEGATIVE.pattern + r'|\b(?:chưa|chua)\b', re.I)
UNCERTAIN = re.compile(UNCERTAIN.pattern + r'|\b(?:không phải không|khong phai khong)\b', re.I)
UPDATE = re.compile(UPDATE.pattern + r'|\b(?:hết|het|đã khỏi|da khoi)\b', re.I)


class ExtractionError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)  # No untrusted text/feature/provider body in diagnostics.


@dataclass(frozen=True)
class Turn:
    turn_id: str
    role: str
    text: str
    subject_id: str


@dataclass(frozen=True)
class Catalog:
    features: tuple[str, ...]
    classes: tuple[str, ...]
    schema_id: str

    @classmethod
    def load(cls, project_root: Path, storage_root: Path | None = None):
        project_root = Path(project_root)
        storage_root = Path(storage_root) if storage_root is not None else project_root
        baseline = read_baseline(project_root / "configs/phase2_integrity.json")
        values = []
        for name in ("feature_schema.json", "label_mapping.json"):
            relative = "artifacts/metadata/phase2/" + name
            path = storage_root / relative
            if sha256_file(path) != baseline["files"][relative]["sha256"]:
                raise ExtractionError("metadata_checksum_mismatch")
            values.append(json.loads(path.read_text(encoding="utf-8")))
        schema, labels = values
        features, classes = schema["features"], labels["classes"]
        if (len(features) != 375 or len(set(features)) != 375 or len(classes) != 587
                or schema["schema_sha256"] != baseline["processed"]["schema_sha256"]
                or labels["id_to_class"] != classes
                or labels["class_to_id"] != {n: i for i, n in enumerate(classes)}
                or set(features) & {"regurgitation", "regurgitation.1"}):
            raise ExtractionError("metadata_schema_mismatch")
        return cls(tuple(features), tuple(classes), schema["schema_sha256"])


def extraction_schema(catalog: Catalog) -> dict:
    def obj(properties):
        return {"type": "object", "additionalProperties": False,
                "required": list(properties), "properties": properties}
    def array(item):
        return {"type": "array", "items": item}
    ref = lambda name: {"$ref": "#/$defs/" + name}
    span = obj({"turn_id": {"type": "string", "minLength": 1},
                "start": {"type": "integer", "minimum": 0}, "end": {"type": "integer", "minimum": 1},
                "text": {"type": "string", "minLength": 1}})
    evidence = {**array(ref("span")), "minItems": 1}
    mention = obj({"feature": ref("feature"), "evidence": ref("evidence")})
    unknown = obj({"phrase": {"type": "string", "minLength": 1}, "state": {"enum": list(STATES)},
                   "reason": {"enum": ["ambiguous_mapping", "outside_schema", "excluded_feature", "unclear_context"]},
                   "evidence": ref("evidence")})
    clarification = obj({"needed": {"type": "boolean"},
                         "reasons": {**array({"enum": ["ambiguous", "uncertain", "unmapped", "insufficient", "conflict"]}), "uniqueItems": True},
                         "target_features": {**array(ref("feature")), "uniqueItems": True}})
    schema = obj({"contract_version": {"const": 2}, "schema_sha256": {"const": catalog.schema_id},
                  **{name: array(ref("mention")) for name in STATES},
                  "unmapped": array(ref("unmapped")), "clarification": clarification})
    schema["$defs"] = {"feature": {"type": "string", "enum": list(catalog.features)},
                       "span": span, "evidence": evidence, "mention": mention, "unmapped": unknown}
    return schema


def anchor_subject(word: str) -> str:
    # Keep accented kinship distinctions before folding (bà != ba).
    if re.match(r"(?:anh|chị|em|bạn|ông|bà|vợ|chồng)\s+(?:tôi|mình)\b", word.casefold()):
        return "other"
    word = _cue_fold(word.casefold())
    if word.startswith(("me", "ma")): return "mother"
    if word.startswith(("bo", "ba ", "cha ")): return "father"
    if word.startswith("con toi"): return "child"
    if re.match(r"(?:anh|chi|em|ban|ong|ba|vo|chong)\s+(?:toi|minh)\b", word): return "other"
    return "self"


def evidence_context(turn: Turn, span: dict, intended_subject: str, state: str | None, *, conflicted=False):
    start, end = span["start"], span["end"]
    if turn.role != "user" or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(turn.text):
        raise ExtractionError("invalid_evidence_reference")
    if turn.text[start:end] != span["text"]:
        raise ExtractionError("evidence_slice_mismatch")
    for quote in re.finditer(r'''"[^"\n]*"|“[^”\n]*”|'[^'\n]*'|‘[^’\n]*’|`[^`\n]*`''', turn.text):
        if quote.start() <= start and end <= quote.end():
            raise ExtractionError("quoted_or_json_evidence")
    anchors = [m for m in ANCHOR.finditer(_unicode.normalize('NFC', turn.text[:end]))]
    subject = anchor_subject(anchors[-1].group()) if anchors else turn.subject_id
    if subject != intended_subject:
        raise ExtractionError("wrong_subject_evidence")
    separators = list(SEPARATOR.finditer(turn.text[:start]))
    left = separators[-1].end() if separators else 0
    context = _unicode.normalize('NFC', turn.text[left:end])
    # Meta/temporal cues can govern a comma-separated symptom list. A question
    # in a DIFFERENT sentence must not mask a later actual distress report.
    boundaries = list(re.finditer(r"[.!?;\n]", turn.text[:start]))
    sentence_start = boundaries[-1].end() if boundaries else 0
    boundary = re.search(r"[.!?;\n]", turn.text[end:])
    sentence_end = end + boundary.end() if boundary else len(turn.text)
    sentence = _unicode.normalize('NFC', turn.text[sentence_start:sentence_end])
    patient_assertion = bool(PATIENT_ASSERTION.search(sentence))
    if NONPATIENT.search(context):
        raise ExtractionError("hypothetical_or_general_evidence")
    if (NONPATIENT.search(sentence) or re.search(r"nguyên nhân|định nghĩa|trích dẫn|trích câu|giải thích|tìm hiểu|tôi hỏi", sentence, re.I)) and not patient_assertion:
        raise ExtractionError("hypothetical_or_general_evidence")
    if re.search(r"\?|là gì|nghĩa là|như thế nào", sentence, re.I) and not patient_assertion:
        raise ExtractionError("question_without_patient_assertion")
    if (re.search(r"\b(?:bạn|một người)\b", context)
            or re.search(r"\b(?:viết sách|tìm hiểu|giải thích|tôi hỏi)\b", context) and not PATIENT_ASSERTION.search(context)):
        raise ExtractionError("nonpatient_context")
    if PAST.search(context) and not CURRENT.search(context):
        raise ExtractionError("past_evidence")
    if PAST.search(sentence) and not CURRENT.search(sentence):
        raise ExtractionError("past_evidence")
    # These respiratory inability phrases are positive warning signs, not denials.
    assertion_context = re.sub(r"thở không nổi|không (?:thể )?nói (?:thành|trọn) câu", "", context, flags=re.I)
    assertion_context = re.sub(r"\bkhông\s+(?:chỉ|những)\b", "", assertion_context, flags=re.I)
    if state == "present" and (NEGATIVE.search(assertion_context) or UNCERTAIN.search(context)):
        raise ExtractionError("assertion_context_mismatch")
    if state == "denied" and (not NEGATIVE.search(assertion_context) or UNCERTAIN.search(context)):
        raise ExtractionError("assertion_context_mismatch")
    if state == "uncertain" and not conflicted and not UNCERTAIN.search(_unicode.normalize('NFC', turn.text)):
        raise ExtractionError("uncertainty_without_evidence")


@dataclass
class ValidatedExtraction:
    data: dict
    states: dict[str, str]
    subject_id: str
    turn_id: str
    schema_id: str

    def sidecar(self, catalog):
        return {"states": dict(self.states), "unmentioned": [f for f in catalog.features if f not in self.states],
                "unmapped": deepcopy(self.data["unmapped"]), "evidence": {
                    m["feature"]: deepcopy(m["evidence"]) for state in STATES for m in self.data[state]},
                "clarification": deepcopy(self.data["clarification"]), "subject_id": self.subject_id,
                "source_user_turn": self.turn_id, "schema_sha256": self.schema_id,
                "binary_zero": "not recorded as present; not confirmed clinically absent"}


class ExtractionValidator:
    def __init__(self, catalog: Catalog):
        self.catalog, self.schema = catalog, extraction_schema(catalog)
        self._validator = Draft202012Validator(self.schema)

    def validate(self, data: dict, turns: list[Turn], subject_id: str,
                 *, previous: ValidatedExtraction | None = None, clarified_feature: str | None = None,
                 answer_bindings: dict | None = None):
        if subject_id not in SUBJECTS or not turns or turns[-1].role != "user":
            raise ExtractionError("invalid_context")
        if next(self._validator.iter_errors(data), None) is not None:
            raise ExtractionError("invalid_extraction_contract")
        by_id = {t.turn_id: t for t in turns}
        if len(by_id) != len(turns):
            raise ExtractionError("duplicate_turn_id")
        latest = turns[-1]
        short_answer = latest.text.strip(" \t\n.!?").casefold() in {"có", "vâng", "đúng", "không", "chưa rõ", "chưa chắc", "co", "dung", "vang", "khong", "ko", "chưa", "chua", "chua ro", "chua chac"}
        info = data["clarification"]
        if (info["needed"] != bool(info["reasons"]) or not info["needed"] and info["target_features"]
                or len(info["target_features"]) > 2):
            raise ExtractionError("invalid_clarification")
        states, ranges = {}, []
        changed_context = bool(UPDATE.search(latest.text))
        for state in STATES:
            if len(data[state]) > 375:
                raise ExtractionError("too_many_mentions")
            for mention in data[state]:
                feature = mention["feature"]
                if feature in states:
                    raise ExtractionError("duplicate_or_conflicting_states")
                states[feature] = state
                if not 1 <= len(mention["evidence"]) <= 8:
                    raise ExtractionError("invalid_evidence_count")
                fresh = False
                for span in mention["evidence"]:
                    turn = by_id.get(span["turn_id"])
                    if turn is None:
                        raise ExtractionError("unknown_evidence_turn")
                    # Bindings come only from the server's pending-question parser,
                    # never from extraction JSON or client-supplied feature names.
                    binding = (answer_bindings or {}).get(turn.turn_id, {}).get(feature)
                    scoped = bool(binding and binding['state'] == state and binding['evidence'] == span
                                  and binding['subject_id'] == subject_id)
                    if span['turn_id'] in (answer_bindings or {}) and not scoped:
                        raise ExtractionError('unscoped_batch_answer')
                    evidence_context(turn, span, subject_id, None if scoped else state,
                                     conflicted="conflict" in info["reasons"])
                    fresh |= turn.turn_id == latest.turn_id
                    if turn.turn_id == latest.turn_id and short_answer and feature != clarified_feature and not scoped:
                        raise ExtractionError("unscoped_clarification_answer")
                    for other_feature, tid, start, end in ranges:
                        if other_feature != feature and tid == span["turn_id"] and max(start, span["start"]) < min(end, span["end"]):
                            other_binding = (answer_bindings or {}).get(tid, {}).get(other_feature)
                            if not (scoped and other_binding and other_binding['state'] == state
                                    and other_binding['subject_id'] == subject_id
                                    and other_binding['evidence'] == span):
                                raise ExtractionError("overlapping_feature_evidence")
                    ranges.append((feature, span["turn_id"], span["start"], span["end"]))
                if changed_context and not fresh:
                    raise ExtractionError("stale_evidence_after_update")
                if previous and previous.subject_id == subject_id and feature in previous.states and previous.states[feature] != state:
                    resolved_answer = feature == clarified_feature and previous.states[feature] == "uncertain" and fresh and state != "uncertain"
                    current_binding = (answer_bindings or {}).get(latest.turn_id, {}).get(feature)
                    resolved_answer |= bool(previous.states[feature]=='uncertain' and fresh and state!='uncertain'
                        and current_binding and current_binding['state']==state
                        and current_binding['subject_id']==subject_id)
                    if not changed_context and not resolved_answer and "conflict" not in info["reasons"]:
                        raise ExtractionError("unresolved_history_conflict")
        if previous and previous.subject_id == subject_id and not changed_context and set(previous.states) - set(states):
            raise ExtractionError("omitted_active_state")
        if not set(info["target_features"]) <= set(states):
            raise ExtractionError("unrelated_clarification_target")
        for item in data["unmapped"]:
            if not 1 <= len(item["evidence"]) <= 8:
                raise ExtractionError("invalid_evidence_count")
            for span in item["evidence"]:
                turn = by_id.get(span["turn_id"])
                if turn is None or item["phrase"] not in span["text"]:
                    raise ExtractionError("unmapped_evidence_mismatch")
                evidence_context(turn, span, subject_id, item["state"], conflicted="conflict" in info["reasons"])
        return ValidatedExtraction(deepcopy(data), states, subject_id, latest.turn_id, self.catalog.schema_id)

    def gate(self, value: ValidatedExtraction, *, min_present_features: int = 2):
        if value.schema_id != self.catalog.schema_id:
            return "schema_mismatch"
        if value.data["clarification"]["needed"]:
            return value.data["clarification"]["reasons"][0]
        if value.data["unmapped"]:
            return "unmapped"
        if "uncertain" in value.states.values():
            return "uncertain"
        if sum(s == "present" for s in value.states.values()) < min_present_features:
            return "insufficient"
        return None

    def frame(self, value: ValidatedExtraction, *, min_present_features: int = 2):
        if self.gate(value, min_present_features=min_present_features) is not None:
            raise ExtractionError("quality_gate_blocked")
        array = np.array([[int(value.states.get(f) == "present") for f in self.catalog.features]], dtype=np.uint8)
        return pd.DataFrame(array, columns=self.catalog.features)
