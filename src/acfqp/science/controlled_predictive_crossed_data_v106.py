"""Recover shared V105 decision inputs from retained model prefixes without simulation."""
from collections import Counter
import gzip
from itertools import groupby
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from acfqp.science.controlled_predictive_joint_fragments_v84 import _array
from acfqp.science.controlled_predictive_paired_continuation_value_v92 import _pair_array
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES

LIFECYCLES, REPLICAS, PREFIX_REPLICAS = (11, 12, 13, 14), 8, 32
PREFIX_FIELDS = ('option', 'replica', 'spawn_seed', 'planning_seed', 'initial_board',
                 'final_board', 'status', 'direct')


def recover_features(board, query, prefixes, replicas=32):
    """Reproduce V100's feature operations from outcomes already retained on disk."""
    indexed = {(row['option'], row['replica']): row for row in prefixes}
    expected = {(option, replica) for option in OPTIONS for replica in range(replicas)}
    if set(indexed) != expected or len(indexed) != len(prefixes):
        raise ValueError('retained candidate prefixes do not contain the complete option and replica roster')
    for replica in range(replicas):
        reference = indexed['H2', replica]
        for option in OPTIONS:
            row = indexed[option, replica]
            if row['initial_board'] != board:
                raise ValueError('retained candidate prefix starts at a different query board')
            if (row['spawn_seed'] != reference['spawn_seed']
                    or row['planning_seed'] != row['spawn_seed'] + 10 ** 12):
                raise ValueError('retained candidate prefix streams are not paired')
    work = Counter()
    observed = _array([dict(board=board)], work)[0]
    q = QUERIES[query]
    coefficients = [q['reward_weight'], -q['failure_penalty'], q['goal_bonus']]
    features, utilities = [], []
    for oi, option in enumerate(OPTIONS):
        pairs, deltas = [], []
        for replica in range(replicas):
            candidate, reference = indexed[option, replica], indexed['H2', replica]
            pairs.append(dict(candidate_board=candidate['final_board'], reference_board=reference['final_board'],
                candidate_active=candidate['status'] == 'ACTIVE', reference_active=reference['status'] == 'ACTIVE'))
            deltas.append([a - b for a, b in zip(candidate['direct'], reference['direct'])])
        paired = _pair_array(pairs, work).mean(axis=0)
        direct = np.asarray(deltas).mean(axis=0)
        features.append(np.concatenate((observed, paired, direct, np.eye(5)[oi], coefficients)).tolist())
        utilities.append(float(np.dot(direct, coefficients)))
    work['candidate_feature_vectors'] += len(OPTIONS)
    return features, utilities, dict(work)


def _rows(path):
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            yield json.loads(line)


def load_cohort(source, output, run):
    started = perf_counter()
    source, output = Path(source), Path(output)
    settings = run['settings']
    if (run['status'] != 'complete' or tuple(settings['lifecycles']) != LIFECYCLES
            or tuple(settings['queries']) != tuple(QUERIES)
            or settings['evaluation_replicas'] != REPLICAS or settings['prefix_replicas'] != PREFIX_REPLICAS):
        raise ValueError('V106 requires the complete fixed V105 natural-root cohort')
    methods = settings['methods']
    if len(methods) != 6 or methods[:2] != ['H2_ONLY', 'PREFIX_ONLY_DIRECT']:
        raise ValueError('V105 original method roster differs from the six frozen methods')
    lives = {life['id']: life for life in run['lifecycles']}
    if len(lives) != len(run['lifecycles']) or set(lives) != set(LIFECYCLES):
        raise ValueError('V105 histories do not match the fixed source roster')
    counts = Counter(new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, neural_candidate_predictions=0, new_selector_calls=0)
    feature_work, inherited_model, inherited_planning = Counter(), Counter(), Counter()
    roots = []
    for life in LIFECYCLES:
        validation = lives[life]['evaluation']['validation']
        references = {(row['root']['query'], row['root']['episode']): row for row in validation['roots']}
        roster = [(query, episode) for query in QUERIES for episode in range(REPLICAS)]
        if (validation['missing_roots'] or len(references) != len(validation['roots'])
                or set(references) != set(roster)):
            raise ValueError('V105 references do not cover every original natural query root')
        def selected_prefixes():
            for raw in _rows(source / f'life_{life}' / 'evaluation/model_prefixes.jsonl.gz'):
                counts['rows_read'] += 1
                if raw['method'] != 'PREFIX_ONLY_DIRECT':
                    continue
                counts['retained_prefixes'] += 1
                inherited_model.update(raw['model_work'])
                inherited_planning.update(raw['planning_counts'])
                yield dict(query=raw['query'], episode=raw['episode'],
                           **{field: raw[field] for field in PREFIX_FIELDS})
        restored = {}
        for key, stream in groupby(selected_prefixes(), key=lambda row: (row['query'], row['episode'])):
            if key in restored or key not in references:
                raise ValueError('retained PREFIX root is repeated or absent from the reference roster')
            reference = references[key]
            root = reference['root']
            if root['life'] != life:
                raise ValueError('V105 reference belongs to a different source history')
            prefixes = list(stream)
            seed = (settings['synthetic_seed_base'] + life * 10000000
                    + tuple(QUERIES).index(key[0]) * 1000000 + key[1] * 1000)
            if any(row['spawn_seed'] != seed + row['replica'] for row in prefixes):
                raise ValueError('retained PREFIX stream differs from its original natural-root seed')
            features, direct, work = recover_features(root['board'], key[0], prefixes, replicas=PREFIX_REPLICAS)
            feature_work.update(work)
            predictions = reference['predictions']
            if (set(predictions) != set(methods[1:]) or any(
                    event['board'] != root['board'] or event['step'] != root['step'] for event in predictions.values())):
                raise ValueError('V105 original prediction events do not match their retained query root')
            original = predictions['PREFIX_ONLY_DIRECT']
            if (set(original['predictions']) != set(OPTIONS)
                    or [original['predictions'][option]['value'] for option in OPTIONS] != direct):
                raise ValueError('recovered prefix scores differ from the original decision')
            selected = max(range(len(OPTIONS)), key=lambda index: direct[index])
            if original['option'] != OPTIONS[selected] or original['value'] != direct[selected]:
                raise ValueError('recovered prefix choice differs from the original decision')
            restored[key] = dict(root_id=f'life_{life}_{key[0]}_{key[1]}', **root,
                features=features, prefix_utilities=direct, original_predictions=predictions,
                reference_log=reference['terminal_log'], reference_complete=reference['reference_complete'],
                reference_audit=reference['audit'])
        if set(restored) != set(roster):
            raise ValueError('retained PREFIX trajectories do not cover all natural query roots')
        roots.extend(restored[key] for key in roster)
    counts.update(roots=len(roots), recovered_candidate_vectors=len(roots) * len(OPTIONS))
    log = dict(counts=dict(counts), feature_counts=dict(feature_work), seconds=perf_counter() - started,
        inherited_prefix_model_work=dict(inherited_model), inherited_prefix_planning_counts=dict(inherited_planning),
        checks=dict(source_complete=True, source_roster_complete=True, prefix_rosters_complete=True,
            prefix_boards_match=True, prefix_streams_match=True, prefix_scores_exact=True,
            prefix_choices_exact=True, original_events_bound=True))
    (output / 'cohort.json').write_text(json.dumps(dict(roots=roots, log=log),
        allow_nan=False, separators=(',', ':')) + '\n')
    return roots, log
