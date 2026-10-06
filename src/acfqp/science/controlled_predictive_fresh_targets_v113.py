"""Acquire fixed fresh H2 trigger roots, model features and terminal references."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path
from time import perf_counter

from .controlled_predictive_candidate_data_v100 import build_candidates, write_row
from .controlled_predictive_fragment_experience_v83 import collect_source, sample_root
from .controlled_predictive_fragments_v83 import OPTIONS, QUERIES, TRIGGER_EMPTY_CELLS
from .controlled_predictive_reference_suffix_v104 import audit_reference
from .controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE_LIFE_BASE = 113000
PREFIX_REPLICAS = REFERENCE_REPLICAS = 32
ROOTS_PER_QUERY = 8
MAX_STEPS = 2000


def prefix_seed(life, query, episode):
    return 253000000000 + life * 10000000 + tuple(QUERIES).index(query) * 1000000 + episode * 1000


def _save(path, value):
    path.write_text(json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n')


def build_target_history(life, directory, dynamics_payload):
    """Finish each fixed source game; retain missing triggers without replacement."""
    started = perf_counter()
    folder = Path(directory) / f'life_{life}'
    folder.mkdir(parents=True, exist_ok=False)
    rule = LearnedDynamics.from_payload(dynamics_payload)
    source = dict(games=0, roots=0, ground_work=Counter(), planning_counts=Counter(),
        outcomes=Counter(), seconds=0.)
    prefix = dict(trajectories=0, model_work=Counter(), planning_counts=Counter(),
        feature_counts=Counter(), outcomes=Counter(), wiring={}, seconds=0.)
    checks = dict(source_streams_match=True, source_h2_only=True, first_trigger_roots_match=True,
        source_costs_match=True, source_games_roster_complete=True, candidate_shape_match=True,
        prefix_roster_complete=True, prefix_streams_match=True, prefix_wiring_match=True)
    result = dict(life=life, roots=[], missing_roots=[], source_log=source, prefix_log=prefix,
        checks=checks, seconds=0.)

    def retain():
        result['seconds'] = perf_counter() - started
        _save(folder / 'target_history.json', result)

    with gzip.open(folder / 'source_games.jsonl.gz', 'wt') as source_file, \
            gzip.open(folder / 'model_prefixes.jsonl.gz', 'wt') as prefix_file:
        for query in QUERIES:
            for episode in range(ROOTS_PER_QUERY):
                root_id = f'{life}_{query}_{episode}'
                root, raw, log = collect_source(SOURCE_LIFE_BASE + life, episode, query, rule,
                    max_steps=MAX_STEPS)
                write_row(source_file, dict(life=life, root_id=root_id, **raw))
                for name in ('games', 'roots', 'seconds'):
                    source[name] += log[name]
                for name in ('ground_work', 'planning_counts', 'outcomes'):
                    source[name].update(log[name])
                game, controller = raw['game'], raw['controller']
                seed = 8300000 + (SOURCE_LIFE_BASE + life) * 10000 + episode
                trigger = next((index for index, step in enumerate(game['steps'])
                    if step['board'].count(0) <= TRIGGER_EMPTY_CELLS), None)
                checks['source_streams_match'] &= (raw['query'] == query and raw['episode'] == episode
                    and raw['env_seed'] == game['seed'] == seed and raw['model_seed'] == seed + 1000000)
                checks['source_h2_only'] &= (controller['events'] == []
                    and controller['fragment_actions'] == 0 and controller['selected_option'] is None)
                checks['first_trigger_roots_match'] &= ((root is None) == (trigger is None)
                    and (root is None or (root['step'] == trigger and root['board'] == game['steps'][trigger]['board']
                        and root['query'] == query and root['episode'] == episode and root['source_seed'] == seed)))
                checks['source_costs_match'] &= (log['games'] == 1 and log['roots'] == int(root is not None)
                    and log['ground_work'] == game['work'] and log['planning_counts'] == raw['planning_counts']
                    and log['outcomes'] == {game['status']: 1})
                if not all(checks.values()):
                    retain()
                    raise ValueError('V113 source execution differs from its fixed H2 trigger or stream')
                if root is None:
                    result['missing_roots'].append(dict(life=life, root_id=root_id, query=query,
                        episode=episode, source_seed=seed, status=game['status'], reason='no_h2_trigger'))
                    retain()
                    continue
                seed_prefix = prefix_seed(life, query, episode)
                features, utilities, traces, built = build_candidates(root['board'], query, rule,
                    seed_prefix, replicas=PREFIX_REPLICAS)
                for trace in traces:
                    write_row(prefix_file, dict(root_id=root_id, life=life, query=query, episode=episode,
                        prefix_seed=seed_prefix, **trace))
                prefix['trajectories'] += built['trajectories']
                prefix['seconds'] += built['seconds']
                for name in ('model_work', 'planning_counts', 'feature_counts', 'outcomes'):
                    prefix[name].update(built[name])
                for name, value in built['wiring'].items():
                    prefix['wiring'][name] = prefix['wiring'].get(name, True) and value
                checks['candidate_shape_match'] &= (len(features) == len(utilities) == len(OPTIONS)
                    and all(len(row) == 121 for row in features))
                checks['prefix_roster_complete'] &= (len(traces) == built['trajectories']
                    == PREFIX_REPLICAS * len(OPTIONS) and {(row['option'], row['replica']) for row in traces}
                    == {(option, replica) for option in OPTIONS for replica in range(PREFIX_REPLICAS)})
                checks['prefix_streams_match'] &= all(trace['initial_board'] == root['board']
                    and trace['spawn_seed'] == seed_prefix + trace['replica']
                    and trace['planning_seed'] == trace['spawn_seed'] + 1000000000000 for trace in traces)
                checks['prefix_wiring_match'] &= all(built['wiring'].values())
                result['roots'].append(dict(deepcopy(root), life=life, root_id=root_id,
                    features=features, prefix_utilities=utilities, prefix_seed=seed_prefix))
                retain()
                if not all(checks.values()):
                    raise ValueError('V113 candidate features or retained prefixes differ from the fixed construction')
    checks['source_games_roster_complete'] = (source['games'] == ROOTS_PER_QUERY * len(QUERIES)
        == len(result['roots']) + len(result['missing_roots']) and source['roots'] == len(result['roots']))
    retain()
    if not all(checks.values()):
        raise ValueError('V113 source game roster is incomplete')
    return result


def reference_job(root, directory, dynamics_payload):
    """Retain all reference arms; a censored root is evidence, not a retry request."""
    started = perf_counter()
    folder = Path(directory) / f"life_{root['life']}" / 'references' / f"{root['query']}_{root['episode']}"
    folder.mkdir(parents=True, exist_ok=False)
    rule = LearnedDynamics.from_payload(dynamics_payload)
    _, raw, log = sample_root(root, rule, SOURCE_LIFE_BASE + root['life'],
        replicas=REFERENCE_REPLICAS, max_steps=MAX_STEPS)
    checks = audit_reference(root, raw, log, replicas=REFERENCE_REPLICAS, life_base=SOURCE_LIFE_BASE)
    with gzip.open(folder / 'games.jsonl.gz', 'wt') as handle:
        for row in raw:
            write_row(handle, dict(root_id=root['root_id'], block='A' if row['replica'] < 16 else 'B', **row))
    record = dict(root_id=root['root_id'], life=root['life'], query=root['query'], episode=root['episode'],
        reference_log=log, reference_audit=checks,
        reference_complete=not log['censored_root'] and all(checks.values()), seconds=perf_counter() - started)
    _save(folder / 'reference.json', record)
    if not all(checks.values()):
        raise ValueError('V113 reference execution differs from retained costs or frozen semantics')
    return record
