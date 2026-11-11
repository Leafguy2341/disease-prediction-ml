"""Three frozen candidates; per-checkpoint runtime guards, no fallback/routing."""
from pathlib import Path
from threading import RLock
import numpy as np
from threadpoolctl import threadpool_limits
from src.models.ensemble import HARD, PRIORITY, hard_vote
from .prediction import (LRPredictionService, MODEL_ID, PROJECT_ROOT, ModelLoadError,
                         _file, _read, _check, protocol)

HARD_ID = 'hard_tuned_lr_svc_knn'
MODEL_NAMES = {MODEL_ID:'LR tuned C=2 — Mặc định', 'lr_baseline':'LR baseline C=1',
               HARD_ID:'Hard tuned LR + SVC + KNN'}
MEMBERS = {'logistic_regression':'lr_tuned_c2', 'linear_svc':'svc_tuned', 'knn':'knn_tuned'}


class HardVotingService:
    def __init__(self, members, frozen):
        self.members, self.frozen = members, frozen
        self.catalog = members['logistic_regression'].catalog
        self.verification = 'REAL CHECKPOINT VERIFIED'
        self._lock = RLock()

    @classmethod
    def load(cls, storage_root, tuned=None):
        root = Path(storage_root).resolve()
        frozen = protocol(); e = frozen['ensemble']
        _check(list(HARD[e['key']]) == e['members'] and list(PRIORITY) == e['priority'],
               'ensemble_policy_mismatch', 'Hard-vote members/priority khác frozen protocol.')
        _file(PROJECT_ROOT, 'src/models/ensemble.py', {'sha256':e['engine_source_sha256']})
        m = _read(_file(root, f"artifacts/metadata/runs/{e['run_id']}/tuned_ensemble_manifest.json",
                        {'sha256':e['manifest_sha256']}))
        _check(m['hard_tie_priority'] == e['priority'] and m['hard'][e['key']] == e['members']
               and m['selected_identity'] == frozen['checkpoints'][MODEL_ID]['identity']
               and m['tuning_experiment'] == frozen['tuning']['experiment_id']
               and m['tuning_manifest_sha256'] == frozen['tuning']['manifest_sha256'],
               'ensemble_policy_mismatch', 'Ensemble manifest khác selected checkpoint identity.')
        members = {name:(tuned if name=='logistic_regression' and tuned is not None else
                        LRPredictionService.load(root, model_id=key)) for name,key in MEMBERS.items()}
        _check(all(s.catalog == members['logistic_regression'].catalog for s in members.values()),
               'catalog_mismatch', 'Các member không cùng catalog.')
        return cls(members, frozen)

    def frame_from_features(self, features):
        return self.members['logistic_regression'].frame_from_features(features)

    def identity(self):
        e=self.frozen['ensemble']
        return dict(model_id=HARD_ID, result_kind='hard_vote_result', ensemble_run_id=e['run_id'],
                    ensemble_manifest_sha256=e['manifest_sha256'],
                    member_checkpoint_sha256={n:s.identity()['checkpoint_sha256'] for n,s in self.members.items()},
                    schema_sha256=self.catalog.schema_id, features=375, classes=587)

    def predict(self, frame, *, schema_sha256):
        # Reuse the LR input contract without asking it to predict probabilities.
        from .prediction import PredictionError
        if (schema_sha256 != self.catalog.schema_id or frame.shape != (1,375) or
            frame.columns.tolist() != list(self.catalog.features) or
            not np.issubdtype(frame.to_numpy().dtype,np.integer) or not np.isin(frame.to_numpy(),[0,1]).all() or not frame.to_numpy().any()):
            raise PredictionError('invalid_feature_frame','Cần DataFrame nhị phân 1×375 đúng schema.')
        with self._lock, threadpool_limits(limits=1):
            labels={n:np.asarray(s._model.predict(frame)) for n,s in self.members.items()}
            voted, ties=hard_vote(labels, tuple(self.frozen['ensemble']['members']), 587)
        winner=int(voted[0])
        return {**self.identity(), 'input_present_count':int(frame.to_numpy().sum()),
                'hard_vote_result':dict(class_id=winner,label=self.catalog.classes[winner],
                    votes=sum(int(p[0])==winner for p in labels.values()),total_members=3,tie=bool(ties),
                    members=[dict(model=n,class_id=int(p[0]),label=self.catalog.classes[int(p[0])]) for n,p in labels.items()]),
                'note':'Phiếu bầu hard voting, không phải xác suất mắc bệnh; không có Top3 probability.'}


def load_optional(storage_root, tuned):
    services, errors = {}, {}
    for key, load in [('lr_baseline', lambda: LRPredictionService.load(storage_root,model_id='lr_baseline')),
                      (HARD_ID, lambda: HardVotingService.load(storage_root,tuned))]:
        try:
            services[key]=load()
        except ModelLoadError as exc:
            errors[key]=dict(code=exc.code,message=exc.message)
        except Exception:
            errors[key]=dict(code='checkpoint_load_failed',message='Candidate verification failed; không fallback.')
    return services, errors


def registry(services, errors):
    frozen=protocol(); rows=[]
    for key,label in MODEL_NAMES.items():
        hard=key==HARD_ID;cp=frozen['checkpoints']['lr_tuned_c2' if hard else key]
        rows.append(dict(model_id=key,display_name=label,available=key in services,
            runtime_compatibility='PASS' if key in services else 'NOT VERIFIED',
            result_kind='hard_vote_result' if hard else 'probability_scores',
            checkpoint_sha256=None if hard else cp['files']['pipeline.joblib']['sha256'],
            artifact_path=(f"artifacts/metadata/runs/{frozen['ensemble']['run_id']}/tuned_ensemble_manifest.json" if hard else cp['folder']),
            checkpoint_identity=cp['identity']['experiment_id'],
            ensemble_run_id=frozen['ensemble']['run_id'] if hard else None,
            member_checkpoints={name:frozen['checkpoints'][member]['files']['pipeline.joblib']['sha256'] for name,member in MEMBERS.items()} if hard else None,
            trained_versions=cp['identity']['versions'], schema_sha256=frozen['processed']['schema_sha256'],
            features=375,classes=587,reason=errors.get(key) if key in services else errors.get(key,dict(code='not_verified',message='Model chưa được xác minh trong runtime này.')),
            ensemble_manifest_sha256=frozen['ensemble']['manifest_sha256'] if hard else None,
            deployment_approval='approved_before_final_test' if key==MODEL_ID else 'owner_requested_research_comparator',
            label_mapping_sha256=frozen['phase2_files']['artifacts/metadata/phase2/label_mapping.json']['sha256']))
    return dict(default_model_id=MODEL_ID,models=rows,online_settings_supported=False)


def render_prediction(prediction, presenter):
    from .schemas import PredictResponse, HardVoteResponse
    if prediction.get('model_id') != HARD_ID:
        return PredictResponse.model_validate(presenter.render(prediction)).model_dump()
    result = HardVoteResponse.model_validate(prediction).model_dump()
    label = result['hard_vote_result']['label']
    display, status = presenter.label(label)
    result['presentation'] = dict(display_label=display,canonical_label=label,translation_status=status)
    return HardVoteResponse.model_validate(result).model_dump()
