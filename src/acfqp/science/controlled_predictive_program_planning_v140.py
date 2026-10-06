"""Budgeted conditional-program rollouts with an unchanged frozen H1 leaf."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from .controlled_predictive_guarded_fragments_v138 import _validate_rule
from .controlled_predictive_ntuple_td_v120 import ACTIONS, NtupleValue
from .controlled_predictive_paired_ntuple_v130 import _delta, _same_query

SCHEMA = 'acfqp.program_planning.v140'
PROGRAM_WIDTH = 30
COUNT_NAMES = ('learned_swipe_calls', 'line_table_lookups', 'legal_swipes',
    'learned_terminal_checks', 'value_predictions', 'table_lookups', 'terminal_goal_bypasses',
    'root_swipe_calls', 'program_swipe_calls', 'bootstrap_swipe_calls', 'model_swipe_budget',
    'model_swipes_used', 'rollouts_started', 'rollout_actions', 'model_sampled_transitions',
    'simulation_uniform_draws', 'simulation_rng_initializations', 'tree_calls',
    'feature_board_reads', 'feature_neighbor_comparisons', 'feature_predicate_values',
    'tree_predicate_checks', 'tree_order_reads', 'line_lookup_calls', 'line_guard_trials',
    'line_guard_checks', 'line_hits', 'line_misses', 'line_bound_output_cells',
    'line_bound_reward_terms', 'composition_line_gathers', 'composition_line_scatters',
    'line_zero_mask_rank_reads', 'line_guard_rank_reads', 'line_bound_rank_reads',
    'root_legal_actions', 'root_goal_actions', 'leaf_choose_calls', 'leaf_terminal_loss_states',
    'rollout_terminal_loss_states', 'rollout_terminal_goal_states', 'budget_early_bootstraps',
    'direct_choose_calls', 'root_empty_cell_reads', 'spawn_empty_cell_reads',
    'spawn_board_writes', 'rollout_reward_additions', 'rollout_mean_additions',
    'line_program_mask_tests')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V140 build_dir must be inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'program_planning_v140_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=2)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd, cu = ctypes.c_int, ctypes.c_double, ctypes.c_uint64
        library.program_choose_v140.argtypes = [ip, ip, ci, dp, ip, lp, ip, ip, ci, ip,
            cd, cd, cd, cd, cd, cd, ci, ci, ci, cu, ip, lp, dp, dp, ip, ip, up]
        library.program_choose_v140.restype = ci
        library.program_line_v140.argtypes = [ip, ip, ci, ip, lp, up]
        library.program_line_v140.restype = ci
        library.program_order_v140.argtypes = [ip, ci, ip, ip, up]
        library.program_order_v140.restype = None
        library.program_h1_v140.argtypes = [ip, ip, ci, dp, ip, lp, ip,
            cd, cd, cd, cd, cd, ci, up]
        library.program_h1_v140.restype = cd
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def encode_programs(payload):
    if payload.get('schema') != 'acfqp.factored_fragments.v139' or payload.get('kind') != 'factored':
        raise ValueError('V140 requires retained V139 local programs')
    output = np.zeros((len(payload['programs']), PROGRAM_WIDTH), dtype=np.int32)
    for row, program in zip(output, payload['programs']):
        guards, rewards = program['guards'], program['reward_expressions']
        if len(guards) > 3 or len(rewards) > 2 or len(program['output_expressions']) != 4:
            raise ValueError('local program is outside the four-cell once-merge grammar')
        row[:3] = program['zero_mask'], len(guards), len(rewards)
        for index, (kind, left, right, expected) in enumerate(guards):
            if kind != 'EQ':
                raise ValueError('local programs require equality guards')
            row[3+5*index:8+5*index] = *left, *right, int(expected)
        for index, expression in enumerate(program['output_expressions']):
            row[18+2*index:20+2*index] = (-1, 0) if expression is None else expression
        for index, expression in enumerate(rewards):
            row[26+2*index:28+2*index] = expression
    output.flags.writeable = False
    return output


class ProgramPlanner:
    def __init__(self, model, factored_payload, policy_payload, mode='ROLLOUT', build_dir=None):
        started = perf_counter()
        if mode not in ('ROLLOUT', 'DIRECT'):
            raise ValueError('V140 mode must be ROLLOUT or DIRECT')
        if model.weights.flags.writeable:
            raise ValueError('the V140 leaf model must already be frozen')
        if type(model.model) is not NtupleValue:
            raise ValueError('V140 uses the existing SINGLE QueryTD leaf')
        _validate_rule(model.rule)
        if policy_payload.get('schema') != 'acfqp.policy_programs.v140':
            raise ValueError('V140 requires the conditional action-priority tree payload')
        self.model, self.mode, self.rule, self.radix = model, mode, model.rule, model.radix
        self.source_query, self.target_query = model.source_query, model.target_query
        self.counts, self.setup_counts = Counter(), Counter()
        self.programs = encode_programs(factored_payload)
        self.trees = np.array(policy_payload['trees'], dtype=np.int32, order='C')
        if self.trees.shape != (4, 7, 5):
            raise ValueError('V140 uses four depth-two conditional trees')
        self.trees.flags.writeable = False
        self.library = _backend(build_dir, self.setup_counts)
        distribution = dict(model.rule.spawn_distribution)
        self.spawn_probabilities = tuple(float(distribution[rank]) for rank in (1, 2))
        self.convert = int(model.kind == 'PRIOR' and not _same_query(self.source_query, self.target_query))
        raw_query = self.source_query if model.kind == 'PRIOR' else self.target_query
        self.source_goal = float(raw_query.get('goal_bonus', 0.))
        self.goal = float(self.target_query.get('goal_bonus', 0.))
        self.failure = float(self.target_query.get('failure_penalty', 0.))
        self.setup_counts.update(copied_local_programs=len(self.programs),
            copied_program_integer_cells=self.programs.size, copied_tree_integer_cells=self.trees.size,
            copied_program_bytes=self.programs.nbytes, copied_tree_bytes=self.trees.nbytes)
        self.setup_seconds = perf_counter()-started

    @property
    def weights(self):
        return self.model.weights

    @property
    def updates(self):
        return self.model.updates

    def freeze(self):
        self.model.freeze()

    def _charge(self, counts):
        self.counts.update({key: int(value) for key, value in zip(COUNT_NAMES, counts) if value})

    def _line(self, line):
        """Finite verification entry point for the same native line interpreter."""
        line = np.ascontiguousarray(line, dtype=np.int32)
        output, score = np.empty(4, dtype=np.int32), np.empty(1, dtype=np.int64)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        found = self.library.program_line_v140(line, self.programs, len(self.programs), output, score, counts)
        self._charge(counts)
        return None if found < 0 else (tuple(map(int, output)), int(score[0]))

    def _order(self, board, previous_action):
        """Finite verification entry point for the decision tree interpreter."""
        board = self.model.model._board(board, terminal_allowed=True)
        output, counts = np.empty(4, dtype=np.int32), np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        self.library.program_order_v140(board, ACTIONS.index(previous_action), self.trees, output, counts)
        self._charge(counts)
        return tuple(ACTIONS[index] for index in output)

    def _h1(self, board):
        """Finite verification entry point for the unchanged query-converted leaf."""
        native = self.model.model
        board = native._board(board, terminal_allowed=True)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        value = self.library.program_h1_v140(board, native.patterns, self.radix, self.weights,
            native.table, native.scores, native.cells, self.source_goal, self.goal, self.failure,
            self.model.failure_shift, self.model.success_shift, self.convert, counts)
        self._charge(counts)
        return float(value)

    def choose(self, board, query=None, *, simulation_seed=0, previous_action='DOWN'):
        if query is not None and not _same_query(query, self.target_query):
            raise ValueError('the frozen planner target query is fixed')
        native = self.model.model
        board = native._board(board, terminal_allowed=True)
        before = self.counts.copy(); self.counts['choose_calls'] += 1
        moved, scores = np.empty((4, 16), dtype=np.int32), np.zeros(4, dtype=np.int64)
        tails, values, legal = np.zeros(4), np.zeros(4), np.zeros(4, dtype=np.int32)
        stats, counts = np.zeros((4, 3), dtype=np.int32), np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        best = self.library.program_choose_v140(board, native.patterns, self.radix, self.weights,
            native.table, native.scores, native.cells, self.programs, len(self.programs), self.trees,
            self.source_goal, self.goal, self.failure, self.model.failure_shift, self.model.success_shift,
            self.spawn_probabilities[0], self.convert, int(self.mode == 'DIRECT'),
            ACTIONS.index(previous_action), int(simulation_seed), moved, scores, tails, values, legal, stats, counts)
        self._charge(counts)
        if best == -3:
            raise ValueError('V139 local program coverage is incomplete; no transition fallback was used')
        if best == -4:
            raise RuntimeError('V140 rollout exceeded its assigned swipe budget')
        work = _delta(self.counts, before)
        value_kind = 'action_priority' if self.mode == 'DIRECT' else 'estimated_return'
        if best < 0:
            status, value = ('WON', self.goal) if best == -2 else ('LOST', -self.failure)
            return dict(action=None, afterstate=board.tolist(), score=0, value=value,
                tail_value=value, action_values={}, status=status, counts=work, value_kind=value_kind)
        action_values = {action: dict(afterstate=moved[index].tolist(), score=int(scores[index]),
            tail_value=float(tails[index]), value=float(values[index]), budget=int(stats[index, 0]),
            used=int(stats[index, 1]), rollouts=int(stats[index, 2]))
            for index, action in enumerate(ACTIONS) if legal[index]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
            status='ACTIVE', counts=work, value_kind=value_kind)
