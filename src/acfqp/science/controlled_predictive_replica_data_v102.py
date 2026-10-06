"""Recover retained terminal replica labels beside unchanged V100 candidate features."""
from collections import Counter
import gzip
from itertools import groupby
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_candidate_data_v100 import FEATURE_DIM, write_row
from acfqp.science.controlled_predictive_continuation_data_v91 import _key, _rows, _target
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility


def load_batch(v98_folder, v100_folder, output):
    """Read each V98 branch once; retain whole roots and their original V100 inputs.

    Source trajectories, heldout branches and incomplete roots remain inherited
    acquisition cost. Reading retained trajectories performs no new simulation.
    """
    start = perf_counter()
    v98_folder, v100_folder, output = map(Path, (v98_folder, v100_folder, output))
    acquisition = json.loads((v98_folder / 'construction.json').read_text())['acquisition']
    feature_data = json.loads((v100_folder / 'construction.json').read_text())['data']
    if any(feature_data[field] != acquisition[field] for field in ('start_cursor', 'next_cursor', 'episode_cutoff')):
        raise ValueError('V100 feature stage differs from the V98 acquisition interval')
    replicas = acquisition['replicas']
    accepted = {_key(root): root for root in acquisition['completed_roots']}
    roster = {_key(record['root']): record for record in acquisition['root_records']
              if record['branch_trajectories']}
    saved = {}
    for record in _rows(v100_folder / 'candidate_roots.jsonl.gz'):
        key = _key(record)
        if key in saved:
            raise ValueError('duplicate retained V100 candidate root')
        saved[key] = record
    if set(saved) != set(accepted):
        raise ValueError('V100 candidate features do not match the complete V98 root roster')
    expected = {(option, replica) for option in OPTIONS for replica in range(replicas)}
    records, seen = [], set()
    counts, ground, planning = (Counter() for _ in range(3))
    largest_difference = 0.0
    branch_path = v98_folder / 'branch_games.jsonl.gz'
    for key, stream in groupby(_rows(branch_path), key=lambda raw: _key(raw['root'])):
        if key in seen or key not in roster:
            raise ValueError('retained branch root is repeated or absent from its original roster')
        seen.add(key)
        raw = list(stream)
        indexed = {(row['option'], row['replica']): row for row in raw}
        for row in raw:
            ground.update(row['game']['work'])
            planning.update(row['planning_counts'])
            counts['trajectories_read'] += 1
            counts['steps_read'] += row['game']['work']['sampled_transitions']
            counts['terminal_trajectories_read'] += row['game']['status'] in ('WON', 'LOST')
            counts['cutoff_trajectories_read'] += row['game']['status'] == 'CUTOFF'
        complete = (set(indexed) == expected and len(indexed) == len(raw)
                    and all(row['game']['status'] in ('WON', 'LOST') for row in raw))
        if complete != (key in accepted) or complete != roster[key]['complete_block']:
            raise ValueError('whole-root completeness differs from V98 acquisition')
        if not complete:
            counts['excluded_roots'] += 1
            counts['excluded_trajectories_read'] += len(raw)
            continue
        retained = saved[key]
        if np.asarray(retained['features']).shape != (len(OPTIONS), FEATURE_DIM):
            raise ValueError('retained V100 candidate feature dimensions differ')
        query = QUERIES[retained['query']]
        deltas = []
        for replica in range(replicas):
            reference = indexed['H2', replica]['game']
            reference_target = _target(reference['return_score'], reference['status'])
            paired = []
            for option in OPTIONS:
                candidate = indexed[option, replica]['game']
                target = _target(candidate['return_score'], candidate['status'])
                paired.append([a - b for a, b in zip(target, reference_target)])
            deltas.append(paired)
        utilities = np.asarray([[_utility(target, query) for target in paired]
                                for paired in deltas])
        mean_difference = float(np.max(np.abs(utilities.mean(axis=0) - retained['utilities'])))
        largest_difference = max(largest_difference, mean_difference)
        if (not np.allclose(utilities.mean(axis=0), retained['utilities'], rtol=0, atol=1e-12)
                or not np.allclose(np.mean(deltas, axis=0), retained['paired_rfs'], rtol=0, atol=1e-12)):
            raise ValueError('replica labels do not reproduce retained V100 terminal means')
        records.append(dict(retained, replica_utilities=utilities.tolist()))
        counts['paired_replica_rows'] += replicas
    if (seen != set(roster) or len(records) != len(accepted)
            or ground != Counter(acquisition['branches']['ground_work'])
            or planning != Counter(acquisition['branches']['planning_counts'])):
        raise ValueError('retained branch roster or costs differ from V98 acquisition')
    with gzip.open(output / 'candidate_roots.jsonl.gz', 'wt') as handle:
        for record in records:
            write_row(handle, record)
    inherited_ground = ground + Counter(acquisition['source']['ground_work'])
    inherited_planning = planning + Counter(acquisition['source']['planning_counts'])
    counts.update(complete_roots=len(records),
        training_roots=sum(record['episode'] % 5 != 4 for record in records),
        heldout_roots=sum(record['episode'] % 5 == 4 for record in records),
        mean_roots_verified=len(records),
        new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, neural_candidate_predictions=0, model_prefix_trajectories=0)
    return records, dict(replicas=replicas, episode_cutoff=acquisition['episode_cutoff'],
        start_cursor=acquisition['start_cursor'], next_cursor=acquisition['next_cursor'],
        counts=dict(counts), inherited_acquisition=acquisition,
        inherited_ground_work=dict(inherited_ground), inherited_planning_counts=dict(inherited_planning),
        inherited_feature_prefixes=dict(model_work=feature_data['new_model_work'],
            planning_counts=feature_data['new_planning_counts'], feature_counts=feature_data['new_feature_counts'],
            outcomes=feature_data['new_prefix_outcomes'], trajectories=feature_data['model_prefix_trajectories'],
            roots=feature_data['model_prefix_roots']),
        max_mean_utility_difference=largest_difference, seconds=perf_counter() - start)
