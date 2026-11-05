"""Deterministic, conservative extraction through the existing conversation contract.

No network, fuzzy matching, disease generation, model loading or learned policy.
The synonym dictionary is a draft for human review, not a clinical ontology.
"""
import json
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import re
import unicodedata
import uuid

from .conversation import ConversationEngine, GuardDecision, InputGuard
from .extraction import Turn, evidence_context, ExtractionError, STATES
from .provider import LLMReply


@dataclass(frozen=True)
class OfflinePolicy:
    # Dialogue heuristics only, never medical confidence thresholds.
    ask_when_present_at_most: int = 2
    question_priority: tuple = ('fever', 'cough', 'headache', 'nausea')
    fallback_to_display_catalog: bool = True
    debug_logging: bool = False
    dialogue_version: int = 1
    batch_size: int = 3
    max_question_batches: int = 4
    max_total_questions: int = 12
    min_answered_questions: int = 3
    min_present_for_result: int = 3
    max_question_rounds: int = 2
    health_keywords: tuple = ('bệnh', 'triệu chứng', 'đau', 'khối u', 'sưng', 'ngứa',
                              'khám', 'bác sĩ', 'thuốc', 'ung thư', 'mang thai', 'có bầu', 'ho', 'sốt', 'buồn nôn')
    health_body_terms: tuple = ('ngực', 'vú', 'bụng', 'cổ họng', 'đầu gối', 'bàn tay', 'bàn chân', 'phổi', 'thận',
                               'âm đạo', 'âm hộ', 'dương vật', 'tinh hoàn', 'bìu')
    health_question_patterns: tuple = ('bị gì', 'bệnh gì', 'có sao không', 'có nguy hiểm không', 'có bầu không')

    def __post_init__(self):
        if (self.dialogue_version not in (1, 2) or self.batch_size not in (1, 2, 3, 4, 5)
                or not 1 <= self.max_question_batches <= 8 or not 1 <= self.max_total_questions <= 30
                or not 0 <= self.min_answered_questions <= self.max_total_questions
                or not 2 <= self.min_present_for_result <= 375 or not 1 <= self.max_question_rounds <= 3):
            raise ValueError('invalid_batch_policy')
        if (type(self.ask_when_present_at_most) is not int or not 2 <= self.ask_when_present_at_most <= 375
                or not isinstance(self.question_priority, (list, tuple))
                or not all(isinstance(f, str) for f in self.question_priority)
                or len(set(self.question_priority)) != len(self.question_priority)
                or type(self.fallback_to_display_catalog) is not bool or type(self.debug_logging) is not bool):
            raise ValueError('invalid_offline_policy')
        for terms in (self.health_keywords, self.health_body_terms, self.health_question_patterns):
            if not isinstance(terms, (list, tuple)) or not all(isinstance(t, str) and t.strip() for t in terms):
                raise ValueError('invalid_offline_health_patterns')

    @classmethod
    def from_file(cls, path):
        return cls(**json.loads(Path(path).read_text(encoding='utf-8'))['offline'])


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold().replace('đ', 'd'))
                   if not unicodedata.combining(c))


def folded_offsets(text):
    """Map normalized match offsets back to ORIGINAL Unicode code point spans."""
    chars, offsets = [], []
    for i, c in enumerate(text):
        value = fold(c)
        chars.extend(value)
        offsets.extend([i] * len(value))
    return ''.join(chars), offsets


class HealthIntentDetector:
    """Current-turn intent only; knows no feature IDs, diseases or ML vector."""
    def __init__(self, policy):
        self.patterns = [(reason, re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(fold(t)) for t in terms) + r')(?!\w)'),
                          {unicodedata.normalize('NFC', t).casefold() for t in terms})
                         for reason, terms in (('health_keyword', policy.health_keywords),
                                               ('health_body_reference', policy.health_body_terms),
                                               ('health_question_pattern', policy.health_question_patterns)) if terms]

    def detect(self, text):
        original = text if isinstance(text, str) else ''
        text, offsets = folded_offsets(original)
        context = ('hypothetical' if re.search(r'\b(?:neu|gia su|vi du|theo sach)\b', text) else
                   'quoted' if re.search(r'\btrich dan\b', text) or any(c in original for c in ('"', '“', '`')) else
                   'other' if re.search(r'\b(?:me(?: toi)?|bo(?: toi)?|con toi|chi toi|anh toi|ba toi)\b', text) else
                   'self' if re.search(r'\b(?:toi|minh|to)\b', text) else 'unspecified')
        reason = 'no_health_cue'
        for name, pattern, exact in self.patterns:
            for match in pattern.finditer(text):
                end = offsets[match.end()-1]+1
                while end < len(original) and unicodedata.combining(original[end]):
                    end += 1
                raw = unicodedata.normalize('NFC', original[offsets[match.start()]:end]).casefold()
                if raw == fold(raw) or raw in exact:
                    reason = name
                    break
            if reason != 'no_health_cue':
                break
        return {'is_health': reason != 'no_health_cue', 'reason': reason, 'context': context}


class OfflineExtractor:
    def __init__(self, catalog, path):
        self.catalog = catalog
        self.synonyms = json.loads(Path(path).read_text(encoding='utf-8'))
        if set(self.synonyms) != set(catalog.features):
            raise ValueError('offline_dictionary_schema_mismatch')
        self.aliases = {}
        self.accented_aliases = {}
        for feature, entry in self.synonyms.items():
            entry.setdefault('display_vi', '')  # Missing display is reported/filtered, never invented.
            if (not isinstance(entry['display_vi'], str) or type(entry['needs_review']) is not bool
                    or not all(isinstance(a, str) and a.strip() for a in entry['aliases_vi'] + entry['aliases_en'])):
                raise ValueError('invalid_offline_dictionary')
            active_vi = entry['aliases_vi'] if entry.get('activation_status') != 'PENDING_REVIEW' else []
            for alias in active_vi + entry['aliases_en']:
                key = fold(alias)
                self.aliases.setdefault(key, set()).add(feature)
                self.accented_aliases.setdefault(unicodedata.normalize('NFC', alias).casefold(), set()).add(feature)
        self.pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(a) for a in
                                  sorted(self.aliases, key=len, reverse=True)) + r')(?!\w)')
        self.pending = None
        self.resolved_aliases = {}
        self.resolution_replies = set()
        self.resolution_current = False
        self.collision_pending = False
        self.answer_bindings = {}

    def candidates(self, phrase):
        raw = unicodedata.normalize('NFC', phrase).casefold()
        # Per-phrase exact accented match takes precedence; unaccented text
        # always checks every candidate in the folded collision index.
        return set(self.accented_aliases.get(raw, ())) if raw != fold(raw) else set(self.aliases.get(fold(raw), ()))

    def status(self):
        return {'mode': 'offline', 'provider': 'offline_rules', 'live_enabled': False,
                'key_required': False, 'requests_used': 0,
                'message': 'Chế độ offline — xử lý triệu chứng bằng quy tắc, không dùng dịch vụ ngôn ngữ bên ngoài.'}

    def generate(self, *, task, system, payload, schema):
        turns = [Turn(**t) for t in payload['turns']]
        if task == 'intent':
            text = fold(turns[-1].text)
            if self.answer_bindings.get(turns[-1].turn_id):
                return LLMReply({'intent': 'symptom_description', 'subject_id': payload['target_subject'],
                                 'evidence': [self.span(turns[-1], 0, len(turns[-1].text))]})
            if self.resolution_current or self.collision_pending and text.strip(' .!?') in {'co', 'khong', 'ko', 'chua'}:
                return LLMReply({'intent': 'symptom_description', 'subject_id': payload['target_subject'],
                                 'evidence': [self.span(turns[-1], 0, len(turns[-1].text))]})
            m = self.pattern.search(text) or re.search(r'\b(?:dau|te|ngua|sung|trieu chung)\b', text)
            matched = bool(m)
            intent = 'symptom_description' if matched else 'unrelated'
            # Full narrow alias evidence; canonical intent checks remain in force.
            _, offsets = folded_offsets(turns[-1].text)
            evidence = [self.span(turns[-1], offsets[m.start()], offsets[m.end()-1]+1)] if m else []
            if evidence:
                try:
                    evidence_context(turns[-1], evidence[0], payload['target_subject'], None)
                except ExtractionError:
                    intent, evidence = 'unsupported_or_ambiguous', []
            return LLMReply({'intent': intent, 'subject_id': payload['target_subject'], 'evidence': evidence})
        data = {'contract_version': 2, 'schema_sha256': self.catalog.schema_id,
                **{s: [] for s in STATES}, 'unmapped': [],
                'clarification': {'needed': False, 'reasons': [], 'target_features': []}}
        active = {}
        reasons = set()
        conflicts = set()
        pending = None
        for turn in turns:
            if turn.role != 'user':
                pending = next((f for f, entry in self.synonyms.items()
                                if turn.text == 'Bạn có bị ' + entry['display_vi'] + ' không?'), None)
                continue
            if turn.turn_id in self.resolution_replies:
                # Selection resolves an old mention's meaning, not its assertion state.
                continue
            text, offsets = folded_offsets(turn.text)
            bindings = self.answer_bindings.get(turn.turn_id, {})
            if bindings:
                for feature, binding in bindings.items():
                    active[feature] = (binding['state'], [binding['evidence']])
                    conflicts.discard(feature)
                continue
            if re.search(r'\b(?:noi nham|sua lai|dinh chinh|hien tai|bay gio|het|da khoi|khong con|xac nhan)\b', text):
                # Existing contract requires fresh evidence after an explicit update.
                # Do not silently carry symptoms lacking fresh confirmation.
                active.clear()
                reasons.clear()
                conflicts.clear()
                data['unmapped'].clear()
            short = text.strip(' \t\n.!?')
            if short in {'co', 'dung', 'vang', 'khong', 'ko', 'chua', 'chua ro', 'chua chac'}:
                focused = pending or (self.pending if turn is turns[-1] else None)
                if focused:
                    state = 'uncertain' if short in {'chua ro', 'chua chac'} else 'denied' if short in {'khong', 'ko', 'chua'} else 'present'
                    active[focused] = (state, [self.span(turn, 0, len(turn.text))])
                    conflicts.discard(focused)
                    pending = None
                continue
            covered = []
            current_mentions = []
            for match in self.pattern.finditer(text):
                start, end = offsets[match.start()], offsets[match.end()-1]+1
                while end < len(turn.text) and unicodedata.combining(turn.text[end]):
                    end += 1
                span = self.span(turn, start, end)
                aliases = self.candidates(span['text'])
                if not aliases:
                    # Accent stripping must not turn "họ" into cough ("ho").
                    continue
                chosen = self.resolved_aliases.get((turn.turn_id, start, end, payload['target_subject']))
                if chosen in aliases:
                    aliases = {chosen}
                covered.append((match.start(), match.end()))
                left = re.split(r'[.,;!?\n]|\b(?:nhung|va|con|ma)\b', text[:match.start()])[-1]
                uncertainty_scope = re.split(r'[.;!?\n]|\bnhung\b', text[:match.start()])[-1]
                uncertain = bool(re.search(r'khong (?:ro|chac)|chua (?:ro|chac)|hinh nhu|co le|co the|khong phai khong', uncertainty_scope))
                state = 'uncertain' if uncertain else 'denied' if re.search(r'\b(?:khong|ko|chua|het|da khoi|chang)\b', left) else 'present'
                if len(aliases) != 1:
                    data['unmapped'].append({'phrase': span['text'], 'state': state,
                                             'reason': 'ambiguous_mapping', 'evidence': [span]})
                    continue
                feature = next(iter(aliases))
                if feature == 'difficulty speaking' and re.match(r'\s+chuyen\b', text[match.end():]):
                    data['unmapped'].append({'phrase':span['text'], 'state':state,
                        'reason':'unclear_context', 'evidence':[span]})
                    continue  # "Khó nói chuyện" can describe communication, not motor speech.
                try:
                    evidence_context(turn, span, payload['target_subject'], state, conflicted=uncertain)
                except ExtractionError:
                    # Subject, past, quotes or hypothetical text never become present.
                    reasons.add('ambiguous')
                    continue
                current_mentions.append((feature, match.end()))
                updated = bool(re.search(r'noi nham|sua lai|dinh chinh|hien tai|bay gio|da het|khong con|xac nhan|\bhet\b', text))
                if feature in active and active[feature][0] != state and not updated:
                    # A focused answer may resolve only its pending uncertain feature.
                    state = 'uncertain'
                    conflicts.add(feature)
                    evidence = active[feature][1] + [span]
                else:
                    evidence = [span]
                active[feature] = (state, evidence[-8:])
            # Unrecognized symptom-bearing clauses block inference, including mixed input.
            remainder = list(text)
            for a, b in covered:
                remainder[a:b] = ' ' * (b-a)
            # These are modifiers of an already evidence-validated mention, not
            # additional binary symptoms. Never discard them globally (u nang,
            # nang nguc, etc.). The urgent guard has already seen the full text.
            for feature, end in current_mentions:
                qualifiers = r'(?:nang|nhe|nhieu|lien tuc)' if feature != 'fever' else r'(?:nang|nhe|nhieu|lien tuc|cao)'
                modifier = re.match(r'\s+(?:rat\s+)?' + qualifiers + r'\b', text[end:])
                if modifier:
                    remainder[end:end+modifier.end()] = ' ' * modifier.end()
            residual = ''.join(remainder)
            if current_mentions:
                # A bounded request suffix does not describe a new condition.
                # Keep cancer, masses, pregnancy and all other unknown content.
                residual = re.sub(
                    r'\b(?:thi\s+)?(?:(?:toi|minh)\s+)?(?:(?:co the|dang|co)\s+)?'
                    r'(?:(?:bi|mac|la)\s+)?benh\s+gi(?:\s+(?:khong|vay|a|nhi))*[\s.!?]*$',
                    ' ', residual)
            filler = r'\b(?:toi|minh|to|me|bo|con|dang|bi|co|khong|ko|chua|het|da|khoi|khong con|va|nhung|con|ma|tu|sang|nay|hom|qua|ngay|dem|gio|luc|rat|hoi|van|chi|moi|lai|thay|noi|nham|sua|dinh|chinh|hien|tai|bay|xac|nhan|ro|chac|hinh|nhu|le|the|phai|tuan|thang|gan|day)\b'
            unexplained = re.sub(filler, ' ', residual)
            if re.search(r'[^\W\d_]', unexplained):
                unknown_state = 'uncertain' if re.search(r'khong ro|chua chac|co le|hinh nhu', text) else 'denied' if re.search(r'\b(?:khong|ko|chua|het)\b', text) else 'present'
                data['unmapped'].append({'phrase': turn.text, 'state': unknown_state,
                                         'reason': 'unclear_context', 'evidence': [self.span(turn, 0, len(turn.text))]})
        for feature, (state, evidence) in active.items():
            data[state].append({'feature': feature, 'evidence': evidence})
        if conflicts:
            reasons.add('conflict')
        if any(state == 'uncertain' for state, _ in active.values()):
            reasons.add('uncertain')
        if data['unmapped']:
            reasons.add('unmapped')
        data['clarification'] = {'needed': bool(reasons), 'reasons': sorted(reasons),
                                 'target_features': [f for f, (s, _) in active.items() if s == 'uncertain'][:2]}
        return LLMReply(data)

    @staticmethod
    def span(turn, start, end):
        return {'turn_id': turn.turn_id, 'start': start, 'end': end, 'text': turn.text[start:end]}


class OfflineGuard(InputGuard):
    def check(self, text, subject_id='self', *, context_reply=False):
        decision = super().check(text, subject_id, context_reply=context_reply)
        if not isinstance(text, str) or decision.intent in {'urgent', 'instruction_injection'} or decision.reason in {
                'empty_or_invalid_input', 'input_too_long', 'invalid_characters', 'user_stopped'}:
            return decision
        if decision.intent == 'medical_information_question':
            return GuardDecision(None, 'offline_health_context')
        normalized = fold(text)
        sudden = re.search(r'(?:dot ngot|bat ngo).{0,35}(?:kho noi|noi ngong|yeu nua nguoi)|(?:kho noi|noi ngong|yeu nua nguoi).{0,35}(?:dot ngot|bat ngo)', normalized)
        if sudden:
            _, positions = folded_offsets(text)
            try:
                evidence_context(Turn('guard', 'user', text, subject_id),
                    OfflineExtractor.span(Turn('guard', 'user', text, subject_id),
                                          positions[sudden.start()], positions[sudden.end()-1]+1), subject_id, 'present')
                return GuardDecision('urgent', 'sudden_neurological_language')
            except ExtractionError:
                pass
        if normalized.strip(' .!?') in {'xin chao', 'chao', 'hello', 'hi'}:
            return GuardDecision('unsupported_or_ambiguous', 'offline_greeting')
        # Apply existing guard also to a cue-restored view; original evidence stays untouched.
        cues = {'kho tho nang': 'khó thở nặng', 'tho khong noi': 'thở không nổi',
                'khong the noi thanh cau': 'không thể nói thành câu',
                'khong the noi tron cau': 'không thể nói trọn câu',
                'khong noi thanh cau': 'không nói thành câu',
                'khong noi tron cau': 'không nói trọn câu',
                'ngat tho': 'ngạt thở', 'khong': 'không', 'toi': 'tôi', 'sot': 'sốt',
                'bo qua': 'bỏ qua', 'huong dan': 'hướng dẫn', 'quy tac': 'quy tắc',
                'la gi': 'là gì', 'nguyen nhan': 'nguyên nhân', 'trieu chung cua': 'triệu chứng của'}
        for a in sorted(cues, key=len, reverse=True):
            normalized = re.sub(r'(?<!\w)' + re.escape(a) + r'(?!\w)', cues[a], normalized)
        other = super().check(normalized, subject_id, context_reply=context_reply)
        if other.intent in {'urgent', 'instruction_injection'}:
            return other
        if other.intent == 'medical_information_question':
            return GuardDecision(None, 'offline_health_context')
        if re.search(r'\b(?:neu|gia su|vi du|theo sach|trich dan)\b', fold(text)) or any(c in text for c in ['"', '“', '`']):
            return GuardDecision('unsupported_or_ambiguous', 'hypothetical_or_quoted_context')
        if context_reply and (re.match(r'^\s*\d', text) or fold(text).strip(' .!?') in
                              {'co','khong','khong co cai nao','toi khong biet','khong ro','chua tra loi'}):
            return GuardDecision(None, 'offline_pending_answer')
        return GuardDecision(None, 'offline_context_check') if decision.reason == 'uncertain_statement' else decision


class OfflineConversation(ConversationEngine):
    def __init__(self, catalog, provider, policy=None, *, offline_policy=None):
        super().__init__(catalog, provider, policy)
        self.guard = OfflineGuard(self.policy)
        self.offline_policy = offline_policy or OfflinePolicy()
        self.health_detector = HealthIntentDetector(self.offline_policy)
        if not set(self.offline_policy.question_priority) <= set(catalog.features):
            raise ValueError('offline_question_feature_not_in_schema')

    @staticmethod
    def _state(session):
        # Session-owned extension; same SessionStore, TTL, lock and reset behavior.
        if not hasattr(session, 'offline'):
            session.offline = {'pending_clarification': None, 'resolutions': {},
                               'resolution_replies': set(), 'selector': 'not_run', 'limited': False}
        return session.offline

    def _remaining(self, session):
        if self.offline_policy.dialogue_version == 2:
            return max(0, self.offline_policy.max_total_questions -
                       (session.questions - self.batch_state(session)['round_start_questions']))
        return max(0, self.policy.max_clarification_turns - session.questions)

    def batch_state(self, session):
        state = self._state(session)
        return state.setdefault('batch', {'pending': None, 'count': 0, 'answered': set(), 'bindings': {},
            'round':1, 'round_start_questions':0, 'round_start_batches':0, 'answer_error':False})

    def _ask_batch(self, session, turn, intent, telemetry, value):
        state = self.batch_state(session)
        pending = state['pending']
        if pending:
            for item in pending['items']:
                if item['state'] is None and item['feature'] in value.states:
                    item['state'] = value.states[item['feature']]
                    state['answered'].add(item['feature'])
        if pending and any(item['state'] is None for item in pending['items']):
            return super()._finish(session, turn, 'clarification_required', intent, 'offline_batch_partial',
                'Bạn có thể trả lời các mục còn lại; mục chưa trả lời không được xem là không có triệu chứng.',
                telemetry, sidecar=value.sidecar(self.catalog))
        if state['count'] - state['round_start_batches'] >= self.offline_policy.max_question_batches or not self._remaining(session):
            self._state(session)['selector'] = 'question_round_budget_exhausted'
            return None
        known = set(value.states)
        groups = json.loads((Path(__file__).resolve().parents[2] / 'configs/synonyms.json').read_text(encoding='utf-8'))
        active_groups = {groups[f].get('question_group') for f in known if value.states[f] == 'present'} - {None}
        eligible = [f for f in self.catalog.features if f not in known
                    and session.subject_id + ':' + f not in session.asked
                    and groups[f].get('question_eligible', False)
                    and groups[f].get('activation_status') != 'PENDING_REVIEW'
                    and groups[f].get('question_group') in (active_groups | {'general'} if active_groups else {'general'})]
        priority = {f:i for i,f in enumerate(self.offline_policy.question_priority)}
        eligible.sort(key=lambda f: (groups[f].get('question_group') not in active_groups,
                                      priority.get(f, len(priority)), self.catalog.features.index(f)))
        selected = eligible[:min(self.offline_policy.batch_size, self._remaining(session))]
        if not selected:
            self._state(session)['selector'] = 'no_relevant_unasked_candidate'
            return None
        self._state(session)['selector'] = 'context_group_questions'
        state['count'] += 1
        session.questions += len(selected)
        session.asked.update(session.subject_id + ':' + f for f in selected)
        session.pending_feature = None
        items = [{'number':i+1, 'feature':f, 'text':groups[f]['display_vi'], 'state':None} for i,f in enumerate(selected)]
        state['pending'] = {'batch_id':uuid.uuid4().hex, 'epoch':session.epoch,
                            'subject_id':session.subject_id, 'items':items}
        question = 'Bạn có các triệu chứng sau không?\n' + '\n'.join(str(i['number'])+'. '+i['text'] for i in items)
        session.turns.append(Turn('b'+str(state['count']), 'assistant', question, session.subject_id))
        return super()._finish(session, turn, 'clarification_required', intent, 'offline_batch_questions', question,
                               telemetry, sidecar=value.sidecar(self.catalog))

    def _bind_batch(self, session, text, batch_id):
        """Parse only exact bounded answers. Never guess an omitted item's state."""
        state = self.batch_state(session)
        pending = state['pending']
        if not pending:
            return 'stale_batch' if batch_id else None
        if pending['epoch'] != session.epoch or pending['subject_id'] != session.subject_id:
            return 'stale_batch'
        raw_folded = fold(text)
        normalized = raw_folded.strip(' .!?')
        prefix = len(raw_folded) - len(raw_folded.lstrip(' .!?'))
        numeric = bool(re.match(r'^\s*(?:toi\s+)?(?:co\s+)?\d', normalized))
        if batch_id and batch_id != pending['batch_id'] or numeric and batch_id != pending['batch_id']:
            return 'stale_batch'
        answers = {}
        if re.fullmatch(r'\d+\s+(?:co|khong|khong ro|chua ro|chua tra loi)(?:\s*[,;]\s*\d+\s+(?:co|khong|khong ro|chua ro|chua tra loi))*', normalized):
            for m in re.finditer(r'(\d+)\s+(khong ro|chua ro|chua tra loi|khong|co)', normalized):
                number = int(m[1])
                if number in answers or number < 1 or number > len(pending['items']):
                    return 'invalid_batch_answer'
                status = {'co':'present','khong':'denied','khong ro':'uncertain','chua ro':'uncertain','chua tra loi':None}[m[2]]
                answers[number] = (status, m.start(), m.end())
        elif re.fullmatch(r'(?:toi\s+)?co\s+\d+(?:\s*[,;]\s*\d+)*(?:\s+va\s+\d+)?', normalized):
            for m in re.finditer(r'\d+', normalized):
                number = int(m[0])
                if number in answers or not 1 <= number <= len(pending['items']):
                    return 'invalid_batch_answer'
                answers[number] = ('present', m.start(), m.end())
        elif normalized in {'khong co cai nao','toi khong biet','khong ro','co','khong'}:
            unresolved = [i for i in pending['items'] if i['state'] is None]
            if normalized not in {'co','khong'} and len(unresolved) != len(pending['items']):
                return 'ambiguous_batch_answer'  # Could be a correction of earlier answers.
            if normalized in {'co','khong'} and len(unresolved) != 1:
                return 'ambiguous_batch_answer'
            selected = unresolved
            status = 'denied' if normalized in {'khong co cai nao','khong'} else 'present' if normalized=='co' else 'uncertain'
            answers = {i['number']:(status,0,len(text)) for i in selected}
        elif numeric:
            return 'invalid_batch_answer'
        else:
            return None  # Ordinary free text goes through the original extractor.
        bindings = {}
        _, offsets = folded_offsets(text)
        for number, (status, start, end) in answers.items():
            item = pending['items'][number-1]
            if item['state'] is not None and not (item['state']=='uncertain' and status in {'present','denied'}):
                return 'already_answered'  # Explicit corrections use ordinary symptom text.
            if status is None:
                continue
            if numeric:
                a, b = offsets[start+prefix], offsets[end-1+prefix]+1
            else:
                a, b = 0, len(text)
            while b < len(text) and unicodedata.combining(text[b]): b += 1
            bindings[item['feature']] = {'state':status,'subject_id':session.subject_id,
                'evidence':{'turn_id':'u'+str(session.user_turns+1),'start':a,'end':b,'text':text[a:b]}}
        if not bindings:
            return 'empty_batch_answer'
        # Commit only after all entries have passed bounds/duplicate checks.
        for item in pending['items']:
            if item['feature'] in bindings:
                item['state'] = bindings[item['feature']]['state']
                state['answered'].add(item['feature'])
        state['bindings']['u'+str(session.user_turns+1)] = bindings
        return None

    def _classify(self, session, turns):
        if self.offline_policy.dialogue_version == 2 and self.provider.answer_bindings.get(turns[-1].turn_id):
            return 'symptom_description', []
        intent, telemetry = super()._classify(session, turns)
        # Do not derive health intent from previous turns or past predictions.
        if intent in {'unrelated', 'unsupported_or_ambiguous', 'medical_information_question'} and self.health_detector.detect(turns[-1].text)['is_health']:
            return 'unsupported_health', telemetry
        return intent, telemetry

    def _unsupported_health(self, session, turn, intent, telemetry=(), value=None):
        session.pending_feature = None
        self._state(session)['pending_clarification'] = None
        message = ('Phần mô tả sức khỏe này chưa được ánh xạ đầy đủ vào 375 triệu chứng mà chatbot hỗ trợ. '
                   'Mô hình chỉ dự đoán trong 587 nhãn đã học, không thể khẳng định hoặc loại trừ bệnh ngoài phạm vi; chưa có Top 3. '
                   'Bạn hãy mô tả triệu chứng thực tế đang gặp. Nếu có khối bất thường, triệu chứng kéo dài hoặc dấu hiệu đáng lo ngại, hãy tìm tư vấn y tế phù hợp.')
        return self._finish(session, turn, 'unsupported_health', 'unsupported_health', 'offline_unsupported_health', message,
                            telemetry, sidecar=value.sidecar(self.catalog) if value else None)

    def _select_question(self, session, value):
        def eligible(feature):
            display = self.provider.synonyms[feature]['display_vi'].strip()
            # English placeholders are reported for review, not presented as Vietnamese.
            return (feature not in value.states and session.subject_id + ':' + feature not in session.asked
                    and display and display != feature
                    and self.provider.synonyms[feature].get('activation_status') != 'PENDING_REVIEW')
        primary = next((f for f in self.offline_policy.question_priority if eligible(f)), None)
        if primary:
            return primary, 'priority_question'
        if self.offline_policy.fallback_to_display_catalog:
            fallback = next((f for f in self.catalog.features if eligible(f)), None)
            if fallback:
                return fallback, 'display_catalog_fallback'
        return None, 'no_eligible_display_question'

    def _ask_feature(self, session, turn, feature, intent, reason, telemetry, value):
        session.questions += 1
        session.asked.add(session.subject_id + ':' + feature)
        session.pending_feature = feature
        question = 'Bạn có bị ' + self.provider.synonyms[feature]['display_vi'] + ' không?'
        session.turns.append(Turn('a' + str(session.questions), 'assistant', question, session.subject_id))
        return self._finish(session, turn, 'clarification_required', intent, reason, question,
                            telemetry, sidecar=value.sidecar(self.catalog))

    def _finish(self, session, turn, status, intent, reason, message, telemetry=(), *, sidecar=None, reset=False):
        state = self._state(session)
        if self.offline_policy.dialogue_version == 2:
            batch = self.batch_state(session)
            if reset:
                batch['pending'] = None
                batch['bindings'].clear()
            if status == 'extraction_ready':
                value = session.validated
                pending = batch['pending']
                if pending:
                    for item in pending['items']:
                        if item['feature'] in value.states and item['state'] is None:
                            item['state'] = value.states[item['feature']]
                            batch['answered'].add(item['feature'])
                count = sum(s == 'present' for s in value.states.values())
                if (count < self.offline_policy.min_present_for_result
                        or len(batch['answered']) < self.offline_policy.min_answered_questions
                        or pending and any(i['state'] is None for i in pending['items'])):
                    asked = self._ask_batch(session, turn, intent, telemetry, value)
                    if asked: return asked
                    if count < self.offline_policy.min_present_for_result:
                        status, reason, message = 'abstained', 'offline_v2_insufficient', 'Dữ kiện còn quá ít hoặc chưa rõ và đã hết câu hỏi phù hợp; chưa hiển thị Top 3.'
                    else:
                        status, reason, message = 'abstained', 'offline_v2_insufficient', 'Chưa hoàn tất thu thập dữ kiện. Bạn có thể hỏi thêm hoặc chủ động xem kết quả tham khảo.'
                else:
                    reason = 'offline_v2_ready'
                state['limited'] = reason.startswith('offline_limited_')
            return super()._finish(session, turn, status, intent, reason, message, telemetry, sidecar=sidecar, reset=reset)
        if reset:
            state['pending_clarification'] = None
            state['resolutions'].clear()
            state['resolution_replies'].clear()
        if status == 'extraction_ready':
            state['pending_clarification'] = None
            value = session.validated
            count = sum(s == 'present' for s in value.states.values())
            if count <= self.offline_policy.ask_when_present_at_most:
                if self._remaining(session):
                    feature, selector = self._select_question(session, value)
                    state['selector'] = selector
                    if feature:
                        return self._ask_feature(session, turn, feature, intent, 'offline_collect_more', telemetry, value)
                    reason = 'offline_limited_no_eligible_question'
                else:
                    state['selector'] = 'question_budget_exhausted'
                    reason = 'offline_limited_question_budget'
                # Only reached after the unchanged canonical gate has passed.
                state['limited'] = True
                message = 'Thông tin còn hạn chế; kết quả chỉ là gợi ý nghiên cứu với dữ kiện ít.'
            else:
                state['limited'] = False
                state['selector'] = 'enough_present_for_dialogue_policy'
                reason = 'offline_dialogue_ready'
        return super()._finish(session, turn, status, intent, reason, message, telemetry,
                               sidecar=sidecar, reset=reset)

    def control(self, action, *, session_id=None, subject_id=None):
        """Explicit user controls reuse the current validated extraction and LR port."""
        from .conversation import ConversationResult
        with self.store.lock:
            try:
                session = self.store.get(session_id) if session_id else self.store.get(self.start(subject_id or 'self'))
            except ValueError:
                return ConversationResult(None,None,'abstained','unsupported_or_ambiguous','invalid_session','Phiên đã hết hạn; hãy bắt đầu phiên mới.')
            session.invalidate()
            session.user_turns += 1
            turn = Turn('u'+str(session.user_turns),'user','',session.subject_id)
            def finish(status, reason, message):
                return super(OfflineConversation,self)._finish(session,turn,status,'symptom_description',reason,message,
                    sidecar=session.validated.sidecar(self.catalog) if session.validated else None)
            if session.stopped or session.user_turns > self.policy.max_user_turns:
                session.stopped=True
                return finish('abstained','conversation_limit','Phiên đã đạt giới hạn an toàn; hãy tạo cuộc trò chuyện mới.')
            if subject_id and subject_id != session.subject_id:
                return finish('abstained','control_subject_mismatch','Hãy mô tả triệu chứng cho chủ thể mới trước khi yêu cầu kết quả.')
            value=session.validated
            if value is None:
                return finish('abstained','no_validated_symptoms','Chưa có triệu chứng đã kiểm chứng. Bạn hãy mô tả triệu chứng đang gặp.')
            batch=self.batch_state(session)
            if session.result and session.result.status in {'unsupported_health','out_of_scope','provider_error','model_error','urgent_redirect'}:
                batch['answer_error']=True
            # Revalidate original evidence, not the control label or an assistant question.
            turns=session.turns[session.epoch:]
            last=next((i for i,t in enumerate(turns) if t.turn_id==value.turn_id),None)
            try:
                if last is None: raise ExtractionError('stale_control_evidence')
                value=self.validator.validate(value.data,turns[:last+1],session.subject_id,
                    answer_bindings=batch['bindings'])
            except ExtractionError:
                return finish('abstained','invalid_control_evidence','Thông tin cần được mô tả và kiểm tra lại trước khi tiếp tục.')
            reason=self.validator.gate(value,min_present_features=1)
            if action=='preview':
                if reason or batch['answer_error'] or self._state(session)['pending_clarification']:
                    return finish('clarification_required','preview_requires_clarity',
                        'Chưa thể xem tham khảo: cần ít nhất một triệu chứng hiện diện và phải làm rõ phần chưa chắc, mâu thuẫn hoặc chưa ánh xạ.')
                session.ready_frame=self.validator.frame(value,min_present_features=1)
                return finish('extraction_ready','offline_requested_preview',
                    'Kết quả tham khảo với thông tin còn hạn chế; bạn chủ động yêu cầu xem từ những triệu chứng đã kiểm chứng.')
            if action!='more':
                return finish('abstained','unsupported_control','Thao tác chưa được hỗ trợ.')
            if reason not in {None,'insufficient'} or batch['answer_error']:
                return finish('clarification_required','offline_resolve_uncertain',
                    'Hãy làm rõ các mục Không rõ hoặc mô tả lại phần mâu thuẫn/chưa hiểu trước khi hỏi tiếp.')
            pending=batch['pending']
            if pending and any(i['state'] is None for i in pending['items']):
                return self._ask_batch(session,turn,'symptom_description',[],value)
            exhausted=(batch['count']-batch['round_start_batches']>=self.offline_policy.max_question_batches or not self._remaining(session))
            if exhausted:
                if batch['round']>=self.offline_policy.max_question_rounds:
                    return finish('abstained','question_round_limit','Đã hết số vòng hỏi. Bạn vẫn có thể bổ sung triệu chứng hoặc xem tham khảo nếu đủ điều kiện.')
                batch.update(round=batch['round']+1,round_start_questions=session.questions,round_start_batches=batch['count'])
            asked=self._ask_batch(session,turn,'symptom_description',[],value)
            return asked or finish('abstained','no_relevant_questions',
                'Không còn câu hỏi phù hợp chưa hỏi. Bạn có thể tự bổ sung triệu chứng hoặc xem kết quả tham khảo hiện tại.')

    def handle(self, text, *, session_id=None, subject_id=None, batch_id=None, action='message'):
        if self.offline_policy.dialogue_version==2:
            if isinstance(text,str) and action=='message':
                action={'hoi them trieu chung':'more','xem ket qua tham khao hien tai':'preview'}.get(fold(text).strip(' .!?'),action)
            if action!='message':
                if text and self.guard.check(text,subject_id or 'self').intent=='urgent':
                    return super().handle(text,session_id=session_id,subject_id=subject_id)
                return self.control(action,session_id=session_id,subject_id=subject_id)
        with self.store.lock:
            self.provider.pending = None
            self.provider.answer_bindings = {}
            self.provider.resolved_aliases = {}
            self.provider.resolution_replies = set()
            self.provider.resolution_current = False
            self.provider.collision_pending = False
            try:
                session = self.store.get(session_id) if session_id else None
            except ValueError:
                session = None
            if session:
                state = self._state(session)
                state['selector'] = 'not_run'
                state['limited'] = False
                # A subject/current-state change cannot inherit old disambiguation.
                changed = subject_id and subject_id != session.subject_id or isinstance(text, str) and re.search(
                    r'\b(?:chuyen sang hoi cho|tu day toi hoi cho|noi nham|sua lai|dinh chinh|hien tai|bay gio|het|da khoi|khong con|xac nhan)\b', fold(text))
                if changed:
                    state['pending_clarification'] = None
                    state['resolutions'].clear()
                    state['resolution_replies'].clear()
                    if self.offline_policy.dialogue_version == 2:
                        self.batch_state(session)['pending'] = None
                        self.batch_state(session)['bindings'].clear()
                        self.batch_state(session)['answered'].clear()
                if self.offline_policy.dialogue_version == 2:
                    # Guard sees original text before parsing a batch answer.
                    decision = self.guard.check(text, subject_id or session.subject_id, context_reply=True)
                    error = (None if session.stopped or not isinstance(text, str) or decision.intent in {'urgent','instruction_injection'}
                             or decision.reason in {'empty_or_invalid_input','input_too_long','invalid_characters'}
                             else self._bind_batch(session, text, batch_id))
                    if error:
                        self.batch_state(session)['answer_error']=True
                        session.invalidate()
                        session.user_turns += 1
                        from .conversation import ConversationResult
                        result = ConversationResult(session.session_id, 'u'+str(session.user_turns), 'clarification_required',
                            'symptom_description', error, '', session.subject_id)
                        if session.validated:
                            result.sidecar = session.validated.sidecar(self.catalog)
                        result.message = 'Câu trả lời chưa gắn rõ với nhóm hiện tại. Hãy dùng các lựa chọn Có/Không/Không rõ bên dưới.'
                        if session.user_turns > self.policy.max_user_turns:
                            session.stopped = True
                            self.batch_state(session)['pending'] = None
                            result.status, result.reason = 'abstained', 'conversation_limit'
                            result.message = 'Phiên đã đạt giới hạn lượt; hãy bắt đầu cuộc trò chuyện mới.'
                        session.result = result
                        return result
                    self.batch_state(session)['answer_error']=False
                    self.provider.answer_bindings = dict(self.batch_state(session)['bindings'])
                pending = state['pending_clarification']
                if pending and pending['subject_id'] == session.subject_id and isinstance(text, str):
                    reply = unicodedata.normalize('NFC', text).casefold().strip(' \t\n.!?')
                    candidates = pending['candidate_features']
                    ordinals = {'cai dau': 0, 'cai thu nhat': 0, 'thu nhat': 0, '1': 0,
                                'cai thu hai': 1, 'thu hai': 1, '2': 1}
                    chosen = None
                    if fold(reply) in ordinals and ordinals[fold(reply)] < len(candidates):
                        chosen = candidates[ordinals[fold(reply)]]
                    else:
                        exact = self.provider.candidates(reply) & set(candidates)
                        if len(exact) == 1:
                            chosen = next(iter(exact))
                    if chosen:
                        span = pending['evidence']
                        proof_key = (span['turn_id'], span['start'], span['end'], pending['subject_id'])
                        state['resolutions'][proof_key] = chosen
                        state['resolution_replies'].add('u' + str(session.user_turns + 1))
                        state['pending_clarification'] = None
                        self.provider.resolution_current = True
                self.provider.pending = session.pending_feature
                self.provider.resolved_aliases = dict(state['resolutions'])
                self.provider.resolution_replies = set(state['resolution_replies'])
                self.provider.collision_pending = state['pending_clarification'] is not None
            result = super().handle(text, session_id=session_id, subject_id=subject_id)
            self.log_debug(result)
            return result

    def _clarify(self, session, turn, intent, reason, telemetry=(), value=None):
        state = self._state(session)
        if self.offline_policy.dialogue_version == 2 and value is not None and reason in {'insufficient','uncertain'}:
            if not value.data['unmapped']:
                if reason=='uncertain':
                    return self._finish(session,turn,'clarification_required',intent,'offline_resolve_uncertain',
                        'Có triệu chứng chưa rõ. Bạn có thể sửa từng mục Không rõ hoặc mô tả lại bằng câu đầy đủ.',telemetry,
                        sidecar=value.sidecar(self.catalog))
                asked = self._ask_batch(session, turn, intent, telemetry, value)
                if asked: return asked
                return self._finish(session, turn, 'abstained', intent, 'offline_v2_insufficient',
                    'Thông tin chưa đủ rõ; chưa hiển thị Top 3. Bạn có thể bổ sung hoặc sửa triệu chứng.',
                    telemetry, sidecar=value.sidecar(self.catalog))
        if reason == 'offline_greeting':
            session.pending_feature = None
            state['pending_clarification'] = None
            return self._finish(session, turn, 'clarification_required', intent, reason,
                                'Chào bạn! Mình ghi nhận triệu chứng bằng quy tắc offline. Bạn đang gặp triệu chứng gì?')
        collisions = [item for item in value.data['unmapped'] if item['reason'] == 'ambiguous_mapping'] if value else []
        if collisions:
            item = collisions[0]
            span = item['evidence'][0]
            candidates = sorted(self.provider.candidates(item['phrase']))
            if len(candidates) < 2:
                return self._finish(session, turn, 'abstained', intent, 'offline_collision_invalid_candidates',
                                    'Chưa xác định được nghĩa của triệu chứng; chưa có kết quả.', sidecar=value.sidecar(self.catalog))
            state['pending_clarification'] = {'candidate_features': candidates, 'evidence': deepcopy(span),
                                               'state': item['state'], 'subject_id': session.subject_id}
            session.pending_feature = None
            key = session.subject_id + ':collision:' + span['turn_id'] + ':' + str(span['start'])
            if not self._remaining(session) or key in session.asked:
                state['selector'] = 'collision_question_budget_exhausted' if not self._remaining(session) else 'collision_already_asked'
                return self._finish(session, turn, 'abstained', intent, 'offline_collision_unresolved',
                                    'Cụm triệu chứng vẫn chưa rõ nghĩa; không đủ thông tin để dự đoán.', sidecar=value.sidecar(self.catalog))
            session.questions += 1
            session.asked.add(key)
            displays = [self.provider.synonyms[f]['display_vi'].strip() for f in candidates]
            question = 'Bạn muốn nói ' + ' hay '.join(displays) + '? Hãy chọn tên rõ dấu hoặc số thứ tự.'
            session.turns.append(Turn('a' + str(session.questions), 'assistant', question, session.subject_id))
            state['selector'] = 'alias_collision_candidates'
            return self._finish(session, turn, 'clarification_required', intent, 'offline_alias_collision', question,
                                telemetry, sidecar=value.sidecar(self.catalog))
        health = self.health_detector.detect(turn.text)
        # Health keywords describe a topic, not a reason to reject known symptoms.
        # A validated state (even denied/uncertain) continues through the usual
        # gate and clarification unless there is genuinely unmapped content.
        if health['is_health'] and (value is None or not value.states or value.data['unmapped']):
            return self._unsupported_health(session, turn, intent, telemetry, value)
        if reason not in {'insufficient', 'uncertain', 'conflict'} or value is None:
            return super()._clarify(session, turn, intent, reason, telemetry, value)
        if not self._remaining(session):
            state['selector'] = 'question_budget_exhausted'
            return self._finish(session, turn, 'abstained', intent, 'offline_insufficient_question_budget',
                                'Thông tin chưa đủ rõ và đã hết lượt hỏi; chưa có dự đoán.', telemetry,
                                sidecar=value.sidecar(self.catalog))
        if reason == 'insufficient':
            feature, selector = self._select_question(session, value)
        else:
            feature = next((f for f, s in value.states.items() if s == 'uncertain'
                            and session.subject_id + ':' + f not in session.asked), None)
            selector = 'resolve_uncertain_feature' if feature else 'no_unasked_uncertain_feature'
        state['selector'] = selector
        if feature:
            return self._ask_feature(session, turn, feature, intent, reason, telemetry, value)
        return self._finish(session, turn, 'abstained', intent, 'offline_insufficient_no_eligible_question',
                            'Không còn câu hỏi phù hợp và thông tin chưa đủ; chưa có dự đoán.', telemetry,
                            sidecar=value.sidecar(self.catalog))

    def log_debug(self, result, *, scores=None, translation_stats=None):
        if not self.offline_policy.debug_logging or not result.session_id:
            return
        try:
            session = self.store.get(result.session_id)
        except ValueError:
            return
        state = self._state(session)
        action = ('URGENT_GUIDANCE' if result.status == 'urgent_redirect' else
                  'UNSUPPORTED_HEALTH' if result.status == 'unsupported_health' else
                  'REQUEST_CLARIFICATION' if result.reason == 'offline_alias_collision' else
                  'ASK' if result.status == 'clarification_required' else
                  'SHOW_LIMITED_RESULT' if result.status == 'extraction_ready' and state['limited'] else
                  'SHOW_RESULT' if result.status == 'extraction_ready' else 'ABSTAIN')
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.hasHandlers():
            logger.addHandler(logging.StreamHandler())
        logger.info(json.dumps({
            'event': 'offline_prediction' if scores is not None else 'offline_policy',
            'session': hashlib.sha256(result.session_id.encode()).hexdigest()[:12],
            'action': action, 'reason': result.reason,
            'present_count': sum(s == 'present' for s in (result.sidecar or {}).get('states', {}).values()),
            'asked_count': session.questions, 'remaining_question_budget': self._remaining(session),
            'pending_clarification': state['pending_clarification'] is not None,
            'selector': state['selector'], 'top3_model_scores': scores,
            'health_intent': self.health_detector.detect(next((t.text for t in reversed(session.turns) if t.role == 'user'), '')),
            'matched_count': len((result.sidecar or {}).get('states', {})),
            'unmatched_count': len((result.sidecar or {}).get('unmapped', [])),
            'unsupported_health_reason': 'no_supported_current_description' if result.status == 'unsupported_health' else None,
            'translation_stats': translation_stats,
        }, separators=(',', ':')))
