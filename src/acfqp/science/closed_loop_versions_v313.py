"""Sparse actual head histories and chronological matched factual-state quotas."""
import json
from pathlib import Path
from time import perf_counter, process_time

import numpy as np


def terminal_weights(leaf):
    return leaf.risk_weights if leaf.kind == 'LOCAL_RISK' else leaf.win_weights


def snapshot_weights(leaf):
    started, cpu = perf_counter(), process_time()
    reward, terminal = leaf.reward_weights.copy(), terminal_weights(leaf).copy()
    return dict(reward=reward, terminal=terminal,
        copy_parameters=int(reward.size + terminal.size),
        copy_bytes=int(reward.nbytes + terminal.nbytes),
        copy_cpu_seconds=process_time()-cpu, copy_wall_seconds=perf_counter()-started)


def save_version(leaf, source, lifecycle, context_id, arm, version, path,
                 *, base=None, previous=None):
    """v0 differs from SOURCE/neutral terminal; later versions from previous weights."""
    started, cpu = perf_counter(), process_time()
    path = Path(path).resolve(); path.parent.mkdir(parents=True, exist_ok=True)
    reward, terminal = leaf.reward_weights.reshape(-1), terminal_weights(leaf).reshape(-1)
    neutral = 0. if leaf.kind == 'LOCAL_RISK' else 1./64.
    if version == 0:
        reward_reference, terminal_reference = leaf.model.weights.reshape(-1), neutral
        if base is not None or previous is not None:
            raise ValueError('Initial head history uses its actual SOURCE baseline')
    else:
        if base is None or previous is None:
            raise ValueError('Consolidated head history requires its previous version')
        reward_reference = previous['reward'].reshape(-1)
        terminal_reference = previous['terminal'].reshape(-1)
    reward_indices = np.flatnonzero(reward != reward_reference).astype(np.int64)
    terminal_indices = np.flatnonzero(terminal != terminal_reference).astype(np.int64)
    metadata = dict(schema='acfqp.head_version.v313', head_kind=leaf.kind,
        lifecycle=lifecycle, parent=source['parent'], context_id=context_id,
        arm=arm, version=version, updates=leaf.updates, file=str(path),
        base_file=None if base is None else base['file'], source_checkpoint=source['checkpoint'],
        default_terminal=neutral, parameter_count=int(leaf.reward_weights.size),
        reward_indices_count=int(reward_indices.size), terminal_indices_count=int(terminal_indices.size))
    np.savez_compressed(path, reward_indices=reward_indices,
        reward_values=reward[reward_indices], terminal_indices=terminal_indices,
        terminal_values=terminal[terminal_indices], metadata_json=json.dumps(metadata, sort_keys=True))
    return dict(metadata, scan_parameters=int(leaf.reward_weights.size + terminal.size),
        copy_parameters=0 if previous is None else previous['copy_parameters'],
        copy_bytes=0 if previous is None else previous['copy_bytes'],
        copy_cpu_seconds=0. if previous is None else previous['copy_cpu_seconds'],
        copy_wall_seconds=0. if previous is None else previous['copy_wall_seconds'],
        saved_bytes=path.stat().st_size, save_cpu_seconds=process_time()-cpu,
        save_wall_seconds=perf_counter()-started,
        changed_parameters=int(reward_indices.size + terminal_indices.size))


def eligible_samples(dataset):
    end = int(dataset['fit_step_end'])
    return int(np.count_nonzero(np.max(dataset['afterstates'][:end], axis=1) < 11))


def select_prefix(dataset, quota):
    """Preserve complete labels and suffixes; select only a prefix of eligible FIT states."""
    started, cpu = perf_counter(), process_time()
    end = int(dataset['fit_step_end'])
    eligible = np.flatnonzero(np.max(dataset['afterstates'][:end], axis=1) < 11)
    if quota < 1 or quota > len(eligible):
        raise ValueError('Matched quota must fit each actor complete-game FIT prefix')
    mask = np.zeros(len(dataset['afterstates']), dtype=np.int32)
    mask[eligible[:quota]] = 1
    return mask, dict(eligible_samples=int(len(eligible)), selected_samples=int(quota),
        last_selected_step=int(eligible[quota-1]), candidate_fit_steps=end,
        selection_rule='CHRONOLOGICAL_NONWINNING_FIT_PREFIX_FULL_FACTUAL_SUFFIXES',
        selection_cpu_seconds=process_time()-cpu, selection_wall_seconds=perf_counter()-started)
