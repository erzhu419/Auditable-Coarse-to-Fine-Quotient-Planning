"""Recover all V103 natural query roots and their retained decisions without prediction."""
from collections import Counter
import gzip
import json
from pathlib import Path
from time import perf_counter

from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS

LIFECYCLES, REPLICAS = (9, 10), 8
CURRENT = tuple(f'R{replicas}_H{hidden}_{family}_DIRECT'
    for replicas in (8, 4) for hidden in (4, 16)
    for family in ('MEAN_SIGN', 'REPLICA', 'UNIFORM_SHRINK'))
METHODS = ('H2_ONLY', 'PREFIX_ONLY_DIRECT') + CURRENT + tuple(name + '_FROZEN_HALF' for name in CURRENT)
NATURAL_FIELDS = ('seed', 'replica', 'query', 'score', 'utility', 'status', 'steps',
                  'selected_option', 'initiation_step')


def _read(path):
    return json.loads(path.read_text())


def _rows(path):
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            yield json.loads(line)


def load_cohort(source_v103, output):
    """Keep the whole fixed natural roster; reference outcomes never choose roots."""
    started = perf_counter()
    source, output = Path(source_v103), Path(output)
    run, analysis = _read(source / 'run.json'), _read(source / 'analysis.json')
    settings = run['settings']
    if (run['status'] != 'complete' or not analysis['complete'] or not analysis['primary_complete']
            or tuple(settings['methods']) != METHODS or tuple(settings['lifecycles']) != LIFECYCLES
            or tuple(settings['queries']) != tuple(QUERIES) or settings['evaluation_replicas'] != REPLICAS):
        raise ValueError('V104 requires the completed fixed V103 natural cohort')
    lifecycles = {row['id']: row for row in run['lifecycles']}
    if len(lifecycles) != len(run['lifecycles']) or set(lifecycles) != set(LIFECYCLES):
        raise ValueError('V103 natural histories differ from the frozen roster')
    counts = Counter(new_environment_transitions=0, new_synthetic_transitions=0,
        neural_model_fits=0, new_selector_calls=0, neural_candidate_predictions=0)
    roots = []
    for life in LIFECYCLES:
        evaluation = lifecycles[life]['evaluation']
        expected_roots = [(query, replica) for query in QUERIES for replica in range(REPLICAS)]
        cohort = {key: dict(id=f'life_{life}_{key[0]}_{key[1]}', life=life, query=key[0],
            episode=key[1], predictions={}, natural={}) for key in expected_roots}
        summaries = {}
        if set(evaluation['methods']) != set(METHODS):
            raise ValueError('V103 natural summary lacks a complete method roster')
        for method in METHODS:
            games = evaluation['methods'][method]['games']
            if (len(games) != len(expected_roots)
                    or {(game['query'], game['replica']) for game in games} != set(expected_roots)):
                raise ValueError('V103 natural summaries lack the complete query and replica roster')
            for game in games:
                key = game['query'], game['replica']
                summaries[method, game['query'], game['seed']] = game
                cohort[key]['natural'][method] = {field: game[field] for field in NATURAL_FIELDS}
                counts['source_natural_games'] += 1
        seen = set()
        for raw in _rows(source / f'life_{life}' / 'evaluation/evaluation_games.jsonl.gz'):
            game, method = raw['episode'], raw['method']
            raw_key = method, raw['query'], game['seed']
            if raw_key in seen or raw_key not in summaries:
                raise ValueError('V103 natural trace is repeated or absent from its summary roster')
            seen.add(raw_key)
            summary = summaries[raw_key]
            root = cohort[summary['query'], summary['replica']]
            if (game['return_score'] != summary['score'] or game['status'] != summary['status']
                    or game['status'] not in ('WON', 'LOST')
                    or game['steps_count'] != summary['steps']
                    or len(raw['controller_events']) != summary['controller_events']):
                raise ValueError('V103 natural trace outcome or event count differs from its summary')
            counts['raw_rows_read'] += 1
            if method == 'H2_ONLY':
                trigger = next((step for step, row in enumerate(game['steps'])
                                if row['board'].count(0) <= TRIGGER_EMPTY_CELLS), None)
                if trigger is None or raw['controller_events'] or summary['selected_option'] is not None:
                    raise ValueError('V103 H2 trace lacks its expected first natural query trigger')
                root.update(board=game['steps'][trigger]['board'], step=trigger, source_seed=game['seed'])
                continue
            if len(raw['controller_events']) != 1:
                raise ValueError('V103 candidate trace does not retain exactly one decision')
            event = raw['controller_events'][0]
            if (event['option'] != summary['selected_option'] or event['step'] != summary['initiation_step']
                    or event['board'] != game['steps'][event['step']]['board']
                    or set(event['predictions']) != set(OPTIONS)):
                raise ValueError('V103 retained decision differs from its natural choice or trace root')
            root['predictions'][method] = event
            counts['retained_prediction_events'] += 1
        if seen != set(summaries):
            raise ValueError('V103 natural traces lack a complete method and query roster')
        validation = evaluation['validation']
        inherited = {(row['root']['query'], row['root']['episode']): row for row in validation['roots']}
        expected_inherited = {(query, replica) for query in QUERIES for replica in range(2)}
        if (validation['missing_roots'] or len(inherited) != len(validation['roots'])
                or set(inherited) != expected_inherited):
            raise ValueError('V103 inherited references differ from their original eight-root roster')
        for key in expected_roots:
            root = cohort[key]
            if (set(root['natural']) != set(METHODS) or set(root['predictions']) != set(METHODS[1:])
                    or any(event['board'] != root['board'] or event['step'] != root['step']
                           for event in root['predictions'].values())
                    or any(game['seed'] != root['source_seed'] for game in root['natural'].values())):
                raise ValueError('V103 methods do not share the same natural decision root')
            reference = inherited.get(key)
            if reference is not None:
                observed = {field: root[field] for field in ('life', 'query', 'episode', 'board', 'source_seed', 'step')}
                if reference['root'] != observed or reference['predictions'] != root['predictions']:
                    raise ValueError('V103 inherited reference root or predictions differ from the recovered decision')
            root.update(reference_origin='inherited' if key[1] < 2 else 'new', inherited_reference=reference)
            counts['inherited_reference_roots' if reference is not None else 'new_reference_roots'] += 1
            roots.append(root)
    counts['roots'] = len(roots)
    log = dict(source=str(source), source_terminal=True, methods=list(METHODS),
        contrasts=settings['contrasts'], counts=dict(counts),
        inherited_v103_work=analysis['actual_executed_work'], seconds=perf_counter() - started)
    (output / 'cohort.json').write_text(json.dumps(dict(roots=roots, log=log),
        allow_nan=False, separators=(',', ':')) + '\n')
    return roots, log
