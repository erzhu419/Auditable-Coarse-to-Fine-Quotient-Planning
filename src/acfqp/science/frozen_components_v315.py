"""Restore actual LOCAL head histories and mix immutable reward/WIN components."""
from collections import Counter
from copy import copy, deepcopy
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

import numpy as np

from .native_split_risk_v301 import SplitLeaf

IDENTITY_KEYS = ('lifecycle', 'parent', 'context_id', 'source_checkpoint',
                 'head_kind', 'parameter_count', 'default_terminal')


def _child_cpu():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def restore_head(template, receipt, runtime):
    """Root supplies the template loaded from this receipt's V312 SOURCE parent."""
    started, cpu_started, compiler_started = perf_counter(), process_time(), _child_cpu()
    path, chain, identity = Path(receipt['file']).resolve(), [], None
    while True:
        with np.load(path, allow_pickle=False) as saved:
            metadata = json.loads(str(saved['metadata_json']))
            if metadata['schema'] != 'acfqp.head_version.v313' or metadata['head_kind'] != 'LOCAL_RISK':
                raise ValueError('V315 reconstructs the actual LOCAL version format')
            if Path(metadata['file']).resolve() != path:
                raise ValueError('Selected version file differs from its recorded path')
            current_identity = {key:metadata[key] for key in IDENTITY_KEYS}
            if identity is None:
                if any(receipt.get(key) != value for key, value in metadata.items()):
                    raise ValueError('Selected head receipt differs from saved version metadata')
                identity = current_identity
            elif current_identity != identity:
                raise ValueError('Head version chain changes its SOURCE or task-bank identity')
            if metadata['default_terminal'] != 0. or metadata['parameter_count'] != template.parent.source.weights.size:
                raise ValueError('Head version does not match the LOCAL SOURCE table shape')
            if chain:
                child = chain[-1]['metadata']
                if metadata['version'] != child['version'] - 1:
                    raise ValueError('Head history does not follow consecutive actual versions')
                expected_arm = 'FIRST_LOCAL' if metadata['version'] == 0 else child['arm']
                if metadata['arm'] != expected_arm:
                    raise ValueError('Head history switches its fitted arm')
            arrays = {key:saved[key] for key in
                ('reward_indices', 'reward_values', 'terminal_indices', 'terminal_values')}
        chain.append(dict(metadata=metadata, arrays=arrays, saved_bytes=path.stat().st_size))
        if metadata['base_file'] is None:
            if metadata['version'] != 0 or metadata['arm'] != 'FIRST_LOCAL':
                raise ValueError('Head history lacks its SOURCE-relative FIRST_LOCAL v0')
            break
        path = Path(metadata['base_file']).resolve()
    leaf = SplitLeaf(template, 'LOCAL_RISK', runtime)
    counts = Counter(version_files_loaded=len(chain),
        version_file_bytes_read=sum(row['saved_bytes'] for row in chain))
    for row in reversed(chain):
        arrays = row['arrays']
        leaf.reward_weights.reshape(-1)[arrays['reward_indices']] = arrays['reward_values']
        leaf.risk_weights.reshape(-1)[arrays['terminal_indices']] = arrays['terminal_values']
        counts['reward_sparse_parameter_writes'] += len(arrays['reward_indices'])
        counts['win_sparse_parameter_writes'] += len(arrays['terminal_indices'])
    leaf.updates = int(receipt['updates'])
    leaf.freeze()
    leaf.component_identity = dict(identity, version=receipt['version'], updates=leaf.updates)
    leaf.component_versions = dict(reward=deepcopy(receipt), win=deepcopy(receipt))
    reconstruction = dict(source_checkpoint=identity['source_checkpoint'], selected_head=deepcopy(receipt),
        version_chain=[deepcopy(row['metadata']) for row in reversed(chain)], counts=dict(counts),
        setup_counts=dict(leaf.setup_counts), setup_seconds=leaf.setup_seconds,
        private_weight_bytes=int(leaf.reward_weights.nbytes+leaf.risk_weights.nbytes),
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=_child_cpu()-compiler_started)
    return leaf, reconstruction


def combine_heads(reward_leaf, win_leaf):
    """Two frozen views use exactly the chosen existing arrays and native policy."""
    started, cpu_started = perf_counter(), process_time()
    if reward_leaf.kind != 'LOCAL_RISK' or win_leaf.kind != 'LOCAL_RISK':
        raise ValueError('V315 mixes exactly LOCAL reward/WIN heads')
    if reward_leaf.component_identity != win_leaf.component_identity:
        raise ValueError('Component selection must use the same SOURCE, task bank and version')
    if any(weights.flags.writeable for leaf in (reward_leaf, win_leaf)
           for weights in (leaf.reward_weights, leaf.risk_weights)):
        raise ValueError('Both selected component heads must remain frozen')
    leaf = copy(reward_leaf)
    leaf.reward_weights, leaf.risk_weights = reward_leaf.reward_weights, win_leaf.risk_weights
    leaf.counts = Counter()
    leaf.component_versions = dict(reward=deepcopy(reward_leaf.component_versions['reward']),
                                  win=deepcopy(win_leaf.component_versions['win']))
    leaf.setup_counts = Counter(head_objects_created=1,
        shared_reward_parameters=leaf.reward_weights.size, shared_win_parameters=leaf.risk_weights.size,
        allocated_weight_parameters=0, copied_weight_parameters=0)
    leaf.setup_seconds = leaf.seconds = perf_counter()-started
    leaf.setup_cpu_seconds = leaf.cpu_seconds = process_time()-cpu_started
    return leaf
