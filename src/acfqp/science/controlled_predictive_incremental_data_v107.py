"""Load original V105 increments and bind fixed half-budget training statistics."""
import gzip
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_continuation_data_v91 import _key
from acfqp.science.controlled_predictive_fragments_v83 import QUERIES
from acfqp.science.controlled_predictive_replica_ranking_v102 import pair_gamma


def _rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def _coverage(records):
    return {query: {role: sorted(record['episode'] for record in records
        if record['query'] == query and (record['episode'] % 5 == 4) == (role == 'heldout'))
        for role in ('training', 'heldout')} for query in QUERIES}


def _summary(records, cutoff):
    training = [record for record in records if record['episode'] < cutoff and record['episode'] % 5 != 4]
    heldout = [record for record in records if record['episode'] < cutoff and record['episode'] % 5 == 4]
    return dict(records=len(records), training_roots=len(training), heldout_roots=len(heldout),
        training_episodes={query: sorted({record['episode'] for record in training if record['query'] == query})
                           for query in QUERIES})


def load_training(source, life, allocation):
    """Retain both batch orders; derive half statistics from the first batch only."""
    started = perf_counter()
    source = Path(source)
    stages = allocation['construction']
    if (allocation['life'] != life or allocation['replicas'] != 4
            or [stage['budget'] for stage in stages] != [256000, 512000]):
        raise ValueError('V107 requires the original two-stage V105 four-replica allocation')
    records, half_records, seen, stage_rosters = [], [], set(), []
    cursor = 0
    for index, stage in enumerate(stages):
        acquisition, data = stage['acquisition'], stage['data']
        cutoff = stage['episode_cutoff']
        if (acquisition['life'] != life or acquisition['replicas'] != 4
                or acquisition['start_cursor'] != cursor or acquisition['episode_cutoff'] != cutoff
                or any(data[field] != acquisition[field] for field in ('start_cursor', 'next_cursor', 'episode_cutoff'))):
            raise ValueError('V105 training stages no longer share the original incremental cursor')
        folder = source / f'life_{life}' / 'replicas_4' / f"budget_{stage['budget']}"
        path = folder / 'candidate_roots.jsonl.gz'
        batch = _rows(path)
        keys = [_key(record) for record in batch]
        if (keys != [_key(root) for root in acquisition['completed_roots']]
                or len(keys) != len(set(keys)) or seen.intersection(keys)):
            raise ValueError('V105 retained records differ from the complete incremental root roster')
        for record in batch:
            labels, utilities = np.asarray(record['replica_utilities']), np.asarray(record['utilities'])
            if (np.asarray(record['features']).shape != (5, 121) or labels.shape != (4, 5)
                    or utilities.shape != (5,) or not np.all(labels[:, 0] == 0)
                    or not np.allclose(labels.mean(axis=0), utilities, rtol=0, atol=1e-12)):
                raise ValueError('V105 candidate inputs or replica means differ from their original label contract')
        summary = _summary(batch, cutoff)
        if any(summary[field] != data['counts'][counter] for field, counter in (
                ('records', 'complete_roots'), ('training_roots', 'training_roots'), ('heldout_roots', 'heldout_roots'))):
            raise ValueError('V105 batch training or heldout counts differ from retained records')
        records.extend(batch)
        if index == 0:
            half_records = list(batch)
        seen.update(keys)
        if len(records) != stage['cumulative_root_count'] or _coverage(records) != stage['cumulative_roots']:
            raise ValueError('V105 cumulative training and heldout roster differs from retained records')
        stage_rosters.append(dict(budget=stage['budget'], episode_cutoff=cutoff,
            start_cursor=acquisition['start_cursor'], next_cursor=acquisition['next_cursor'],
            records=summary['records'], training_roots=summary['training_roots'],
            heldout_roots=summary['heldout_roots'], path=str(path)))
        cursor = acquisition['next_cursor']
    half_cutoff, full_cutoff = stages[0]['episode_cutoff'], stages[-1]['episode_cutoff']
    half, full = _summary(half_records, half_cutoff), _summary(records, full_cutoff)
    training = [record for record in half_records if record['episode'] < half_cutoff and record['episode'] % 5 != 4]
    x = np.asarray([record['features'] for record in training], dtype=float)
    y = np.asarray([record['utilities'] for record in training], dtype=float)
    labels = np.asarray([record['replica_utilities'] for record in training], dtype=float)
    mean, scale = x.mean(axis=(0, 1)), x.std(axis=(0, 1))
    scale[scale == 0] = 1.
    gamma = float(pair_gamma(y, labels).mean())
    payloads = {}
    for hidden in (4, 16):
        name = f'R4_H{hidden}_UNIFORM_SHRINK_DIRECT_FROZEN_HALF'
        metadata = allocation['model_metadata'][name]
        path = source / f'life_{life}' / 'replicas_4' / f"budget_{stages[0]['budget']}" / f'{name.lower()}_model.json'
        payload = json.loads(path.read_text())
        if (metadata['replicas'] != 4 or metadata['budget'] != stages[0]['budget']
                or metadata['hidden'] != hidden or metadata['episode_cutoff'] != half_cutoff
                or metadata['family'] != 'UNIFORM_SHRINK' or payload['hidden'] != hidden
                or payload['checkpoint'] != half_cutoff or payload['family'] != 'UNIFORM_SHRINK'
                or payload['training_episodes'] != half['training_episodes']):
            raise ValueError('V105 half payload context differs from its original training batch')
        if payload['mean'] != mean.tolist() or payload['scale'] != scale.tolist():
            raise ValueError('V105 half normalization is not exactly the first-batch training statistics')
        if payload['uniform_gamma'] != gamma:
            raise ValueError('V105 half conflict mass is not exactly the first-batch training statistic')
        payloads[str(hidden)] = payload
    log = dict(source=str(source), life=life, half_cutoff=half_cutoff, full_cutoff=full_cutoff,
        half=half, full=full, stage_rosters=stage_rosters,
        counts=dict(record_files_read=2, records_read=len(records), half_payload_files_read=2, files_read=4,
            normalization_recomputations=1, conflict_mass_recomputations=1,
            new_environment_transitions=0, new_synthetic_transitions=0, neural_model_fits=0,
            neural_candidate_predictions=0, new_feature_vectors=0, model_prefix_trajectories=0),
        checks=dict(source_allocation_bound=True, incremental_stages_bound=True, complete_stage_rosters=True,
            replica_means_bound=True, stage_splits_bound=True, half_payload_context_bound=True,
            half_normalization_exact=True, half_gamma_exact=True, half_training_episodes_exact=True),
        seconds=perf_counter() - started)
    return records, payloads, log
