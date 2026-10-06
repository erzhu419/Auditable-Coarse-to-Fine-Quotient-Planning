"""LOCAL sampled-SARSA targets from recorded successors and a batch-start snapshot."""
from collections import Counter
from copy import deepcopy
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .native_retained_critic_v287 import _arrays, _work
from .native_split_risk_v301 import LEARNING_COUNTS, NORMALIZATION_COUNTS, REPRESENTATION_COUNTS

TARGET_COUNTS = ('terminal_game_labels', 'goal_checks', 'skipped_winning_afterstates',
    'sampled_next_reward_reads', 'reward_target_assignments', 'win_target_assignments',
    'bootstrap_successor_targets', 'analytic_next_win_targets', 'terminal_lost_targets',
    'next_afterstate_goal_checks', 'target_kind_reads')
BOOTSTRAP_COUNTS = ('afterstate_predictions', 'reward_table_lookups', 'risk_table_lookups',
    'feature_extractions', 'feature_occurrences', 'feature_digit_reads', 'feature_address_multiply_adds')
TARGET_KINDS = {0:'UNUSED_WINNING_AFTERSTATE', 1:'SAMPLED_SUCCESSOR_BOOTSTRAP',
    2:'ANALYTIC_NEXT_WIN', 3:'LAST_LOST'}
_LIBRARIES = {}


def _backend(build_dir, counts):
    build_dir = Path(build_dir).resolve()
    if not build_dir.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V314 native builds belong inside the research worktree')
    key = str(build_dir), os.getpid()
    if key not in _LIBRARIES:
        build_dir.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = build_dir / f'native_local_targets_v314_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), str(source.with_name('controlled_predictive_frozen_leaf_planning_v135.cpp')),
            str(source.with_name('controlled_predictive_ntuple_kernel_v120.cpp')),
            str(source.with_name('controlled_predictive_contextual_ntuple_v134.cpp')),
            '-o', str(output)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(build_dir)))
        counts.update(cpp_compilations=1, cpp_translation_units_compiled=4)
        library = ctypes.CDLL(str(output))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        library.fit_local_targets_v314.argtypes = [ip, dp, lp, ip, ctypes.c_int,
            ip, ctypes.c_int, dp, dp, dp, dp, ctypes.c_double, dp, dp, ip,
            up, up, up, up, up, up, lp, dp, dp]
        library.fit_local_targets_v314.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def fit_local_targets(leaf, dataset, bootstrap_snapshot, runtime, target_path,
                      *, bootstrap_version, alpha=.0025):
    if leaf.kind != 'LOCAL_RISK':
        raise ValueError('V314 retains exactly the LOCAL reward/risk representation')
    if not leaf.reward_weights.flags.writeable or not leaf.risk_weights.flags.writeable:
        raise ValueError('Both LOCAL heads must be writable while fitting')
    started, cpu_started = perf_counter(), process_time()
    arrays = _arrays(dataset)
    n_games, fit_end = int(dataset['fit_game_count']), int(dataset['fit_step_end'])
    if (int(arrays[2][n_games-1]) if n_games else 0) != fit_end:
        raise ValueError('V314 targets stay inside the complete-game FIT prefix')
    if np.any((arrays[3][:n_games] != 1) & (arrays[3][:n_games] != -1)):
        raise ValueError('V314 terminal targets require natural WON or LOST games')
    bootstrap_reward, bootstrap_risk = bootstrap_snapshot['reward'], bootstrap_snapshot['terminal']
    if bootstrap_reward.shape != leaf.reward_weights.shape or bootstrap_risk.shape != leaf.risk_weights.shape:
        raise ValueError('Bootstrap snapshot must have the actual LOCAL head shape')
    bootstrap_reward.flags.writeable = bootstrap_risk.flags.writeable = False
    setup = Counter()
    library = _backend(runtime, setup)
    reward, win = np.zeros(fit_end), np.zeros(fit_end)
    kind = np.zeros(fit_end, dtype=np.int32)
    learning, targets = np.zeros(len(LEARNING_COUNTS), dtype=np.uint64), np.zeros(len(TARGET_COUNTS), dtype=np.uint64)
    normalization, representation = np.zeros(len(NORMALIZATION_COUNTS), dtype=np.uint64), np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64)
    bootstrap, bootstrap_representation = np.zeros(len(BOOTSTRAP_COUNTS), dtype=np.uint64), np.zeros(len(REPRESENTATION_COUNTS), dtype=np.uint64)
    examples, values, timings = np.empty((2, 2), dtype=np.int64), np.empty((2, 7)), np.empty(2)
    library.fit_local_targets_v314(*arrays, n_games, leaf.model.patterns, leaf.radix,
        leaf.reward_weights, leaf.risk_weights, bootstrap_reward, bootstrap_risk, float(alpha),
        reward, win, kind, learning, targets, normalization, representation,
        bootstrap, bootstrap_representation, examples, values, timings)
    work = _work(LEARNING_COUNTS, learning)
    leaf.updates += work.get('td_updates', 0)
    leaf.counts.update(work)

    def example(index):
        if not work.get('td_updates', 0):
            return None
        game, step = map(int, examples[index])
        rt, pt, rp, pp, utility, re, pe = map(float, values[index])
        return dict(episode=game, step=step, reward_target=rt, risk_target=pt,
            reward_prediction=rp, risk_probability=pp, combined_prediction=utility,
            reward_error=re, risk_error=pe)

    target_path = Path(target_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = dict(schema='acfqp.local_sampled_sarsa_targets.v314',
        bootstrap_mode='BATCH_START_FROZEN_OWN_HEAD', bootstrap_version=deepcopy(bootstrap_version),
        fitted_games=n_games, fitted_steps=fit_end, goal_rank=leaf.radix,
        target_kinds={str(key):value for key,value in TARGET_KINDS.items()},
        target_rule='RECORDED_SUCCESSOR_AFTERSTATE_NEXT_REWARD_UNDISCOUNTED',
        target_array_bytes=int(reward.nbytes+win.nbytes+kind.nbytes))
    save_started, save_cpu = perf_counter(), process_time()
    with target_path.open('wb') as stream:
        np.savez_compressed(stream, targetreward=reward, targetwin=win, targetkind=kind,
            metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False))
    artifact = dict(file=str(target_path), saved_bytes=target_path.stat().st_size,
        save_cpu_seconds=process_time()-save_cpu, save_wall_seconds=perf_counter()-save_started,
        metadata=metadata)
    bootstrap_work = _work(BOOTSTRAP_COUNTS, bootstrap)
    bootstrap_work.update(_work(REPRESENTATION_COUNTS, bootstrap_representation))
    return dict(method='TD_LOCAL', alpha=float(alpha), fitted_games=n_games, fitted_steps=fit_end,
        trained_afterstates=work.get('td_updates', 0), learning_counts=work,
        reward_trained_afterstates=work.get('td_updates', 0), risk_trained_afterstates=work.get('td_updates', 0),
        frozen_game_start_predictions=True, frozen_batch_start_bootstrap=True,
        bootstrap_mode='BATCH_START_FROZEN_OWN_HEAD', bootstrap_version=deepcopy(bootstrap_version),
        target_counts=_work(TARGET_COUNTS, targets), normalization_counts=_work(NORMALIZATION_COUNTS, normalization),
        representation_counts=_work(REPRESENTATION_COUNTS, representation), bootstrap_counts=bootstrap_work,
        target_generation_cpu_seconds=float(timings[0]), target_generation_wall_seconds=float(timings[1]),
        target_artifact=artifact, first_sample=example(0), last_sample=example(1), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu_started)
