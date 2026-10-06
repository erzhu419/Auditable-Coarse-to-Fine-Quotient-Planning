"""Frozen FIRST H2 query selection and four-draw, one-step rootgroup supervision."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .native_retained_critic_v287 import _work
from .native_split_risk_v301 import PLANNING_COUNTS, REPRESENTATION_COUNTS
from .native_value_stream_v286 import ENVIRONMENT_COUNTS

QUERY_COUNTS = ('anchors_queried', 'actual_nonwin_leaf_queries', 'pool_board_cells_written',
    'pool_path_fields_written', 'selector_random_draws', 'valid_anchors', 'selected_roots', 'native_pool_bytes_peak')
SUPERVISION_COUNTS = ('rootgroups_supervised', 'replica_targets', 'supervision_start_spawns',
    'direct_choose_calls', 'direct_action_candidates', 'direct_legal_action_candidates',
    'teacher_predictions', 'teacher_reward_table_lookups', 'teacher_win_table_lookups',
    'analytic_win_candidates', 'bootstrap_targets', 'analytic_win_targets', 'terminal_lost_targets',
    'ground_teacher_branch_checks')
LEARNING_COUNTS = ('rootgroup_updates', 'current_predictions', 'table_lookups', 'table_updates',
    'table_update_occurrences', 'reward_predictions', 'win_predictions', 'reward_table_lookups',
    'win_table_lookups', 'reward_table_updates', 'win_parameter_updates')
TARGET_COUNTS = ('rootgroups_targeted', 'reward_replica_reads', 'win_replica_reads',
    'reward_target_mean_additions', 'win_target_mean_additions', 'target_mean_divisions',
    'replica_noise_residuals', 'replica_noise_squares', 'replica_noise_accumulations',
    'replica_noise_divisions', 'replica_noise_square_roots')
NORMALIZATION_COUNTS = ('rootgroups_processed', 'feature_extractions', 'feature_occurrences',
    'feature_digit_reads', 'feature_address_multiply_adds', 'sort_calls', 'sort_items',
    'sort_comparisons', 'denominator_occurrence_visits', 'rootgroup_unique_addresses',
    'reward_gradient_products', 'win_gradient_products', 'normalization_divisions',
    'parameter_update_multiplications', 'rootgroup_parameter_commits', 'reward_rootgroup_commits',
    'win_rootgroup_commits', 'reward_parameter_writes', 'win_parameter_writes', 'native_workspace_bytes')
PROVENANCE_COLUMNS = ('root_action', 'spawn_cell', 'spawn_rank', 'inner_action', 'query_ordinal', 'total_leaf_queries')
_LIBRARIES = {}


def _backend(runtime, counts):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V319 native builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = runtime / f'native_query_supervision_v319_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(output)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(runtime)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=4)
        library = ctypes.CDLL(str(output))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        ci, cd, cu = ctypes.c_int, ctypes.c_double, ctypes.c_uint64
        library.query_roots_v319.argtypes = [ip, ci, cu, ip, ci, dp, dp, ip, lp, ip, cd,
            ip, ip, lp, ip, ip, ip, lp, dp, dp, ip, up, up, up]
        library.query_roots_v319.restype = None
        library.supervise_v319.argtypes = [ip, ci, ci, cu, ip, ci, dp, dp, ip, lp, ip, cd,
            dp, dp, ip, ip, ip, ip, up, up, up, up]
        library.supervise_v319.restype = ci
        library.fit_supervision_v319.argtypes = [ip, ci, dp, dp, ci, ip, ci, dp, dp, cd,
            up, up, up, up, lp, dp, dp]
        library.fit_supervision_v319.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def _frozen_teacher(first):
    if first.kind != 'LOCAL_RISK' or first.reward_weights.flags.writeable or first.risk_weights.flags.writeable:
        raise ValueError('V319 sampling uses both actual frozen FIRST LOCAL tables')


def _boards(boards):
    result = np.ascontiguousarray(boards, dtype=np.int32)
    if result.ndim != 2 or result.shape[1] != 16:
        raise ValueError('V319 roots and anchors are complete 16-cell boards')
    return result


def _teacher_parameters(first):
    return [first.model.patterns, first.radix, first.reward_weights, first.risk_weights,
        first.model.table, first.model.scores, first.model.cells]


def query_roots(first, anchor_postboards, selection_seed, runtime, *, p_model):
    _frozen_teacher(first)
    started, cpu = perf_counter(), process_time()
    anchors = _boards(anchor_postboards); n = len(anchors)
    roots, chosen_after = np.zeros((n, 16), dtype=np.int32), np.empty((n, 16), dtype=np.int32)
    valid, chosen_actions = np.zeros(n, dtype=np.int32), np.empty(n, dtype=np.int32)
    provenance = np.full((n, 6), -1, dtype=np.int64)
    moved, scores = np.empty((n, 4, 16), dtype=np.int32), np.zeros((n, 4), dtype=np.int64)
    tails, values, legal = np.zeros((n, 4)), np.zeros((n, 4)), np.zeros((n, 4), dtype=np.int32)
    planning, representation, selection = (np.zeros(len(names), dtype=np.uint64)
        for names in (PLANNING_COUNTS, REPRESENTATION_COUNTS, QUERY_COUNTS))
    setup = Counter(); library = _backend(runtime, setup)
    library.query_roots_v319(anchors, n, int(selection_seed), *_teacher_parameters(first), float(p_model),
        roots, valid, provenance, chosen_actions, chosen_after, moved, scores, tails, values, legal,
        planning, representation, selection)
    work = _work(PLANNING_COUNTS, planning); work['choose_calls'] = n

    def probe(index):
        action = int(chosen_actions[index])
        action_values = {name:dict(afterstate=moved[index, j].tolist(), score=int(scores[index, j]),
            tail_value=float(tails[index, j]), value=float(values[index, j])) for j,name in enumerate(ACTIONS) if legal[index, j]}
        return dict(anchor_index=index, preboard=anchors[index].tolist(),
            chosen_action=None if action < 0 else ACTIONS[action], chosen_afterstate=chosen_after[index].tolist(),
            chosen_h2_value=(4. if action == -2 else -4.) if action < 0 else float(values[index, action]),
            action_values=action_values, status=('WON' if action == -2 else 'LOST') if action < 0 else 'ACTIVE')

    return dict(root_afterstates=roots, validmask=valid, provenance=provenance,
        provenance_columns=list(PROVENANCE_COLUMNS), chosen_afterstates=chosen_after, chosen_actions=chosen_actions,
        selection_seed=int(selection_seed), p_model=float(p_model), teacher_updates=first.updates,
        selection_rule='ONE_UNIFORM_POOL_INDEX_DRAW_PER_ANCHOR_ACTUAL_H2_CALL_MULTIPLICITY',
        counts=_work(QUERY_COUNTS, selection), planning_counts=work,
        representation_counts=_work(REPRESENTATION_COUNTS, representation),
        first_probes=[probe(index) for index in range(min(8, n))],
        last_probes=[probe(index) for index in range(max(0, n-8), n)], setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def supervise(first, root_afterstates, p_true, draw_seed, runtime, repeats=4):
    _frozen_teacher(first)
    started, cpu = perf_counter(), process_time()
    roots = _boards(root_afterstates); n = len(roots); repeats = int(repeats)
    if np.any(np.max(roots, axis=1) >= first.radix):
        raise ValueError('V319 paid supervision uses nonwinning afterstate roots')
    shape = (n, repeats)
    reward, win = np.empty(shape), np.empty(shape)
    actions, kinds, cells, ranks = (np.empty(shape, dtype=np.int32) for _ in range(4))
    environment, planning, representation, supervision = (np.zeros(len(names), dtype=np.uint64)
        for names in (ENVIRONMENT_COUNTS, PLANNING_COUNTS, REPRESENTATION_COUNTS, SUPERVISION_COUNTS))
    setup = Counter(); library = _backend(runtime, setup)
    code = library.supervise_v319(roots, n, repeats, int(draw_seed), *_teacher_parameters(first), float(p_true),
        reward, win, actions, kinds, cells, ranks, environment, planning, representation, supervision)
    if code:
        raise ValueError('V319 teacher branch differs from the actual standard-world swipe')
    work = _work(PLANNING_COUNTS, planning); work['choose_calls'] = int(supervision[3])
    return dict(targetreward=reward, targetwin=win, selected_action=actions, targetkind=kinds,
        spawn_cells=cells, spawn_ranks=ranks, draw_seed=int(draw_seed), p_true=float(p_true),
        repeats=repeats, teacher_updates=first.updates,
        target_rule='GROUND_POSTSPAWN_SINGLE_COMBINED_FIRST_DIRECT_BRANCH',
        counts=_work(SUPERVISION_COUNTS, supervision), environment_counts=_work(ENVIRONMENT_COUNTS, environment),
        planning_counts=work, representation_counts=_work(REPRESENTATION_COUNTS, representation),
        setup_counts=dict(setup), seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def fit_supervision(leaf, root_afterstates, targetreward, targetwin, runtime, alpha=.0025):
    if leaf.kind != 'LOCAL_RISK' or not leaf.reward_weights.flags.writeable or not leaf.risk_weights.flags.writeable:
        raise ValueError('V319 fitting writes only both private LOCAL learner tables')
    started, cpu = perf_counter(), process_time()
    roots = _boards(root_afterstates); n = len(roots)
    reward_targets, win_targets = np.ascontiguousarray(targetreward, dtype=np.float64), np.ascontiguousarray(targetwin, dtype=np.float64)
    if reward_targets.ndim != 2 or reward_targets.shape != win_targets.shape or reward_targets.shape[0] != n:
        raise ValueError('V319 target replicas must match each rootgroup')
    if np.any(np.max(roots, axis=1) >= leaf.radix):
        raise ValueError('V319 fitted rootgroups are all nonwinning afterstates')
    repeats = reward_targets.shape[1]
    learning, targets, normalization, representation = (np.zeros(len(names), dtype=np.uint64)
        for names in (LEARNING_COUNTS, TARGET_COUNTS, NORMALIZATION_COUNTS, REPRESENTATION_COUNTS))
    examples, values, noise = np.empty(2, dtype=np.int64), np.empty((2, 7)), np.empty(2)
    setup = Counter(); library = _backend(runtime, setup)
    library.fit_supervision_v319(roots, n, reward_targets, win_targets, repeats, leaf.model.patterns,
        leaf.radix, leaf.reward_weights, leaf.risk_weights, float(alpha), learning, targets,
        normalization, representation, examples, values, noise)
    work = _work(LEARNING_COUNTS, learning)
    leaf.updates += work.get('rootgroup_updates', 0); leaf.counts.update(work)

    def sample(index):
        if not n:
            return None
        rt, pt, rp, pp, utility, re, pe = map(float, values[index])
        return dict(rootgroup=int(examples[index]), reward_target=rt, risk_target=pt,
            reward_prediction=rp, risk_probability=pp, combined_prediction=utility, reward_error=re, risk_error=pe)

    return dict(method='GROUPED_LOCAL', alpha=float(alpha), fitted_rootgroups=n, replicates=repeats,
        trained_afterstates=work.get('rootgroup_updates', 0), frozen_rootgroup_predictions=True,
        sampling_unit='ROOTGROUP_MEAN_OF_PROVIDED_REPLICAS',
        learning_counts=work, target_counts=_work(TARGET_COUNTS, targets),
        normalization_counts=_work(NORMALIZATION_COUNTS, normalization), representation_counts=_work(REPRESENTATION_COUNTS, representation),
        replicate_noise=dict(reward_replica_rms=float(noise[0]), win_replica_rms=float(noise[1]),
            definition='SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'),
        first_sample=sample(0), last_sample=sample(1), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
