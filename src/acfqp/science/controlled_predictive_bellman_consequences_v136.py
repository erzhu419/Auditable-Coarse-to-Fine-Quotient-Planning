"""Joint reward/probability TD under one fixed, frozen H2 teacher policy."""
from collections import Counter
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter

import numpy as np

from . import controlled_predictive_online_query_td_v131 as single
from .controlled_predictive_ntuple_td_v120 import ACTIONS, ALPHA, PATTERNS
from .controlled_predictive_paired_ntuple_v130 import _delta

SCHEMA = 'acfqp.bellman_consequences.v136'
PRIOR_SUCCESS = .5
COUNT_NAMES = ('learned_swipe_calls', 'line_table_lookups', 'legal_swipes',
    'learned_terminal_checks', 'joint_predictions', 'reward_predictions', 'success_predictions',
    'table_lookups', 'terminal_goal_bypasses', 'context_cell_reads', 'context_bank_selections',
    'context_bank_offset_additions', 'reward_table_update_occurrences', 'success_table_update_occurrences',
    'reward_table_updates', 'success_table_updates', 'update_feature_squared_norm', 'sigmoid_evaluations',
    'bank_0_prediction_occurrences', 'bank_1_prediction_occurrences',
    'bank_0_update_occurrences', 'bank_1_update_occurrences',
    'root_swipe_calls', 'root_legal_actions', 'root_goal_actions', 'leaf_choose_calls',
    'second_ply_swipe_calls', 'generated_spawn_outcomes', 'spawn_rank1_outcomes',
    'spawn_rank2_outcomes', 'leaf_terminal_loss_states', 'expectimax_probability_products',
    'expectimax_probability_sums', 'feature_address_occurrences', 'probability_closure_clips')
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V136 build_dir must be inside the research worktree')
    key = (str(build_dir), os.getpid())
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = build_dir/f'bellman_consequences_v136_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts['cpp_compilations'] += 1
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cl, cd = ctypes.c_int, ctypes.c_int64, ctypes.c_double
        prefix = [ip, ip, ip, ci, ci, cl, dp]
        library.bellman_value_v136.argtypes = prefix+[cd, dp, up]
        library.bellman_value_v136.restype = None
        library.bellman_update_v136.argtypes = prefix+[cd, cd, cd, cd, dp, up]
        library.bellman_update_v136.restype = None
        library.bellman_choose_v136.argtypes = prefix+[ip, lp, ip]+[cd]*9+[ci, ip, lp, dp, dp, dp, dp, ip, up]
        library.bellman_choose_v136.restype = ci
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


class PolicyComponents:
    def _configure(self, teacher_leaf, build_dir):
        started = perf_counter()
        if teacher_leaf.weights.flags.writeable:
            raise ValueError('the scalar teacher leaf must be frozen')
        self.teacher_leaf = teacher_leaf
        self.teacher_query = dict(teacher_leaf.target_query)
        self.target_query = self.teacher_query
        self.rule, self.radix = teacher_leaf.rule, teacher_leaf.radix
        self.representation = getattr(teacher_leaf, 'representation', 'SINGLE')
        if self.representation not in ('SINGLE', 'CAPACITY'):
            raise ValueError('V136 compares SINGLE and CAPACITY representations')
        self.mode = -1 if self.representation == 'SINGLE' else 1
        self.teacher_failure = float(self.teacher_query['failure_penalty'])
        self.teacher_coefficient = self.teacher_failure+float(self.teacher_query['goal_bonus'])
        self.failure_shift, self.success_shift = teacher_leaf.failure_shift, teacher_leaf.success_shift
        self.reward_intercept = teacher_leaf.offset+(self.teacher_failure-PRIOR_SUCCESS*self.teacher_coefficient)
        self.prior_success = PRIOR_SUCCESS
        self.counts, self.setup_counts, self.updates = Counter(), Counter(), 0
        self.library = _backend(build_dir, self.setup_counts)
        native = teacher_leaf.model
        self.patterns, self.table, self.scores, self.cells = native.patterns, native.table, native.scores, native.cells
        self.extra_cells = getattr(native, 'extra_cells', np.zeros((4, 8), dtype=np.int32))
        self.head_size = teacher_leaf.weights.size
        self.weights = np.zeros((2, *teacher_leaf.weights.shape), dtype=np.float64)
        self.setup_counts.update(allocated_weight_parameters=self.weights.size,
            allocated_weight_bytes=self.weights.nbytes)
        distribution = dict(self.rule.spawn_distribution)
        if self.rule.spawn_location != 'uniform' or set(distribution) != {1, 2}:
            raise ValueError('V136 requires the frozen uniform-cell rank-one/rank-two spawn law')
        self.spawn_probabilities = tuple(float(distribution[rank]) for rank in (1, 2))
        self.setup_seconds = perf_counter()-started

    def __init__(self, teacher_leaf, build_dir):
        started = perf_counter()
        self._configure(teacher_leaf, build_dir)
        np.copyto(self.weights[0], teacher_leaf.weights)
        self.setup_counts.update(source_parameters_copied=self.head_size,
            source_weight_bytes_copied=teacher_leaf.weights.nbytes)
        self.setup_seconds = perf_counter()-started

    def _board(self, board, terminal_allowed=True):
        return self.teacher_leaf.model._board(board, terminal_allowed=terminal_allowed)

    def _charge(self, counts):
        self.counts.update({key: int(value) for key, value in zip(COUNT_NAMES, counts) if value})

    def feature_indices(self, afterstate):
        return self.teacher_leaf.model.feature_indices(afterstate)

    def value(self, afterstate):
        board = self._board(afterstate)
        self.counts.update(value_calls=1, learned_terminal_checks=1)
        if int(board.max()) >= self.radix:
            self.counts['terminal_goal_bypasses'] += 1
            return dict(raw_reward=0., reward=0., logit=None, success=1., failure=0.)
        output = np.empty(4, dtype=np.float64)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        self.library.bellman_value_v136(board, self.patterns, self.extra_cells, self.radix,
            self.mode, self.head_size, self.weights, self.reward_intercept, output, counts)
        self._charge(counts)
        return dict(raw_reward=float(output[0]), reward=float(output[1]), logit=float(output[2]),
            success=float(output[3]), failure=1.-float(output[3]))

    def update(self, afterstate, target_reward, target_success):
        if not self.weights.flags.writeable:
            raise RuntimeError('frozen components cannot be updated')
        if not 0. <= target_success <= 1.:
            raise ValueError('the shared success target must be a probability')
        board = self._board(afterstate, terminal_allowed=False)
        before = self.counts.copy()
        output = np.empty(7, dtype=np.float64)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        self.library.bellman_update_v136(board, self.patterns, self.extra_cells, self.radix,
            self.mode, self.head_size, self.weights, self.reward_intercept,
            float(target_reward), float(target_success), ALPHA, output, counts)
        self._charge(counts)
        self.updates += 1
        self.counts.update(td_updates=1, reward_td_updates=1, success_td_updates=1)
        return dict(pre_raw_reward=float(output[0]), pre_reward=float(output[1]),
            pre_logit=float(output[2]), pre_success=float(output[3]), target_reward=float(target_reward),
            target_success=float(target_success), raw_reward_target=float(output[4]),
            reward_error=float(output[5]), success_error=float(output[6]), work=_delta(self.counts, before))

    def choose(self, board, query, depth=2):
        # H2 bounds only the returned success average against summation roundoff;
        # the independently accumulated action values and rankings are unchanged.
        if depth not in (1, 2) or query.get('reward_weight', 1.) != 1.:
            raise ValueError('V136 readouts use depth 1 or 2 and reward weight one')
        before = self.counts.copy()
        self.counts['choose_calls'] += 1
        board = self._board(board)
        moved = np.empty((4, 16), dtype=np.int32)
        scores = np.zeros(4, dtype=np.int64)
        values, tails, rewards, successes = (np.zeros(4) for _ in range(4))
        legal = np.zeros(4, dtype=np.int32)
        counts = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
        failure, goal = (float(query.get(key, 0.)) for key in ('failure_penalty', 'goal_bonus'))
        best = self.library.bellman_choose_v136(board, self.patterns, self.extra_cells,
            self.radix, self.mode, self.head_size, self.weights, self.table, self.scores, self.cells,
            self.reward_intercept, self.failure_shift, self.success_shift, self.teacher_failure,
            self.teacher_coefficient, failure, goal, *self.spawn_probabilities, depth,
            moved, scores, values, tails, rewards, successes, legal, counts)
        self._charge(counts)
        if best < 0:
            won = best == -2
            value, success = (goal, 1.) if won else (-failure, 0.)
            return dict(action=None, afterstate=board.tolist(), score=0, value=value, tail_value=value,
                consequences=[0., 1.-success, success], action_values={}, status='WON' if won else 'LOST',
                counts=_delta(self.counts, before))
        action_values = {action: dict(afterstate=moved[index].tolist(), score=int(scores[index]),
            value=float(values[index]), tail_value=float(tails[index]),
            consequences=[float(rewards[index]), 1.-float(successes[index]), float(successes[index])])
            for index, action in enumerate(ACTIONS) if legal[index]}
        return dict(action=ACTIONS[best], **action_values[ACTIONS[best]], action_values=action_values,
            status='ACTIVE', counts=_delta(self.counts, before))

    def freeze(self):
        self.weights.flags.writeable = False

    def save(self, path):
        started, before = perf_counter(), self.counts.copy()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        flat = self.weights.reshape(-1)
        indices = np.flatnonzero(flat)
        self.counts.update(checkpoint_saves=1, checkpoint_scanned_parameters=flat.size,
            checkpoint_saved_parameters=len(indices))
        metadata = dict(schema=SCHEMA, radix=self.radix, representation=self.representation,
            patterns=PATTERNS, shape=self.weights.shape, parameter_count=self.weights.size,
            teacher_query=self.teacher_query,
            teacher_updates=self.teacher_leaf.updates, prior_success=self.prior_success,
            reward_intercept=self.reward_intercept, failure_shift=self.failure_shift,
            success_shift=self.success_shift, alpha=ALPHA, updates=self.updates,
            counts=dict(self.counts), setup_counts=dict(self.setup_counts),
            setup_seconds=self.setup_seconds, frozen=not self.weights.flags.writeable)
        with path.open('wb') as stream:
            np.savez_compressed(stream, indices=indices, values=flat[indices],
                metadata=json.dumps(metadata, sort_keys=True))
        sidecar = path.with_suffix(path.suffix+'.components.json')
        sidecar.write_text(json.dumps(metadata, sort_keys=True, indent=2)+'\n')
        return dict(path=str(path), sidecar=str(sidecar), parameter_count=self.weights.size,
            nonzero_weights=len(indices), updates=self.updates, bytes=path.stat().st_size,
            sidecar_bytes=sidecar.stat().st_size, seconds=perf_counter()-started,
            work=_delta(self.counts, before))

    @classmethod
    def load(cls, path, teacher_leaf, build_dir):
        started = perf_counter()
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data['metadata']))
            result = cls.__new__(cls)
            result._configure(teacher_leaf, build_dir)
            if (metadata['schema'] != SCHEMA or metadata['radix'] != result.radix
                    or metadata['representation'] != result.representation
                    or metadata['teacher_query'] != result.teacher_query
                    or metadata['teacher_updates'] != teacher_leaf.updates
                    or metadata['shape'] != list(result.weights.shape)
                    or metadata['reward_intercept'] != result.reward_intercept):
                raise ValueError('checkpoint differs from its frozen teacher and component representation')
            result.weights.reshape(-1)[data['indices']] = data['values']
            result.updates = int(metadata['updates'])
            result.load_counts = dict(checkpoint_loads=1, checkpoint_loaded_parameters=len(data['indices']))
            result.counts.update(result.load_counts)
        result.loaded_metadata, result.last_load_seconds = metadata, perf_counter()-started
        if metadata['frozen']:
            result.freeze()
        return result


class TeacherTDStream(single.TDStream):
    """Teacher action, both pre-update next heads, then one joint pending fit."""
    def __init__(self, components, teacher_H2, seed_fn, max_steps=2000, p_four=.1):
        super().__init__(components, seed_fn, max_steps, p_four)
        self.teacher = teacher_H2
        self.teacher_counts = Counter()

    def advance(self, n_transitions):
        if not isinstance(n_transitions, int) or n_transitions < 0:
            raise ValueError('advance requires a nonnegative integer transition budget')
        rows, remaining = [], n_transitions
        while remaining:
            started = perf_counter()
            env_before, model_before = self.environment_counts.copy(), self.model.counts.copy()
            teacher_before, updates_before = self.teacher.counts.copy(), self.model.updates
            initial_spawns = self._start() if self.status != 'ACTIVE' else None
            start_board, start_step = list(self.board), self.step
            pending_before = None if self.pending is None else list(self.pending)
            actions, scores, cells, ranks, values = [], [], [], [], []
            next_components, joint_updates = [], []
            terminal_update, censored_last_update = None, False
            while remaining and self.status == 'ACTIVE':
                chosen = self.teacher.choose(self.board, self.model.teacher_query)
                prediction = self.model.value(chosen['afterstate'])
                update = None if self.pending is None else self.model.update(self.pending,
                    chosen['score']/2048.+prediction['reward'], prediction['success'])
                next_components.append(prediction); joint_updates.append(update)
                self.pending = (None if max(chosen['afterstate']) >= self.model.radix
                    else tuple(chosen['afterstate']))
                action = single.ground.Swipe2048Action(chosen['action'])
                self.environment_counts.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1)
                afterstate, score, changed = single.ground.swipe_board_v1(self.board, action)
                if not changed:
                    raise ValueError(f'illegal teacher action at episode {self.episode} step {self.step}')
                self.board, cell, rank = single._spawn(afterstate, self.rng, self.environment_counts, self.p_four)
                self.environment_counts['sampled_transitions'] += 1
                self.status = single._status(self.board, self.environment_counts)
                self.transitions += 1; self.step += 1; self.return_score += score; remaining -= 1
                actions.append(action.value); scores.append(score); cells.append(cell); ranks.append(rank)
                values.append(chosen['value'])
                if self.status == 'LOST' and self.pending is not None:
                    terminal_update = self.model.update(self.pending, 0., 0.)
                    terminal_update['afterstate'] = list(self.pending)
                    self.pending = None
                if self.status == 'ACTIVE' and self.step == self.max_steps:
                    self.status, censored_last_update = 'CUTOFF', self.pending is not None
                    self.pending = None
                if self.status != 'ACTIVE':
                    self.episodes_completed += 1
            environment_counts = _delta(self.environment_counts, env_before)
            model_counts, teacher_counts = _delta(self.model.counts, model_before), _delta(self.teacher.counts, teacher_before)
            self.training_counts.update(model_counts); self.teacher_counts.update(teacher_counts)
            row = dict(episode=self.episode, seed=self.seed, start_step=start_step, end_step=self.step,
                start_board=start_board, end_board=list(self.board), actions=actions, scores=scores,
                spawned_cells=cells, spawned_ranks=ranks, chosen_values=values,
                next_components=next_components, joint_updates=joint_updates, terminal_update=terminal_update,
                pending_before=pending_before, pending_after=None if self.pending is None else list(self.pending),
                updates_before=updates_before, updates_after=self.model.updates,
                cumulative_transitions=self.transitions, cumulative_updates=self.model.updates,
                environment_counts=environment_counts, model_counts=model_counts, teacher_counts=teacher_counts,
                status=self.status, budget_status='BUDGET_END' if self.status == 'ACTIVE' else 'EPISODE_END',
                censored_last_update=censored_last_update, return_score=self.return_score,
                seconds=perf_counter()-started)
            if initial_spawns is not None:
                row['initial_spawns'] = initial_spawns
            rows.append(row)
        return rows
