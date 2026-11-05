"""Presentation only: canonical IDs and numeric scores remain untouched."""
from copy import deepcopy
import json
import math
import hashlib
from pathlib import Path


class PredictionPresenter:
    def __init__(self, classes, translations=None, *, score_decimals=4, allow_draft_translations=False,
                 evaluation_reference=None):
        if type(score_decimals) is not int or not 0 <= score_decimals <= 8:
            raise ValueError('invalid_score_decimals')
        self.classes = tuple(classes)
        self.translations = translations or {}
        self.score_decimals = score_decimals
        if type(allow_draft_translations) is not bool:
            raise ValueError('invalid_draft_translation_policy')
        self.allow_draft_translations = allow_draft_translations
        self.evaluation_reference = evaluation_reference

    @staticmethod
    def evaluation(root):
        """Read frozen closeout evidence, never test payload or new metrics."""
        path=Path(root)/'artifacts/metadata/final_evaluation_audit/colab_evidence.json'
        expected='102845056236bfe3855962cd1717ece4402a958cc6ce593540ab1ccab4f34131'
        try:
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=expected: return None
            packet=json.loads(raw)
            if packet['status']!='PASS' or packet['manifest_sha256']!='f1ad195e1e46154d7a29a421e80387bfa76e494f4df771cede240f882d0b754a': return None
            return {'model_id':'lr_tuned_c2', 'split':'test', 'metric':'Accuracy',
                'accuracy':packet['recalculated']['lr_tuned_c2']['accuracy'],
                'records':packet['manifest']['records'],
                'checkpoint_sha256':packet['checkpoints']['lr_tuned_c2']['pipeline.joblib']['sha256'],
                'evidence_packet_sha256':expected,
                'scope':'Toàn tập test đã đánh giá; không phải độ chính xác của từng gợi ý hoặc hiệu năng lâm sàng.'}
        except (OSError,ValueError,KeyError,TypeError):
            return None

    @classmethod
    def load(cls, root, catalog):
        root = Path(root)
        config = json.loads((root/'configs/phase5b.json').read_text(encoding='utf-8'))
        path = root/'configs/disease_names_vi.json'
        try:
            names = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(names, dict):
                names = {}
        except (OSError, ValueError):
            names = {}  # Missing/unreadable translation is never a model fallback.
        return cls(catalog.classes, names, score_decimals=config['presentation']['SCORE_DECIMALS'],
                   allow_draft_translations=config['presentation'].get('ALLOW_DRAFT_TRANSLATIONS', False),
                   evaluation_reference=cls.evaluation(root))

    def label(self, canonical):
        entry = self.translations.get(canonical)
        if not isinstance(entry, dict) or not isinstance(entry.get('display_vi'), str) or not entry['display_vi'].strip():
            return canonical, 'missing'
        if entry.get('needs_review') is False:
            return entry['display_vi'].strip(), 'reviewed'
        if self.allow_draft_translations and entry['display_vi'].strip() != canonical:
            return entry['display_vi'].strip(), 'draft'
        return canonical, 'needs_review'

    def render(self, prediction):
        result = deepcopy(prediction)
        rows = []
        for item in result['top3']:
            label, index, score = item['label'], item['class_id'], item['score_percent']
            if (type(index) is not int or not 0 <= index < len(self.classes) or self.classes[index] != label
                    or isinstance(score, bool) or not isinstance(score, (int, float))
                    or not math.isfinite(score) or not 0 <= score <= 100):
                raise ValueError('invalid_prediction_presentation')
            display, status = self.label(label)
            rows.append({'class_id': index, 'canonical_label': label, 'display_label': display,
                         'translation_status': status,
                         'score_text': f'{score:.{self.score_decimals}f}%'})
        warnings = []
        if any(r['translation_status'] == 'draft' for r in rows) or self.allow_draft_translations and any(
                r['display_label'] != r['canonical_label'] for r in rows):
            warnings.append('Tên tiếng Việt là bản dịch tham khảo cho đồ án, chưa được chuyên gia y tế rà soát. Nhãn gốc được giữ trong metadata.')
        if any(r['translation_status'] in {'missing', 'needs_review'} for r in rows):
            warnings.append('Một số nhãn chưa dịch đủ rõ nghĩa; đang giữ tên gốc.')
        result['presentation'] = {'SCORE_DECIMALS': self.score_decimals, 'top3': rows, 'warnings': warnings}
        result['presentation'].update(confidence_label='Điểm tự tin dự đoán (%)',
            confidence_note='Điểm tự tin là score từ model chưa calibration, không phải xác suất mắc bệnh hoặc độ tin cậy chẩn đoán.')
        reference=self.evaluation_reference
        valid=bool(reference and prediction.get('model_id')==reference['model_id']
                   and prediction.get('checkpoint_sha256')==reference['checkpoint_sha256'])
        result['presentation']['model_evaluation']=deepcopy(reference) if valid else None
        return result

    def coverage(self):
        review_only = PredictionPresenter(self.classes, self.translations, score_decimals=self.score_decimals)
        statuses = {label: review_only.label(label)[1] for label in self.classes}
        return {'canonical_labels': len(self.classes),
                **{status: [label for label, value in statuses.items() if value == status]
                   for status in ('reviewed', 'needs_review', 'missing')},
                'draft_vi': [label for label in self.classes if isinstance(self.translations.get(label), dict)
                             and self.translations[label].get('display_vi') not in (None, '', label)
                             and self.translations[label].get('needs_review') is not False],
                'original_label_fallback': [label for label in self.classes if self.label(label)[0] == label],
                'invalid_canonical_keys': sorted(set(self.translations) - set(self.classes))}
