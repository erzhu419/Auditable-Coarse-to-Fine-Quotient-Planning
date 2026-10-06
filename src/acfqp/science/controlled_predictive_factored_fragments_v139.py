"""Compose observed guarded line programs into conditional two-action exits."""
from collections import Counter
from dataclasses import asdict, dataclass

from .controlled_predictive_guarded_fragments_v138 import _expected, _validate_rule
from .controlled_predictive_parametric_contract_v75 import ACTION_CELLS, ACTION_ORDER, _Trace, _value

SCHEMA = 'acfqp.factored_fragments.v139'
COMPOSITION_FOOTPRINT = (('action_passes', 2), ('oriented_line_gathers', 8),
    ('line_program_lookups', 8), ('line_scatter_writes', 8), ('legal_action_checks', 2),
    ('first_goal_checks', 1), ('dynamic_spawn_patches', 2), ('exit_status_calls', 1),
    ('duration_constants', 1))


@dataclass(frozen=True)
class LocalProgram:
    program_id: int
    zero_mask: int
    guards: tuple
    output_expressions: tuple
    reward_expressions: tuple
    anchor_binding: tuple


class FactoredFragmentCache:
    def __init__(self, rule):
        _validate_rule(rule)
        self.rule, self.buckets, self.programs, self.last_components = rule, {}, [], []
        self.work = Counter(composition_descriptions=1,
            composition_description_instructions=sum(n for _, n in COMPOSITION_FOOTPRINT))

    def _inputs(self, root, actions, spawns):
        board, actions = tuple(root), tuple(actions)
        if len(board) != 16 or len(actions) != 2 or len(spawns) != 2:
            raise ValueError('a fragment requires sixteen cells, two actions and two spawns')
        if any(action not in ACTION_ORDER for action in actions):
            raise ValueError('unknown fragment action')
        cells, ranks = tuple(s['cell'] for s in spawns), tuple(s['rank'] for s in spawns)
        self.work.update(input_rank_reads=18, input_cell_reads=2)
        if (any(rank < 0 for rank in board) or not any(board) or max(board) >= self.rule.goal_rank
                or any(rank not in (1, 2) for rank in ranks) or any(not 0 <= cell < 16 for cell in cells)):
            return None
        return board, actions, tuple(zip(cells, ranks))

    def _matches(self, program, line):
        self.work['line_guard_trials'] += 1
        for kind, left, right, expected in program.guards:
            self.work.update(line_guard_checks=1, line_guard_rank_reads=2)
            if (_value(left, line) == _value(right, line)) != expected:
                self.work['line_guard_rejections'] += 1
                return False
        return True

    def _bind(self, program, line):
        output = []
        for expression in program.output_expressions:
            output.append(0 if expression is None else _value(expression, line))
            self.work['line_bound_output_cells'] += 1
            if expression is not None:
                self.work['line_bound_rank_reads'] += 1
        score = 0
        for expression in program.reward_expressions:
            score += 1 << _value(expression, line)
            self.work.update(line_bound_reward_terms=1, line_bound_reward_additions=1,
                line_bound_reward_rank_reads=1)
        self.work['line_bind_calls'] += 1
        return tuple(output), score

    def _lookup_line(self, line, track=False):
        self.work.update(line_lookup_calls=1, line_zero_mask_rank_reads=4)
        zero_mask = sum(1 << position for position, rank in enumerate(line) if rank == 0)
        for program in self.buckets.get(zero_mask, ()):
            if self._matches(program, line):
                self.work['line_hits'] += 1
                self.work['new_numeric_line_hits'] += int(tuple(line) != program.anchor_binding)
                if track:
                    self.last_components.append(program.program_id)
                return self._bind(program, line)
        self.work['line_misses'] += 1
        return None

    def _compile_line(self, line):
        self.work['compile_local_line_rewrites'] += 1
        zero_mask = sum(1 << position for position, rank in enumerate(line) if rank == 0)
        trace = _Trace(self.rule, line, self.work)
        packed = tuple((position, 0) for position, rank in enumerate(line) if rank)
        result, rewards, index = [], [], 0
        while index < len(packed):
            expression = packed[index]
            if index+1 < len(packed) and trace.equal(expression, packed[index+1]):
                expression = expression[0], expression[1]+1
                rewards.append(expression); index += 2
            else:
                index += 1
            result.append(expression)
        result.extend([None]*(4-len(result)))
        return LocalProgram(len(self.programs), zero_mask, tuple(trace.guards), tuple(result), tuple(rewards), tuple(line))

    def _observe_line(self, line, expected_output):
        self.work['line_observations'] += 1
        existing = self._lookup_line(line)
        if existing is not None:
            if existing[0] != expected_output:
                raise ValueError('observed line disagrees with its guarded program')
            return existing
        program = self._compile_line(line)
        result = self._bind(program, line)
        if result[0] != expected_output:
            raise ValueError('compiled line disagrees with the frozen rewrite primitive')
        bank = self.buckets.setdefault(program.zero_mask, [])
        self.work['guard_refinements'] += int(bool(bank))
        bank.append(program)
        self.programs.append(program)
        self.work.update(compiled_programs=1, stored_anchor_rank_copies=4,
            stored_output_expression_slots=4, stored_reward_expressions=len(program.reward_expressions))
        return result

    def _reject(self):
        self.work.update(applicability_rejections=1, misses=1)
        return None

    def lookup(self, root, actions, spawns):
        self.last_components = []
        self.work['lookup_calls'] += 1
        inputs = self._inputs(root, actions, spawns)
        if inputs is None:
            return self._reject()
        board, actions, descriptors = inputs
        scores = []
        for step, (action, (cell, rank)) in enumerate(zip(actions, descriptors)):
            after, score = [0]*16, 0
            for cells in ACTION_CELLS[action]:
                line = tuple(board[position] for position in cells)
                self.work.update(composition_line_gathers=1, composition_gather_rank_reads=4)
                result = self._lookup_line(line, track=True)
                if result is None:
                    self.work.update(component_misses=1, misses=1)
                    return None
                output, gained = result
                for position, value in zip(cells, output):
                    after[position] = value
                score += gained
                self.work.update(composition_line_scatters=1, composition_board_writes=4,
                    composition_score_additions=1)
            self.work.update(composition_action_passes=1, composition_legal_action_checks=1)
            if tuple(after) == board:
                return self._reject()
            if step == 0:
                self.work.update(composition_first_goal_checks=1, composition_goal_rank_reads=16)
                if max(after) >= self.rule.goal_rank:
                    return self._reject()
            self.work['composition_spawn_vacancy_checks'] += 1
            if after[cell] != 0:
                return self._reject()
            after[cell] = rank
            self.work.update(composition_spawn_patches=1, composition_board_writes=1)
            board = tuple(after); scores.append(score)
        status_work = Counter()
        status, _ = self.rule.classify(board, status_work)
        self.work.update({f'exit_status_{name}': count for name, count in status_work.items()})
        self.work.update(hits=1, composition_cumulative_score_additions=1)
        return _expected(board, scores, status)

    def _validate_observation(self, root, actions, spawns, expected):
        inputs = self._inputs(root, actions, spawns)
        if inputs is None:
            raise ValueError('fragment root or spawn is outside its applicability domain')
        board, actions, descriptors = inputs
        steps, scores, work = [], [], Counter()
        try:
            for step, (action, (cell, rank)) in enumerate(zip(actions, descriptors)):
                after, score, changed = self.rule.swipe(board, action, work)
                if not changed:
                    raise ValueError(f'fragment action {step} is illegal')
                if step == 0 and max(after) >= self.rule.goal_rank:
                    raise ValueError('fragment first action reaches the goal before its second action')
                if after[cell] != 0:
                    raise ValueError(f'fragment spawn {step} has no vacancy')
                steps.append((board, action, after, score)); scores.append(score)
                spawned = list(after); spawned[cell] = rank; board = tuple(spawned)
                work['recorded_spawn_patches'] += 1
            status, _ = self.rule.classify(board, work)
            if _expected(board, scores, status) != expected:
                raise ValueError('fragment observation disagrees with the frozen rewrite primitive')
        finally:
            self.work.update({f'observation_validation_{name}': count for name, count in work.items()})
        return steps

    def observe(self, root, actions, spawns, expected_exit, expected_scores, status):
        self.work['observations'] += 1
        expected = _expected(expected_exit, expected_scores, status)
        # Validate the complete supplied trace before it can add any local program.
        steps = self._validate_observation(root, actions, spawns, expected)
        for board, action, after, score in steps:
            gained = 0
            for cells in ACTION_CELLS[action]:
                line = tuple(board[position] for position in cells)
                expected_output = tuple(after[position] for position in cells)
                self.work.update(observation_line_gathers=1, observation_gather_rank_reads=8)
                _, reward = self._observe_line(line, expected_output)
                gained += reward
                self.work['observation_score_additions'] += 1
            if gained != score:
                raise ValueError('local reward expressions disagree with the observed action score')
        return _expected(expected_exit, expected_scores, status)

    def summary(self):
        programs = self.programs
        local_instructions = sum(len(p.guards)+4+len(p.reward_expressions) for p in programs)
        shared_instructions = sum(n for _, n in COMPOSITION_FOOTPRINT)
        return dict(num_programs=len(programs), num_buckets=len(self.buckets),
            total_guards=sum(len(p.guards) for p in programs),
            total_exit_expressions=sum(sum(x is not None for x in p.output_expressions) for p in programs),
            total_exit_cell_slots=4*len(programs),
            total_reward_expressions=sum(len(p.reward_expressions) for p in programs),
            total_anchor_rank_copies=4*len(programs), local_program_instructions=local_instructions,
            shared_composition_instructions=shared_instructions,
            total_instructions=local_instructions+shared_instructions)

    def to_dict(self):
        programs = [asdict(program) for program in self.programs]
        self.work['serialized_programs'] += len(programs)
        return dict(schema=SCHEMA, kind='factored', composition_footprint=COMPOSITION_FOOTPRINT,
            programs=programs)

    @classmethod
    def from_dict(cls, payload, rule):
        if payload['schema'] != SCHEMA or payload['kind'] != 'factored':
            raise ValueError('not a V139 factored fragment cache')
        result = cls(rule)
        for data in payload['programs']:
            program = LocalProgram(data['program_id'], data['zero_mask'],
                tuple((kind, tuple(left), tuple(right), expected)
                    for kind, left, right, expected in data['guards']),
                tuple(None if expression is None else tuple(expression) for expression in data['output_expressions']),
                tuple(tuple(expression) for expression in data['reward_expressions']),
                tuple(data['anchor_binding']))
            result.buckets.setdefault(program.zero_mask, []).append(program)
            result.programs.append(program)
        result.work['copied_programs'] = len(payload['programs'])
        result.work['copied_anchor_ranks'] = 4*len(payload['programs'])
        return result
