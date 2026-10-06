"""V319 WIN-only grouped learning with the actual FIRST reward table frozen."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from .native_query_supervision_v319 import LEARNING_COUNTS, TARGET_COUNTS, NORMALIZATION_COUNTS, _boards
from .native_retained_critic_v287 import _work
from .native_split_risk_v301 import REPRESENTATION_COUNTS

_LIBRARIES = {}


def _backend(runtime, counts):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V324 native builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        output = runtime / f'native_win_learning_v324_{os.getpid()}.so'
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
        ci, cd = ctypes.c_int, ctypes.c_double
        library.fit_win_supervision_v324.argtypes = [ip, ci, dp, ci, ip, ci, dp, cd,
            up, up, up, up, lp, dp, dp]
        library.fit_win_supervision_v324.restype = None
        _LIBRARIES[key] = library
    else:
        counts['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def fit_win_supervision(leaf, root_afterstates, targetwin, runtime, alpha=.0025):
    if leaf.kind != 'LOCAL_RISK' or leaf.reward_weights.flags.writeable or not leaf.risk_weights.flags.writeable:
        raise ValueError('V324 fitting requires frozen FIRST reward and private writable LOCAL WIN logits')
    started, cpu = perf_counter(), process_time()
    roots = _boards(root_afterstates); n = len(roots)
    win_targets = np.ascontiguousarray(targetwin, dtype=np.float64)
    if win_targets.ndim != 2 or win_targets.shape[0] != n or win_targets.shape[1] not in (2, 4):
        raise ValueError('WIN targets have two or four replicas per rootgroup')
    repeats = win_targets.shape[1]
    if np.any(np.max(roots, axis=1) >= leaf.radix):
        raise ValueError('V324 fitted rootgroups are all nonwinning afterstates')
    learning, targets, normalization, representation = (np.zeros(len(names), dtype=np.uint64)
        for names in (LEARNING_COUNTS, TARGET_COUNTS, NORMALIZATION_COUNTS, REPRESENTATION_COUNTS))
    examples, values, noise = np.empty(2, dtype=np.int64), np.empty((2, 3)), np.empty(1)
    setup = Counter(); library = _backend(runtime, setup)
    library.fit_win_supervision_v324(roots, n, win_targets, repeats, leaf.model.patterns,
        leaf.radix, leaf.risk_weights, float(alpha), learning, targets, normalization,
        representation, examples, values, noise)
    work = _work(LEARNING_COUNTS, learning)
    leaf.updates += work.get('rootgroup_updates', 0); leaf.counts.update(work)

    def sample(index):
        if not n:
            return None
        target, probability, error = map(float, values[index])
        return dict(rootgroup=int(examples[index]), risk_target=target,
            risk_probability=probability, risk_error=error)

    return dict(method='GROUPED_WIN_ONLY_LOCAL', alpha=float(alpha), fitted_rootgroups=n, replicates=repeats,
        trained_afterstates=work.get('rootgroup_updates', 0), reward_trained_afterstates=0,
        win_trained_afterstates=work.get('rootgroup_updates', 0), frozen_rootgroup_predictions=True,
        reward_frozen=True, sampling_unit='ROOTGROUP_MEAN_OF_PROVIDED_REPLICAS',
        learning_counts=work, target_counts=_work(TARGET_COUNTS, targets),
        normalization_counts=_work(NORMALIZATION_COUNTS, normalization),
        representation_counts=_work(REPRESENTATION_COUNTS, representation),
        replicate_noise=dict(win_replica_rms=float(noise[0]),
            definition='SQRT_MEAN_OVER_ALL_REPLICAS_OF_WITHIN_ROOTGROUP_CENTERED_SQUARES'),
        first_sample=sample(0), last_sample=sample(1), setup_counts=dict(setup),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
