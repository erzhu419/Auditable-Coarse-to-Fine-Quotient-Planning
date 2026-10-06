"""Whole-game T* residual updates isolated by observed LIBRARY module IDs."""
from collections import Counter
import ctypes
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np

from . import native_conditional_bellman_v294 as base

COUNT_NAMES = base.COUNT_NAMES + ('routed_sample_expert_reads',
    'routed_gradient_expert_address_visits', 'routed_expert_address_pairs',
    'routed_expert_parameter_commits', 'routed_parameter_pointer_views')
_LIBRARIES = {}


def _backend(runtime, setup):
    runtime = Path(runtime).resolve()
    if not runtime.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError('V295 builds belong inside the research worktree')
    key = str(runtime), os.getpid()
    if key not in _LIBRARIES:
        runtime.mkdir(parents=True, exist_ok=True)
        source = Path(__file__).with_suffix('.cpp')
        path = runtime / f'native_routed_bellman_v295_{os.getpid()}.so'
        subprocess.run(['g++', '-std=c++17', '-O3', '-shared', '-fPIC', '-ffp-contract=off',
            str(source), '-o', str(path)], check=True, capture_output=True, text=True,
            env=dict(os.environ, TMPDIR=str(runtime)))
        setup.update(cpp_compilations=1, cpp_translation_units_compiled=1,
                     included_v294_source_files=1)
        library = ctypes.CDLL(str(path))
        ip = np.ctypeslib.ndpointer(dtype=np.int32, flags='C_CONTIGUOUS')
        lp = np.ctypeslib.ndpointer(dtype=np.int64, flags='C_CONTIGUOUS')
        dp = np.ctypeslib.ndpointer(dtype=np.float64, flags='C_CONTIGUOUS')
        up = np.ctypeslib.ndpointer(dtype=np.uint64, flags='C_CONTIGUOUS')
        pp = np.ctypeslib.ndpointer(dtype=np.uintp, flags='C_CONTIGUOUS')
        ci, cd = ctypes.c_int, ctypes.c_double
        library.fit_routed_bellman_v295.argtypes = [ip, ci, dp, ip, ip, ci, dp, pp, ci,
            ip, lp, ip, cd, cd, cd, cd, cd, up, up, lp, dp, lp, dp]
        library.fit_routed_bellman_v295.restype = None
        _LIBRARIES[key] = library
    else:
        setup['cpp_library_cache_hits'] += 1
    return _LIBRARIES[key]


def fit_routed_episode(heads, game, runtime, alpha=.0025):
    """Read all experts first; normalize every routed gradient by global N_a."""
    started, cpu = perf_counter(), process_time()
    setup = Counter(); library = _backend(runtime, setup)
    boards, probabilities = base._inputs(game['afterstates'], game['model_p_four'])
    modules = np.asarray(game['module_ids'], dtype=np.int32)
    if modules.shape != (len(boards),):
        raise ValueError('V295 requires the observed module before each action')
    if not heads:
        raise ValueError('V295 requires the retained observed experts')
    module_ids = sorted(heads)
    template = heads[module_ids[0]].template
    for head in heads.values():
        if head.template is not template or head.banks != 2 or not head.residuals.flags.writeable:
            raise ValueError('V295 uses writable two-bank experts over one shared source')
    index = {module: i for i, module in enumerate(module_ids)}
    expert_indices = np.asarray([index[int(module)] for module in modules], dtype=np.int32)
    # Keep the original arrays alive; this array contains pointers, never weights.
    pointers = np.asarray([heads[m].residuals.ctypes.data for m in module_ids], dtype=np.uintp)
    n_experts = len(module_ids)
    native = np.zeros(len(COUNT_NAMES), dtype=np.uint64)
    module_work = np.zeros((n_experts, 3), dtype=np.uint64)
    indices, examples = np.full(2, -1, dtype=np.int64), np.zeros((2, 4), dtype=np.float64)
    module_indices = np.full((n_experts, 2), -1, dtype=np.int64)
    module_examples = np.zeros((n_experts, 2, 4), dtype=np.float64)
    p = base._parameters(heads[module_ids[0]])
    library.fit_routed_bellman_v295(boards, len(boards), probabilities, expert_indices,
        *p[:3], pointers, n_experts, *p[5:], float(alpha), native, module_work,
        indices, examples, module_indices, module_examples)
    work = {key: int(value) for key, value in zip(COUNT_NAMES, native) if value}
    def sample(step, values):
        if step < 0:
            return None
        target, before, error, prob = map(float, values)
        return dict(step=int(step), target=target, prediction_before_update=before,
                    error=error, model_p_four=prob)
    by_module = {}
    for i, module in enumerate(module_ids):
        head = heads[module]
        trained, writes, addresses = map(int, module_work[i])
        old = head.updates; head.updates += trained
        head.counts.update(td_updates=trained, parameter_write_events=writes,
                           table_update_occurrences=64*trained)
        by_module[str(module)] = dict(old_value_updates=old, new_value_updates=head.updates,
            trained_afterstates=trained, game_unique_addresses=addresses,
            learning_counts=dict(td_updates=trained, table_updates=writes,
                                 table_update_occurrences=64*trained),
            first_sample=sample(module_indices[i, 0], module_examples[i, 0]),
            last_sample=sample(module_indices[i, 1], module_examples[i, 1]))
    trained = work.get('td_updates', 0)
    return dict(target_kind='EXPECTED_CONTROL', conditioned=True, routed=True,
        alpha=float(alpha), fitted_games=1, fitted_steps=len(boards), trained_afterstates=trained,
        learning_counts=dict(td_updates=trained, table_updates=work.get('parameter_write_events', 0),
            table_update_occurrences=work.get('table_update_occurrences', 0)),
        target_counts=base._subset(work, base.TARGET_NAMES),
        prediction_counts=base._subset(work, base.PREDICTION_NAMES),
        consolidation_counts=base._subset(work, base.CONSOLIDATION_NAMES+COUNT_NAMES[46:]),
        counts=work, module_updates={m: r['trained_afterstates'] for m, r in by_module.items()},
        by_module=by_module, first_sample=sample(indices[0], examples[0]),
        last_sample=sample(indices[1], examples[1]), setup_counts=dict(setup),
        residual_pointer_array_bytes=pointers.nbytes, dense_expert_weight_stack_bytes=0,
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)
