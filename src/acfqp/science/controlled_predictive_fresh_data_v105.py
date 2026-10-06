"""Build fresh candidate inputs and replica terminal labels from one new budget batch."""
from collections import Counter
import gzip
from itertools import groupby
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_candidate_data_v100 import FEATURE_DIM, build_candidates, write_row
from acfqp.science.controlled_predictive_continuation_data_v91 import _key, _rows, _target
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility


def prefix_seed(life, episode, query):
    return 250000000000 + life * 10000000 + episode * 1000 + tuple(QUERIES).index(query) * 100


def load_batch(acquisition, folder, rule, life):
    """Read new branches once and generate prefixes only for complete four-replica roots.

    The acquisition was just executed by V105. The compatibility field
    inherited_acquisition records that supplied work, which this loader does not repeat.
    """
    start = perf_counter()
    folder = Path(folder)
    if acquisition['life'] != life or acquisition['replicas'] != 4:
        raise ValueError('V105 candidate data must match its new four-replica acquisition')
    accepted = {_key(root): root for root in acquisition['completed_roots']}
    roster = {_key(record['root']): record for record in acquisition['root_records']
              if record['branch_trajectories']}
    expected = {(option, replica) for option in OPTIONS for replica in range(4)}
    records, seen = [], set()
    counts, ground, planning, model_new, plan_new, feature_new, outcomes_new = (Counter() for _ in range(7))
    largest_difference = 0.0
    with gzip.open(folder / 'training_model_prefixes.jsonl.gz', 'wt') as retained:
        for key, stream in groupby(_rows(folder / 'branch_games.jsonl.gz'), key=lambda raw: _key(raw['root'])):
            if key in seen or key not in roster:
                raise ValueError('fresh branch root is repeated or absent from its acquisition roster')
            seen.add(key)
            raw = list(stream)
            indexed = {(row['option'], row['replica']): row for row in raw}
            for row in raw:
                ground.update(row['game']['work'])
                planning.update(row['planning_counts'])
                counts['trajectories_read'] += 1
                counts['steps_read'] += row['game']['work']['sampled_transitions']
            complete = (set(indexed) == expected and len(indexed) == len(raw)
                        and all(row['game']['status'] in ('WON', 'LOST') for row in raw))
            if complete != (key in accepted) or complete != roster[key]['complete_block']:
                raise ValueError('fresh whole-root completeness differs from acquisition')
            if not complete:
                counts['excluded_roots'] += 1
                continue
            root = accepted[key]
            seed = prefix_seed(life, root['episode'], root['query'])
            features, direct, prefixes, log = build_candidates(root['board'], root['query'], rule, seed, replicas=32)
            if np.asarray(features).shape != (len(OPTIONS), FEATURE_DIM) or not all(log['wiring'].values()):
                raise ValueError('fresh candidate inputs violate the frozen prefix semantics')
            for prefix in prefixes:
                write_row(retained, dict(root={field: root[field] for field in ('board', 'query', 'episode')}, **prefix))
            model_new.update(log['model_work'])
            plan_new.update(log['planning_counts'])
            feature_new.update(log['feature_counts'])
            outcomes_new.update(log['outcomes'])
            deltas = []
            for replica in range(4):
                reference = indexed['H2', replica]['game']
                reference_target = _target(reference['return_score'], reference['status'])
                paired = []
                for option in OPTIONS:
                    candidate = indexed[option, replica]['game']
                    paired.append([a - b for a, b in zip(
                        _target(candidate['return_score'], candidate['status']), reference_target)])
                deltas.append(paired)
            query = QUERIES[root['query']]
            targets = np.mean(deltas, axis=0).tolist()
            utilities = [_utility(target, query) for target in targets]
            replica_utilities = [[_utility(target, query) for target in paired] for paired in deltas]
            difference = float(np.max(np.abs(np.mean(replica_utilities, axis=0) - utilities)))
            if not np.allclose(np.mean(replica_utilities, axis=0), utilities, rtol=0, atol=1e-12):
                raise ValueError('fresh replica utilities do not average to their paired root means')
            largest_difference = max(largest_difference, difference)
            records.append(dict(board=root['board'], query=root['query'], episode=root['episode'],
                features=features, utilities=utilities, paired_rfs=targets, replica_utilities=replica_utilities,
                prefix_utilities=direct, prefix_seed=seed))
            counts['paired_replica_rows'] += 4
    if (seen != set(roster) or len(records) != len(accepted)
            or ground != Counter(acquisition['branches']['ground_work'])
            or planning != Counter(acquisition['branches']['planning_counts'])
            or ground['sampled_transitions'] + acquisition['source']['ground_work']['sampled_transitions']
                != acquisition['used_transitions'] or acquisition['used_transitions'] > acquisition['budget']):
        raise ValueError('fresh branch roster or physical work differs from acquisition')
    with gzip.open(folder / 'candidate_roots.jsonl.gz', 'wt') as handle:
        for record in records:
            write_row(handle, record)
    counts.update(complete_roots=len(records), training_roots=sum(record['episode'] % 5 != 4 for record in records),
        heldout_roots=sum(record['episode'] % 5 == 4 for record in records), mean_roots_verified=len(records),
        excluded_source_records=sum(not record['branch_trajectories'] for record in acquisition['root_records']),
        new_environment_transitions=0, tree_fits=0, neural_model_fits=0, neural_candidate_predictions=0)
    return records, dict(replicas=4, episode_cutoff=acquisition['episode_cutoff'],
        start_cursor=acquisition['start_cursor'], next_cursor=acquisition['next_cursor'], counts=dict(counts),
        inherited_acquisition=acquisition, new_model_work=dict(model_new), new_planning_counts=dict(plan_new),
        new_feature_counts=dict(feature_new), new_prefix_outcomes=dict(outcomes_new),
        model_prefix_trajectories=sum(outcomes_new.values()), model_prefix_roots=len(records),
        max_mean_utility_difference=largest_difference, seconds=perf_counter() - start)
