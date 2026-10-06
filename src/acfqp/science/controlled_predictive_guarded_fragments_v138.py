"""Observed two-action symbolic fragments over frozen 2048 rewrite primitives."""
from collections import Counter
from dataclasses import asdict, dataclass

from .controlled_predictive_parametric_contract_v75 import ACTION_ORDER, _Trace, _value

SCHEMA = 'acfqp.guarded_fragments.v138'


def _validate_rule(rule):
    p = rule.program
    if (p.pack, p.merge_relation, p.rank_increment, p.consumption,
            p.reward_rule, rule.spawn_location) != (True, 'equal', 1, 'once', 'output_value', 'uniform'):
        raise ValueError('V138 requires the frozen equal-merge, once-consumed rewrite rule')
    if set(dict(rule.spawn_distribution)) != {1, 2} or rule.goal_rank <= 2:
        raise ValueError('V138 requires rank-one/rank-two spawns below the goal')


def _inputs(root, actions, spawns, rule, work):
    root, actions = tuple(root), tuple(actions)
    if len(root) != 16 or len(actions) != 2 or len(spawns) != 2:
        raise ValueError('a fragment requires sixteen cells, two actions and two spawns')
    if any(action not in ACTION_ORDER for action in actions):
        raise ValueError('unknown fragment action')
    cells, ranks = tuple(s['cell'] for s in spawns), tuple(s['rank'] for s in spawns)
    work.update(input_rank_reads=18, input_cell_reads=2)
    if (any(rank < 0 for rank in root) or not any(root) or max(root) >= rule.goal_rank
            or any(rank not in (1, 2) for rank in ranks) or any(not 0 <= cell < 16 for cell in cells)):
        return None
    zero_mask = sum(1 << cell for cell, rank in enumerate(root) if rank == 0)
    work['zero_mask_rank_reads'] += 16
    return (actions, cells, zero_mask), root+ranks


def _expected(exit_board, scores, status):
    if len(exit_board) != 16 or len(scores) != 2 or status not in ('ACTIVE', 'WON', 'LOST'):
        raise ValueError('fragment outcome must contain a full exit, two scores and a terminal status')
    return dict(exit_board=list(exit_board), scores=list(scores), cumulative_score=sum(scores),
        status=status, duration=2)


@dataclass(frozen=True)
class Fragment:
    zero_mask: int
    actions: tuple
    spawn_cells: tuple
    guards: tuple
    exit_expressions: tuple
    reward_expressions_by_step: tuple
    anchor_binding: tuple
    instruction_footprint: tuple


class GuardedFragmentCache:
    def __init__(self, rule):
        _validate_rule(rule)
        self.rule, self.buckets, self.work = rule, {}, Counter()

    def _matches(self, fragment, binding):
        self.work['guard_trials'] += 1
        for kind, left, right, expected in fragment.guards:
            self.work['guard_checks'] += 1
            if kind == 'EQ':
                actual = _value(left, binding) == _value(right, binding)
                self.work['guard_rank_reads'] += int(left[0] >= 0)+int(right[0] >= 0)
            else:
                actual = _value(left, binding) >= right
                self.work['guard_rank_reads'] += int(left[0] >= 0)
            if actual != expected:
                self.work['guard_rejections'] += 1
                return False
        return True

    def _bind(self, fragment, binding):
        board = []
        for expression in fragment.exit_expressions:
            board.append(0 if expression is None else _value(expression, binding))
            self.work['bound_exit_cells'] += 1
            if expression is not None:
                self.work['bound_exit_rank_reads'] += int(expression[0] >= 0)
        scores = []
        for expressions in fragment.reward_expressions_by_step:
            score = 0
            for expression in expressions:
                score += 1 << _value(expression, binding)
                self.work.update(bound_reward_terms=1, bound_reward_additions=1)
            scores.append(score)
        status_work = Counter()
        status, _ = self.rule.classify(board, status_work)
        self.work.update({f'exit_status_{name}': count for name, count in status_work.items()})
        self.work.update(bind_calls=1, cumulative_score_additions=1)
        return _expected(board, scores, status)

    def lookup(self, root, actions, spawns):
        self.work['lookup_calls'] += 1
        inputs = _inputs(root, actions, spawns, self.rule, self.work)
        if inputs is None:
            self.work.update(applicability_rejections=1, misses=1)
            return None
        key, binding = inputs
        for fragment in self.buckets.get(key, ()):
            if self._matches(fragment, binding):
                self.work['hits'] += 1
                if binding[:16] != fragment.anchor_binding[:16]:
                    self.work['new_numeric_board_hits'] += 1
                if binding != fragment.anchor_binding:
                    self.work['new_numeric_binding_hits'] += 1
                return self._bind(fragment, binding)
        self.work['misses'] += 1
        return None

    def _compile(self, key, binding):
        actions, cells, zero_mask = key
        symbolic = tuple(None if rank == 0 else (cell, 0) for cell, rank in enumerate(binding[:16]))
        trace = _Trace(self.rule, binding, self.work)
        rewards = []
        for step, (action, cell) in enumerate(zip(actions, cells)):
            symbolic, reward, changed = trace.swipe(symbolic, action)
            if not changed:
                raise ValueError(f'fragment action {step} is illegal')
            if step == 0 and trace.won(symbolic):
                raise ValueError('fragment first action reaches the goal before its second action')
            if symbolic[cell] is not None:
                raise ValueError(f'fragment spawn {step} has no vacancy')
            spawned = list(symbolic); spawned[cell] = (16+step, 0); symbolic = tuple(spawned)
            rewards.append(reward)
            self.work['compile_symbolic_spawn_assignments'] += 1
        footprint = (('guard_predicates', len(trace.guards)), ('exit_cell_assignments', 16),
            ('reward_terms', sum(map(len, rewards))), ('exit_status_calls', 1), ('duration_constants', 1))
        return Fragment(zero_mask, actions, cells, tuple(trace.guards), symbolic, tuple(rewards),
            binding, footprint)

    def observe(self, root, actions, spawns, expected_exit, expected_scores, status):
        self.work['observations'] += 1
        expected = _expected(expected_exit, expected_scores, status)
        existing = self.lookup(root, actions, spawns)
        if existing is not None:
            if existing != expected:
                raise ValueError('guarded fragment disagrees with the observed outcome')
            self.work['observation_hits'] += 1
            return existing
        inputs = _inputs(root, actions, spawns, self.rule, self.work)
        if inputs is None:
            self.work['compile_applicability_rejections'] += 1
            raise ValueError('fragment root or spawn is outside its applicability domain')
        key, binding = inputs
        try:
            fragment = self._compile(key, binding)
        except ValueError:
            self.work['compile_applicability_rejections'] += 1
            raise
        outcome = self._bind(fragment, binding)
        if outcome != expected:
            raise ValueError('compiled fragment disagrees with the observed outcome')
        bank = self.buckets.setdefault(key, [])
        self.work['guard_refinements'] += int(bool(bank))
        bank.append(fragment)
        self.work.update(compiled_programs=1, stored_anchor_rank_copies=18,
            stored_exit_expression_slots=16, stored_reward_expressions=sum(map(len, fragment.reward_expressions_by_step)))
        return outcome

    def summary(self):
        fragments = [fragment for bank in self.buckets.values() for fragment in bank]
        return dict(num_programs=len(fragments), num_buckets=len(self.buckets),
            total_guards=sum(len(f.guards) for f in fragments),
            total_exit_expressions=sum(sum(x is not None for x in f.exit_expressions) for f in fragments),
            total_exit_cell_slots=16*len(fragments),
            total_reward_expressions=sum(sum(map(len, f.reward_expressions_by_step)) for f in fragments),
            total_instructions=sum(sum(n for _, n in f.instruction_footprint) for f in fragments),
            total_anchor_rank_copies=18*len(fragments))

    def to_dict(self):
        fragments = [asdict(fragment) for bank in self.buckets.values() for fragment in bank]
        self.work['serialized_programs'] += len(fragments)
        return dict(schema=SCHEMA, kind='guarded', fragments=fragments)

    @classmethod
    def from_dict(cls, payload, rule):
        if payload['schema'] != SCHEMA or payload['kind'] != 'guarded':
            raise ValueError('not a V138 guarded fragment cache')
        result = cls(rule)
        pair = lambda expression: None if expression is None else tuple(expression)
        for data in payload['fragments']:
            guards = tuple((kind, tuple(left), tuple(right) if kind == 'EQ' else right, expected)
                for kind, left, right, expected in data['guards'])
            fragment = Fragment(data['zero_mask'], tuple(data['actions']), tuple(data['spawn_cells']),
                guards, tuple(pair(x) for x in data['exit_expressions']),
                tuple(tuple(pair(x) for x in terms) for terms in data['reward_expressions_by_step']),
                tuple(data['anchor_binding']), tuple(tuple(x) for x in data['instruction_footprint']))
            key = fragment.actions, fragment.spawn_cells, fragment.zero_mask
            result.buckets.setdefault(key, []).append(fragment)
        # The snapshot contains persistent programs, not the prefix's work counters.
        result.work['copied_programs'] = sum(map(len, result.buckets.values()))
        return result


class ExactConcreteFragmentCache:
    def __init__(self, rule):
        _validate_rule(rule)
        self.rule, self.entries, self.work = rule, {}, Counter()

    def lookup(self, root, actions, spawns):
        self.work['lookup_calls'] += 1
        inputs = _inputs(root, actions, spawns, self.rule, self.work)
        if inputs is None:
            self.work.update(applicability_rejections=1, misses=1)
            return None
        shape, binding = inputs
        key = shape[0], shape[1], binding
        outcome = self.entries.get(key)
        if outcome is None:
            self.work['misses'] += 1
            return None
        self.work.update(hits=1, copied_exit_cells=16, copied_score_values=2)
        return _expected(outcome['exit_board'], outcome['scores'], outcome['status'])

    def observe(self, root, actions, spawns, expected_exit, expected_scores, status):
        self.work['observations'] += 1
        expected = _expected(expected_exit, expected_scores, status)
        existing = self.lookup(root, actions, spawns)
        if existing is not None:
            if existing != expected:
                raise ValueError('concrete fragment disagrees with the observed outcome')
            self.work['observation_hits'] += 1
            return existing
        inputs = _inputs(root, actions, spawns, self.rule, self.work)
        if inputs is None:
            raise ValueError('fragment root or spawn is outside its applicability domain')
        shape, binding = inputs
        self.entries[(shape[0], shape[1], binding)] = expected
        self.work.update(stored_programs=1, stored_input_rank_copies=18,
            stored_exit_rank_copies=16, stored_score_copies=2)
        return _expected(expected_exit, expected_scores, status)

    def summary(self):
        n = len(self.entries)
        return dict(num_programs=n, num_buckets=n, total_guards=0, total_exit_expressions=0,
            total_exit_cell_slots=16*n, total_reward_expressions=0, total_instructions=0,
            total_anchor_rank_copies=18*n, total_stored_output_values=18*n)

    def to_dict(self):
        entries = [dict(actions=list(actions), spawn_cells=list(cells), binding=list(binding),
            outcome=_expected(outcome['exit_board'], outcome['scores'], outcome['status']))
            for (actions, cells, binding), outcome in self.entries.items()]
        self.work['serialized_programs'] += len(entries)
        return dict(schema=SCHEMA, kind='concrete', entries=entries)

    @classmethod
    def from_dict(cls, payload, rule):
        if payload['schema'] != SCHEMA or payload['kind'] != 'concrete':
            raise ValueError('not a V138 concrete fragment cache')
        result = cls(rule)
        for entry in payload['entries']:
            key = tuple(entry['actions']), tuple(entry['spawn_cells']), tuple(entry['binding'])
            outcome = entry['outcome']
            result.entries[key] = _expected(outcome['exit_board'], outcome['scores'], outcome['status'])
        result.work['copied_programs'] = len(result.entries)
        return result
